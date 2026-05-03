"""
Import movements from Excel file and create linked Document records.

Usage:
    docker compose exec backend python scripts/import_movements.py <file.xlsx>

Excel format (header in row 2, data from row 3):
    A  - Дата внесення       → entry_date
    B  - Найменування        → item_name
    D  - № картки            → item_card_num
    E  - Одиниця виміру      → unit_of_measure
    F  - Категорія           → category
    G  - Надійшло            → qty_in
    H  - Вибуло              → qty_out
    I  - Звідки              → from_unit
    J  - Куди                → to_unit
    K  - МВО звідки          → mvo_from_id (lookup by "Ім'я Прізвище")
    L  - МВО куди            → mvo_to_id
    M  - Підстава            → basis
    N  - Дата документа      → doc_date
    O  - № документа         → doc_number
    Q  - Примітка            → serial_number
    S  - Код номенклатури    → nomenclature_code
    U  - Ціна                → price
    V  - Служба              → service
    Y  - Тип документа Excel → doc_type (Excel label, stored as-is)
    Z  - Тип операції        → mapped to our doc_type for Document record
    AB - Категорія отримувача→ recipient_category
"""

import sys
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from collections import defaultdict

import openpyxl
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

sys.path.insert(0, '/app')
from app.models import Movement, Person, Document

DATABASE_URL = os.environ['DATABASE_URL']
engine = create_engine(DATABASE_URL)

# Map Excel op type → our Document.doc_type
OP_TYPE_MAP = {
    'надходження':            'надходження',
    'внутрішнє переміщення':  'переміщення',
    'переміщення':            'переміщення',
}


def clean(val):
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def parse_date(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.strftime('%Y-%m-%d')
    s = str(val).strip()
    if not s:
        return None
    for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return s


def parse_decimal(val):
    if val is None:
        return None
    try:
        return Decimal(str(val).strip().replace(',', '.'))
    except (InvalidOperation, ValueError):
        return None


def build_person_map(session):
    persons = session.query(Person).all()
    mapping = {}
    for p in persons:
        if p.first_name and p.last_name:
            key = f"{p.first_name} {p.last_name}".strip().lower()
            mapping[key] = p.id
        if p.search_name:
            mapping[p.search_name.strip().lower()] = p.id
    return mapping


def col(row, idx):
    return row[idx].value if idx < len(row) else None


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_movements.py <file.xlsx>")
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        sys.exit(1)

    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(min_row=3))
    print(f"Found {len(rows)} data rows")

    with Session(engine) as session:
        person_map = build_person_map(session)
        print(f"Loaded {len(person_map)} persons from DB")

        admin_id = session.execute(
            text("SELECT id FROM users WHERE username = 'admin' LIMIT 1")
        ).scalar()

        # ── Pass 1: build document groups ─────────────────────────────────
        # Key: (doc_number, doc_date, mapped_doc_type)
        # Value: first row data for Document header fields
        doc_groups = {}
        movement_rows = []

        skipped = 0
        for i, row in enumerate(rows, start=3):
            item_name = clean(col(row, 1))  # B
            if not item_name:
                skipped += 1
                continue

            doc_number  = clean(col(row, 14))   # O
            doc_date    = parse_date(col(row, 13))  # N
            op_type_raw = clean(col(row, 25))   # Z — тип операції
            doc_type    = OP_TYPE_MAP.get(
                (op_type_raw or '').lower().strip(),
                op_type_raw or 'надходження'
            )

            doc_key = (doc_number, doc_date, doc_type)

            if doc_key not in doc_groups and (doc_number or doc_date):
                doc_groups[doc_key] = {
                    'from_unit': clean(col(row, 8)),   # I
                    'to_unit':   clean(col(row, 9)),   # J
                    'basis':     clean(col(row, 12)),  # M
                    'service':   clean(col(row, 21)),  # V
                }

            movement_rows.append((i, row, doc_key))

        print(f"Found {len(doc_groups)} unique documents")

        # ── Pass 2: create Document records ───────────────────────────────
        doc_id_map = {}  # doc_key → Document.id

        for doc_key, hdr in doc_groups.items():
            doc_number, doc_date, doc_type = doc_key
            doc = Document(
                doc_type   = doc_type,
                doc_number = doc_number,
                doc_date   = doc_date,
                from_unit  = hdr['from_unit'],
                to_unit    = hdr['to_unit'],
                basis      = hdr['basis'],
                service    = hdr['service'],
                status     = 'signed',
                signed_at  = datetime.now(timezone.utc),
                created_by = admin_id,
            )
            session.add(doc)
            session.flush()  # get doc.id
            doc_id_map[doc_key] = doc.id

        print(f"Created {len(doc_id_map)} Document records")

        # ── Pass 3: create Movement records ───────────────────────────────
        imported = 0
        unmatched_persons = set()

        for i, row, doc_key in movement_rows:
            mvo_from_name = clean(col(row, 10))  # K
            mvo_to_name   = clean(col(row, 11))  # L
            mvo_from_id = person_map.get(mvo_from_name.lower()) if mvo_from_name else None
            mvo_to_id   = person_map.get(mvo_to_name.lower())   if mvo_to_name   else None

            if mvo_from_name and not mvo_from_id:
                unmatched_persons.add(mvo_from_name)
            if mvo_to_name and not mvo_to_id:
                unmatched_persons.add(mvo_to_name)

            m = Movement(
                document_id       = doc_id_map.get(doc_key),
                entry_date        = parse_date(col(row, 0)),    # A
                item_name         = clean(col(row, 1)),          # B
                item_card_num     = clean(col(row, 3)),          # D
                unit_of_measure   = clean(col(row, 4)),          # E
                category          = clean(col(row, 5)),          # F
                qty_in            = parse_decimal(col(row, 6)),  # G
                qty_out           = parse_decimal(col(row, 7)),  # H
                from_unit         = clean(col(row, 8)),          # I
                to_unit           = clean(col(row, 9)),          # J
                mvo_from_id       = mvo_from_id,
                mvo_to_id         = mvo_to_id,
                basis             = clean(col(row, 12)),         # M
                doc_date          = parse_date(col(row, 13)),    # N
                doc_number        = clean(col(row, 14)),         # O
                serial_number     = clean(col(row, 16)),         # Q
                nomenclature_code = clean(col(row, 18)),         # S
                price             = parse_decimal(col(row, 20)), # U
                service           = clean(col(row, 21)),         # V
                doc_type          = clean(col(row, 24)),         # Y — Excel doc type label
                recipient_category= clean(col(row, 27)),         # AB
                created_by        = admin_id,
            )
            session.add(m)
            imported += 1

        session.commit()

        if unmatched_persons:
            print(f"\nWarning: {len(unmatched_persons)} МВО not found in persons table:")
            for name in sorted(unmatched_persons):
                print(f"  - {name}")

        print(f"\nDone: {imported} movements imported, {skipped} skipped, "
              f"{len(doc_id_map)} documents created")


if __name__ == '__main__':
    main()

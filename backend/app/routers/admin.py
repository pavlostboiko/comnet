"""Admin-only inventory wipe + XLSX bulk import.

Wipe scope: items, asset_documents, item_documents, document_items,
movements, documents. Everything else (persons, recipients, users,
services, op_types, unit_settings) stays.

Import format is hard-coded against the layout the user already has —
the same column maps as the legacy scripts removed in 4f98167.
"""
import re
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.models import (
    AssetDocument, Document, DocumentItem, Item, ItemDocument, Movement,
    OpType, Person, User,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ── Wipe ──────────────────────────────────────────────────────────────────

@router.post("/wipe-inventory", status_code=status.HTTP_200_OK)
def wipe_inventory(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Delete everything inventory-related. Persons/recipients/users
    /services/op_types/unit_settings survive."""
    # Order: leaf rows first, then dependents
    counts = {
        "document_items": db.query(DocumentItem).delete(synchronize_session=False),
        "item_documents": db.query(ItemDocument).delete(synchronize_session=False),
        "asset_documents": db.query(AssetDocument).delete(synchronize_session=False),
        "movements":      db.query(Movement).delete(synchronize_session=False),
        "documents":      db.query(Document).delete(synchronize_session=False),
        "items":          db.query(Item).delete(synchronize_session=False),
    }
    db.commit()
    return {"deleted": counts}


# ── Import helpers ────────────────────────────────────────────────────────

def _clean(val) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    return s or None


def _parse_decimal(val) -> Optional[Decimal]:
    if val is None or val == "":
        return None
    if isinstance(val, (int, float, Decimal)):
        return Decimal(str(val))
    s = str(val).strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _parse_date(val) -> Optional[str]:
    """Return YYYY-MM-DD or original string. Movements.doc_date is VARCHAR."""
    if val is None or val == "":
        return None
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    return str(val).strip()


def _read_workbook(upload: UploadFile):
    blob = upload.file.read()
    try:
        return load_workbook(BytesIO(blob), data_only=True)
    except Exception as e:
        raise HTTPException(400, f"Не вдалось прочитати XLSX: {e}")


# ── Items import ──────────────────────────────────────────────────────────

ITEMS_COLUMN_MAP = {
    "№":               "number",
    "Товар":           "name",
    "Код номер":       "nomenclature_code",
    "Серійний номер":  "serial_number",
    "Од. виміру":      "unit_of_measure",
    "Вартість":        "price",
    "Кіл-сть":         "quantity",
    "Категорія":       "item_type",
    "Де знаходиться":  "notes",
}

TYPE_PREFIX_RE = re.compile(r"^\d+\.\s*")


def _find_items_header_row(ws) -> Optional[int]:
    for row in ws.iter_rows(max_row=20):
        for cell in row:
            if cell.value and str(cell.value).strip() == "№":
                return cell.row
    return None


def _build_items_col_map(ws, header_row: int) -> dict:
    col_map = {}
    for cell in ws[header_row]:
        raw = str(cell.value).strip() if cell.value else ""
        if raw in ITEMS_COLUMN_MAP:
            col_map[cell.column] = ITEMS_COLUMN_MAP[raw]
    return col_map


@router.post("/import/items", status_code=status.HTTP_200_OK)
def import_items(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    wb = _read_workbook(file)
    ws = wb.active

    header_row = _find_items_header_row(ws)
    if not header_row:
        raise HTTPException(400, "Не знайдено рядок заголовків (шукаю колонку '№')")
    col_map = _build_items_col_map(ws, header_row)
    if "number" not in col_map.values() or "name" not in col_map.values():
        raise HTTPException(400, "Обов'язкові колонки '№' і 'Товар' не знайдено")

    created, skipped, errors = 0, 0, []
    existing_numbers = set(n for (n,) in db.query(Item.number).all())

    for row in ws.iter_rows(min_row=header_row + 1, values_only=False):
        vals = {}
        for cell in row:
            if cell.column in col_map and cell.value is not None:
                vals[col_map[cell.column]] = cell.value
        if not vals.get("number") or not vals.get("name"):
            continue

        number = str(vals["number"]).strip()
        if number in existing_numbers:
            skipped += 1
            continue

        item_type = vals.get("item_type")
        if item_type:
            item_type = TYPE_PREFIX_RE.sub("", str(item_type)).strip()

        try:
            db.add(Item(
                number            = number,
                name              = str(vals["name"]).strip(),
                nomenclature_code = _clean(vals.get("nomenclature_code")),
                serial_number     = _clean(vals.get("serial_number")),
                unit_of_measure   = _clean(vals.get("unit_of_measure")),
                price             = _parse_decimal(vals.get("price")),
                quantity          = _parse_decimal(vals.get("quantity")) or Decimal("1"),
                item_type         = item_type,
                notes             = _clean(vals.get("notes")),
                is_official       = True,
                created_by        = user.id,
            ))
            existing_numbers.add(number)
            created += 1
        except Exception as e:
            errors.append(f"#{number}: {e}")

    db.commit()
    return {"created": created, "skipped": skipped, "errors": errors}


# ── Movements import ──────────────────────────────────────────────────────

# Column layout from the legacy import_movements.py — header in row 2,
# data starts row 3, zero-indexed positions:
MV_COLS = {
    "entry_date":        0,    # A
    "item_name":         1,    # B
    "unit_of_measure":   3,    # D
    "category":          4,    # E
    "qty_in":            5,    # F
    "qty_out":           6,    # G
    "from_unit":         7,    # H
    "to_unit":           8,    # I
    "mvo_from_name":     9,    # J
    "mvo_to_name":      10,    # K
    "basis":            11,    # L
    "doc_date":         12,    # M
    "doc_number":       13,    # N
    "serial_number":    15,    # P
    "nomenclature_code":17,    # R
    "price":            19,    # T
    "service":          20,    # U
    "item_card_num":    23,    # X
    "doc_type_excel":   24,    # Y
    "op_type":          25,    # Z
    "recipient_category":26,   # AA
}

OP_TYPE_MAP = {
    "надходження":           ("надходження", "акт"),
    "внутрішнє переміщення": ("переміщення", "накладна"),
    "переміщення":           ("переміщення", "накладна"),
}


def _col(row, idx):
    return row[idx].value if idx < len(row) else None


@router.post("/import/movements", status_code=status.HTTP_200_OK)
def import_movements(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    wb = _read_workbook(file)
    ws = wb.active

    # Persons map for МВО lookup (lowercase search_name → id)
    persons_by_name = {
        (p.search_name or "").lower(): p.id
        for p in db.query(Person).all()
        if p.search_name
    }
    items_card_nums = set(n for (n,) in db.query(Item.number).all())

    created, skipped, errors, unmatched_persons = 0, 0, [], set()

    # Pass 1: collect document keys, create / dedupe Document rows
    doc_id_map = {}  # (op, form, doc_number, doc_date) → document.id
    rows_buffer = []

    for i, row in enumerate(ws.iter_rows(min_row=3, values_only=False), start=3):
        if not _col(row, MV_COLS["entry_date"]) and not _col(row, MV_COLS["item_name"]):
            continue
        rows_buffer.append((i, row))

        op_raw = _clean(_col(row, MV_COLS["op_type"]))
        if not op_raw:
            continue
        op_pair = OP_TYPE_MAP.get(op_raw.lower())
        if not op_pair:
            continue
        op, form = op_pair
        doc_num  = _clean(_col(row, MV_COLS["doc_number"]))
        doc_date = _parse_date(_col(row, MV_COLS["doc_date"]))
        key = (op, form, doc_num, doc_date)
        if key in doc_id_map or (not doc_num and not doc_date):
            continue
        # Re-use existing matching document if any
        doc = db.query(Document).filter(
            Document.operation == op,
            Document.form == form,
            Document.doc_number == doc_num,
            Document.doc_date == doc_date,
        ).first()
        if not doc:
            doc = Document(
                operation  = op,
                form       = form,
                doc_number = doc_num,
                doc_date   = doc_date,
                from_unit  = _clean(_col(row, MV_COLS["from_unit"])),
                to_unit    = _clean(_col(row, MV_COLS["to_unit"])),
                basis      = _clean(_col(row, MV_COLS["basis"])),
                service    = _clean(_col(row, MV_COLS["service"])),
                status     = "signed",
                created_by = user.id,
            )
            db.add(doc)
            db.flush()
        doc_id_map[key] = doc.id

    # Pass 2: create movements
    for i, row in rows_buffer:
        try:
            op_raw = _clean(_col(row, MV_COLS["op_type"]))
            op_pair = OP_TYPE_MAP.get((op_raw or "").lower()) if op_raw else None
            op, form = op_pair if op_pair else (None, None)
            doc_num  = _clean(_col(row, MV_COLS["doc_number"]))
            doc_date = _parse_date(_col(row, MV_COLS["doc_date"]))
            doc_id   = doc_id_map.get((op, form, doc_num, doc_date)) if op else None

            mvo_from_name = _clean(_col(row, MV_COLS["mvo_from_name"]))
            mvo_to_name   = _clean(_col(row, MV_COLS["mvo_to_name"]))
            mvo_from_id = persons_by_name.get(mvo_from_name.lower()) if mvo_from_name else None
            mvo_to_id   = persons_by_name.get(mvo_to_name.lower())   if mvo_to_name   else None
            if mvo_from_name and not mvo_from_id:
                unmatched_persons.add(mvo_from_name)
            if mvo_to_name and not mvo_to_id:
                unmatched_persons.add(mvo_to_name)

            card_num = _clean(_col(row, MV_COLS["item_card_num"]))
            item_card_num = card_num if card_num in items_card_nums else None

            db.add(Movement(
                document_id       = doc_id,
                entry_date        = _parse_date(_col(row, MV_COLS["entry_date"])),
                item_name         = _clean(_col(row, MV_COLS["item_name"])),
                item_card_num     = item_card_num,
                unit_of_measure   = _clean(_col(row, MV_COLS["unit_of_measure"])),
                category          = _clean(_col(row, MV_COLS["category"])),
                qty_in            = _parse_decimal(_col(row, MV_COLS["qty_in"])),
                qty_out           = _parse_decimal(_col(row, MV_COLS["qty_out"])),
                from_unit         = _clean(_col(row, MV_COLS["from_unit"])),
                to_unit           = _clean(_col(row, MV_COLS["to_unit"])),
                mvo_from_id       = mvo_from_id,
                mvo_to_id         = mvo_to_id,
                basis             = _clean(_col(row, MV_COLS["basis"])),
                doc_date          = doc_date,
                doc_number        = doc_num,
                serial_number     = _clean(_col(row, MV_COLS["serial_number"])),
                nomenclature_code = _clean(_col(row, MV_COLS["nomenclature_code"])),
                price             = _parse_decimal(_col(row, MV_COLS["price"])),
                service           = _clean(_col(row, MV_COLS["service"])),
                doc_type          = _clean(_col(row, MV_COLS["doc_type_excel"])),
                recipient_category = _clean(_col(row, MV_COLS["recipient_category"])),
                created_by        = user.id,
            ))
            created += 1
        except Exception as e:
            errors.append(f"row {i}: {e}")

    db.commit()
    return {
        "created": created,
        "skipped": skipped,
        "errors": errors,
        "unmatched_persons": sorted(unmatched_persons),
        "documents_created": len(doc_id_map),
    }

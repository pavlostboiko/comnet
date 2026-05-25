"""Snapshot logic for `накладна_25` documents.

`snap_nakladna()` copies the current values of every referenced FK (op_type,
service, sender/receiver/fin persons, unit_settings) into the doc's
`extra_data` JSON. The export reads ONLY these snap fields so a signed doc
stays immune to later directory edits (TZ §1, §8.4).
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import Document, OpType, Person, Service, UnitSettings
from app.uk_num2words import amount_to_words_uk, qty_to_words_uk


# Every snap-text key that lives in `documents.extra_data` JSON.
SNAP_KEYS = [
    "snap_unit_name", "snap_edrpou", "composed_location",
    "snap_op_type_name", "snap_service_name",
    "snap_service_chief_post", "snap_service_chief_name",
    "snap_sender_subdiv", "snap_sender_post", "snap_sender_name",
    "snap_recv_subdiv", "snap_recv_rank", "snap_recv_name", "snap_recv_post",
    "snap_fin_post", "snap_fin_name",
    "validity_date", "total_qty_words", "total_amount_words",
]

UK_MONTHS = ["січня", "лютого", "березня", "квітня", "травня", "червня",
             "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"]


# ── Date / name helpers ───────────────────────────────────────────────────

def person_full_name(p: Person) -> str:
    """«Ім'я ПРІЗВИЩЕ» — first_name + last_name.upper()"""
    return " ".join(filter(None, [
        (p.first_name or "").strip(),
        (p.last_name or "").strip().upper(),
    ]))


def parse_date(s: Optional[str]):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def calc_validity(doc_date: Optional[str]) -> str:
    """`doc_date + 3 days` formatted as `"DD" місяця YYYY року`."""
    dt = parse_date(doc_date)
    if not dt:
        return ""
    valid = dt + timedelta(days=3)
    return f'"{valid.day:02d}" {UK_MONTHS[valid.month - 1]} {valid.year} року'


# ── Auto-numbering ───────────────────────────────────────────────────────

def next_doc_number(prefix: str, db: Session, exclude_id: Optional[int] = None) -> str:
    """`prefix` + (max trailing integer among existing docs with that prefix + 1)."""
    if not prefix:
        return ""
    q = db.query(Document.doc_number).filter(
        Document.doc_number.like(prefix + "%"),
    )
    if exclude_id is not None:
        q = q.filter(Document.id != exclude_id)
    max_n = 0
    for (num,) in q.all():
        if not num or not num.startswith(prefix):
            continue
        try:
            n = int(num[len(prefix):])
            if n > max_n:
                max_n = n
        except ValueError:
            pass
    return f"{prefix}{max_n + 1}"


def resolve_auto_number(doc: Document, db: Session) -> List[str]:
    """If `doc.doc_number` is blank and op_type has a `number_prefix`, fill it
    via next sequential number. Warns on duplicate but does not block.
    Returns a list of human-readable warnings.
    """
    warnings: List[str] = []
    if doc.doc_number:
        dup = db.query(Document).filter(
            Document.doc_number == doc.doc_number,
            Document.id != (doc.id or -1),
        ).first()
        if dup:
            warnings.append(f"Накладна з номером {doc.doc_number} вже існує")
        return warnings

    if doc.op_type_id:
        ot = db.get(OpType, doc.op_type_id)
        if ot and ot.number_prefix:
            doc.doc_number = next_doc_number(ot.number_prefix, db, exclude_id=doc.id)
    return warnings


# ── Snapshot writer ──────────────────────────────────────────────────────

def snap_nakladna(doc: Document, db: Session) -> None:
    """Refresh snapshot fields on `doc` from current FK references.

    Called on every save while status == 'draft'. Stored values are read at
    export time (signed docs are immutable so their snap is frozen).
    """
    extra = dict(doc.extra_data or {})
    # Clear any prior snap, keep other keys untouched
    for k in SNAP_KEYS:
        extra.pop(k, None)

    settings = db.query(UnitSettings).first()
    if settings:
        extra["snap_unit_name"]    = settings.name or ""
        extra["snap_edrpou"]       = settings.edrpou or ""
        extra["composed_location"] = settings.location or ""

    if doc.op_type_id:
        ot = db.get(OpType, doc.op_type_id)
        if ot:
            extra["snap_op_type_name"] = ot.name or ""

    if doc.service_id:
        sv = db.get(Service, doc.service_id)
        if sv:
            doc.service = sv.name or ""
            extra["snap_service_name"]       = sv.name or ""
            extra["snap_service_chief_post"] = sv.chief_position or ""
            extra["snap_service_chief_name"] = sv.chief_name or ""

    if doc.sender_id:
        # Переміщення (or any sender that's an internal subdivision)
        p = db.get(Person, doc.sender_id)
        if p:
            doc.from_unit = p.unit or ""
            extra["snap_sender_subdiv"] = p.unit or ""
            extra["snap_sender_post"]   = p.position or ""
            extra["snap_sender_name"]   = person_full_name(p)
    else:
        # Надходження зовні: «Звідки» — вільний текст постачальника. No FK,
        # no post/name to snap; the freeform from_unit IS the supplier name.
        extra["snap_sender_subdiv"] = doc.from_unit or ""
        extra["snap_sender_post"]   = ""
        extra["snap_sender_name"]   = ""

    if doc.receiver_id:
        p = db.get(Person, doc.receiver_id)
        if p:
            doc.to_unit = p.unit or ""
            extra["snap_recv_subdiv"] = p.unit or ""
            extra["snap_recv_rank"]   = p.rank or ""
            extra["snap_recv_name"]   = person_full_name(p)
            extra["snap_recv_post"]   = p.position or ""

    if doc.fin_id:
        p = db.get(Person, doc.fin_id)
        if p:
            extra["snap_fin_post"] = p.position or ""
            extra["snap_fin_name"] = person_full_name(p)

    extra["validity_date"] = calc_validity(doc.doc_date)

    total_qty = Decimal(0)
    total_amt = Decimal(0)
    for it in doc.items:
        q = Decimal(str(it.quantity or 0))
        p = Decimal(str(it.price or 0))
        total_qty += q
        total_amt += q * p
    extra["total_qty_words"]    = qty_to_words_uk(total_qty) if total_qty else ""
    extra["total_amount_words"] = amount_to_words_uk(total_amt) if total_amt else ""

    doc.extra_data = extra

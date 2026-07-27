"""v2 snapshot + auto-numbering for `custody_documents` (Дод.25).

Adapts the v1 `document_snapshot` logic to v2 entities: «звідки/куди» come from
`warehouses` (or `counterparty` for external receipt), positions come from the
linked `custody_movements` + `nomenclature`. Reuses the shared date/name helpers
and snap-key set from `document_snapshot`.

`snap_*` values are read at export time; a signed doc's snap is frozen so the
printed form is immune to later directory edits.
"""
import re
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.document_snapshot import (
    SNAP_KEYS, calc_validity, parse_date, person_full_name,
)
from app.models import (
    CustodyDocument, CustodyMovement, Nomenclature, OpType, Person, Service,
    UnitSettings, Warehouse,
)
from app.uk_num2words import amount_to_words_uk, qty_to_words_uk


# ── Chronological tie-breaking ───────────────────────────────────────────

def doc_sort_key(doc_number: Optional[str]) -> Tuple[int, ...]:
    """Chronological key derived from a document number, for ordering movements
    that share the same `date`.

    Assumption: a larger number = a later document. The number is split into its
    integer groups so «596/250/2/1» < «596/250/2/2» < «596/250/2/10»
    (numeric, not lexical). A missing/number-less value sorts earliest (empty
    tuple), losing ties to numbered documents.
    """
    if not doc_number:
        return ()
    return tuple(int(g) for g in re.findall(r"\d+", doc_number))


# ── Auto-numbering ───────────────────────────────────────────────────────

def _next_seq(existing: List[str], year: int) -> str:
    """Next `НК-{year}-{NNN}` given already-used numbers (any format tolerated)."""
    prefix = f"НК-{year}-"
    max_n = 0
    for num in existing:
        if not num or not num.startswith(prefix):
            continue
        try:
            n = int(num[len(prefix):])
        except ValueError:
            continue
        if n > max_n:
            max_n = n
    return f"{prefix}{max_n + 1:03d}"


def next_doc_number(prefix: str, db: Session, exclude_id: Optional[int] = None) -> str:
    """`prefix` + (max trailing integer among existing docs with that prefix + 1)."""
    if not prefix:
        return ""
    q = db.query(CustodyDocument.doc_number).filter(CustodyDocument.doc_number.like(prefix + "%"))
    if exclude_id is not None:
        q = q.filter(CustodyDocument.id != exclude_id)
    max_n = 0
    for (num,) in q.all():
        if not num or not num.startswith(prefix):
            continue
        try:
            n = int(num[len(prefix):])
        except ValueError:
            continue
        if n > max_n:
            max_n = n
    return f"{prefix}{max_n + 1}"


def _doc_year(doc: CustodyDocument) -> int:
    dt = parse_date(doc.doc_date)
    if dt:
        return dt.year
    # fallback: latest linked movement date
    years = [m.date.year for m in (doc.movements or []) if m.date]
    return max(years) if years else 2026


def resolve_auto_number(doc: CustodyDocument, db: Session) -> List[str]:
    """Fill `doc.doc_number` if blank. op_type.number_prefix wins; else year-based
    `НК-{year}-NNN`. Duplicate → warning (does not block). Returns warnings."""
    warnings: List[str] = []
    if doc.doc_number:
        dup = db.query(CustodyDocument).filter(
            CustodyDocument.doc_number == doc.doc_number,
            CustodyDocument.id != (doc.id or -1),
        ).first()
        if dup:
            warnings.append(f"Документ з номером {doc.doc_number} вже існує")
        return warnings

    prefix = None
    if doc.op_type_id:
        ot = db.get(OpType, doc.op_type_id)
        if ot and ot.number_prefix:
            prefix = ot.number_prefix
    if prefix:
        doc.doc_number = next_doc_number(prefix, db, exclude_id=doc.id)
    else:
        year = _doc_year(doc)
        existing = [n for (n,) in db.query(CustodyDocument.doc_number).all()]
        doc.doc_number = _next_seq(existing, year)
    return warnings


# ── Snapshot writer ──────────────────────────────────────────────────────

def snap_nakladna(doc: CustodyDocument, db: Session) -> None:
    """Refresh snap fields on `doc` from current FK references + linked movements.

    Called on every save while status == 'draft'. Read at export time."""
    extra = dict(doc.extra_data or {})
    for k in SNAP_KEYS:
        extra.pop(k, None)

    settings = db.query(UnitSettings).first()
    if settings:
        extra["snap_unit_name"] = settings.name or ""
        extra["snap_edrpou"] = settings.edrpou or ""
        extra["composed_location"] = settings.location or ""

    if doc.op_type_id:
        ot = db.get(OpType, doc.op_type_id)
        if ot:
            extra["snap_op_type_name"] = ot.name or ""

    if doc.service_id:
        sv = db.get(Service, doc.service_id)
        if sv:
            doc.service = sv.name or ""
            extra["snap_service_name"] = sv.name or ""
            extra["snap_service_chief_post"] = sv.chief_position or ""
            extra["snap_service_chief_name"] = sv.chief_name or ""

    # «Звідки»: склад-джерело, або контрагент для приймання ззовні.
    from_label = ""
    if doc.from_warehouse_id:
        wh = db.get(Warehouse, doc.from_warehouse_id)
        from_label = wh.name if wh else ""
    elif doc.counterparty:
        from_label = doc.counterparty
    doc.from_unit = from_label
    extra["snap_sender_subdiv"] = from_label
    if doc.sender_id:
        p = db.get(Person, doc.sender_id)
        if p:
            extra["snap_sender_post"] = p.position or ""
            extra["snap_sender_name"] = person_full_name(p)
    else:
        extra["snap_sender_post"] = ""
        extra["snap_sender_name"] = ""

    # «Куди»: склад-отримувач.
    to_label = ""
    if doc.to_warehouse_id:
        wh = db.get(Warehouse, doc.to_warehouse_id)
        to_label = wh.name if wh else ""
    doc.to_unit = to_label
    extra["snap_recv_subdiv"] = to_label
    if doc.receiver_id:
        p = db.get(Person, doc.receiver_id)
        if p:
            extra["snap_recv_rank"] = p.rank or ""
            extra["snap_recv_name"] = person_full_name(p)
            extra["snap_recv_post"] = p.position or ""

    if doc.fin_id:
        p = db.get(Person, doc.fin_id)
        if p:
            extra["snap_fin_post"] = p.position or ""
            extra["snap_fin_name"] = person_full_name(p)

    extra["validity_date"] = calc_validity(doc.doc_date)

    total_qty = Decimal(0)
    total_amt = Decimal(0)
    for m in (doc.movements or []):
        q = Decimal(str(m.quantity or 0))
        nom = m.nomenclature or db.get(Nomenclature, m.nomenclature_id)
        p = Decimal(str((nom.price if nom else 0) or 0))
        total_qty += q
        total_amt += q * p
    extra["total_qty_words"] = qty_to_words_uk(total_qty) if total_qty else ""
    extra["total_amount_words"] = amount_to_words_uk(total_amt) if total_amt else ""

    doc.extra_data = extra

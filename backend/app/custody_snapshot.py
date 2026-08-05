"""v2 snapshot + auto-numbering for `custody_documents` (Дод.25).

Adapts the shared snapshot logic to v2 entities: «звідки/куди» come from
`warehouses` (or `counterparty` for external receipt), positions come from the
linked `custody_movements` + `nomenclature`. Reuses the shared date/name helpers
and snap-key set from `nakladna_common`.

`snap_*` values are read at export time; a signed doc's snap is frozen so the
printed form is immune to later directory edits.
"""
import re
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.nakladna_common import (
    SNAP_KEYS, calc_validity, parse_date, person_full_name,
)
from app.models import (
    CustodyDocument, CustodyMovement, Mvo, Nomenclature, OpType, Service,
    UnitSettings, Warehouse,
)


def mvo_at(db: Session, on_date, warehouse_id=None, fin: bool = False, service_id=None):
    """Запис журналу підписантів, діючий на дату `on_date`: МВО складу
    (warehouse_id), глобальна фінслужба (fin=True) або начальник служби
    (service_id). Повертає Mvo (з `.person`, `.position`, `.rank`) або None.
    Історичний журнал → стабільно."""
    if on_date is None:
        return None
    q = db.query(Mvo).filter(
        Mvo.from_date <= on_date,
        (Mvo.to_date.is_(None)) | (Mvo.to_date >= on_date),
    )
    if fin:
        q = q.filter(Mvo.kind == "fin")
    elif service_id is not None:
        q = q.filter(Mvo.kind == "service_chief", Mvo.service_id == service_id)
    else:
        if warehouse_id is None:
            return None
        q = q.filter(Mvo.kind == "warehouse", Mvo.warehouse_id == warehouse_id)
    return q.order_by(Mvo.from_date.desc(), Mvo.id.desc()).first()
from app.uk_num2words import amount_to_words_uk, qty_to_words_uk


def derive_service_id(doc: CustodyDocument, db: Session) -> None:
    """«Служба забезпечення» документа = служба його майна, не вибір користувача.

    Позиції однієї служби → проставляємо. Різні служби (склад підрозділу тримає
    майно кількох служб) або порожньо → лишаємо поточне значення: єдиної служби
    в такого документа немає, вигадувати її не можна.
    """
    ids = set()
    for m in (doc.movements or []):
        nom = m.nomenclature or db.get(Nomenclature, m.nomenclature_id)
        if nom and nom.service_id:
            ids.add(nom.service_id)
    if len(ids) == 1:
        doc.service_id = ids.pop()


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


def history_sort_key(e: dict):
    """Порядок подій історії майна (сортуємо з `reverse=True` — новіші зверху).

    Того самого дня:
    1) рухи впорядковані НОМЕРОМ накладної — в імпорті лише він дає хронологію
       (`created_at` там ~однаковий і йде порядком рядків файлу, задача 10);
    2) події особи/точки (видано, повернуто, зміна точки) стоять ПІСЛЯ рухів
       того ж дня: майно спершу приїхало (папером), і вже потім його видали чи
       переставили. Інакше документоване переміщення завжди вигравало в видачі
       по `doc_sort_key` і вилазило над нею.
    """
    return (e["date"] is None, e["date"] or "",
            0 if e.get("source") == "movement" else 1,
            doc_sort_key(e.get("doc_number")),
            e["created_at"], e["source_id"])


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

    doc_date = parse_date(doc.doc_date)

    if doc.service_id:
        sv = db.get(Service, doc.service_id)
        if sv:
            doc.service = sv.name or ""
            extra["snap_service_name"] = sv.name or ""
            # Начальник служби — з журналу підписантів на дату документа; поки
            # службу в журнал не завели, фолбек на вільний текст у її картці.
            chief = mvo_at(db, doc_date, service_id=sv.id)
            if chief:
                extra["snap_service_chief_post"] = chief.position or ""
                extra["snap_service_chief_name"] = person_full_name(chief.person)
            else:
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
    # Підписанти — з журналу МВО на дату документа (Здав = МВО from-складу,
    # Прийняв = МВО to-складу, Фін = глобальна фінслужба). Приймання ззовні:
    # from-складу немає → Здав без особи (лишається контрагент у subdiv).
    sender = mvo_at(db, doc_date, warehouse_id=doc.from_warehouse_id)
    if sender:
        extra["snap_sender_post"] = sender.position or ""
        extra["snap_sender_name"] = person_full_name(sender.person)
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
    receiver = mvo_at(db, doc_date, warehouse_id=doc.to_warehouse_id)
    if receiver:
        extra["snap_recv_rank"] = receiver.rank or ""
        extra["snap_recv_name"] = person_full_name(receiver.person)
        extra["snap_recv_post"] = receiver.position or ""

    fin = mvo_at(db, doc_date, fin=True)
    if fin:
        extra["snap_fin_post"] = fin.position or ""
        extra["snap_fin_name"] = person_full_name(fin.person)

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

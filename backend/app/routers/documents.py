import io
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Document, DocumentItem, Movement, Person, UnitSettings, User

router = APIRouter(prefix="/api/documents", tags=["documents"])

DOC_TYPES = ("надходження", "переміщення", "накладна_25")

REQUIRED_FIELDS = {
    "надходження":  ["doc_number", "doc_date", "to_unit"],
    "переміщення":  ["doc_number", "doc_date", "from_unit", "to_unit"],
    "накладна_25":  ["doc_number", "doc_date", "from_unit", "to_unit"],
}

EXTRA_FIELDS = [
    "validity_date", "composed_date", "composed_location", "operation_date",
    "op_type_text", "responsible_recipient",
    "sender_id", "receiver_id", "commander_id", "mvo_from_id", "mvo_to_id",
    "accountant_id", "fin_chief_id",
    "total_qty_words", "total_amount_words",
]


# ── Schemas ────────────────────────────────────────────────────────────────

class DocItemIn(BaseModel):
    sort_order: Optional[int] = None
    item_name: Optional[str] = None
    nomenclature_code: Optional[str] = None
    unit_of_measure: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[Decimal] = None
    qty_received: Optional[Decimal] = None
    price: Optional[Decimal] = None
    amount: Optional[Decimal] = None
    notes: Optional[str] = None


class DocIn(BaseModel):
    doc_type: str = "переміщення"
    doc_number: Optional[str] = None
    doc_date: Optional[str] = None
    from_unit: Optional[str] = None
    to_unit: Optional[str] = None
    basis: Optional[str] = None
    service: Optional[str] = None
    # накладна_25 extra fields
    validity_date: Optional[str] = None
    composed_date: Optional[str] = None
    composed_location: Optional[str] = None
    operation_date: Optional[str] = None
    op_type_text: Optional[str] = None
    responsible_recipient: Optional[str] = None
    sender_id: Optional[int] = None
    receiver_id: Optional[int] = None
    commander_id: Optional[int] = None
    mvo_from_id: Optional[int] = None
    mvo_to_id: Optional[int] = None
    accountant_id: Optional[int] = None
    fin_chief_id: Optional[int] = None
    total_qty_words: Optional[str] = None
    total_amount_words: Optional[str] = None
    items: List[DocItemIn] = []


# ── Helpers ────────────────────────────────────────────────────────────────

def _sorted_items(doc: Document):
    return sorted(doc.items, key=lambda x: (x.sort_order or 0, x.id))


def _items_for_display(doc: Document) -> list:
    if doc.items:
        return [
            {
                "id": it.id,
                "sort_order": it.sort_order,
                "item_name": it.item_name,
                "nomenclature_code": it.nomenclature_code,
                "unit_of_measure": it.unit_of_measure,
                "category": it.category,
                "quantity": float(it.quantity) if it.quantity is not None else None,
                "qty_received": float(it.qty_received) if it.qty_received is not None else None,
                "price": float(it.price) if it.price is not None else None,
                "amount": float(it.amount) if it.amount is not None else None,
                "notes": it.notes,
            }
            for it in _sorted_items(doc)
        ]
    # Fallback for imported documents: build from linked movements
    return [
        {
            "id": None,
            "sort_order": i,
            "item_name": m.item_name,
            "nomenclature_code": m.nomenclature_code,
            "unit_of_measure": m.unit_of_measure,
            "category": str(m.category) if m.category is not None else None,
            "quantity": float(m.qty_in or m.qty_out or 0),
            "qty_received": None,
            "price": float(m.price) if m.price is not None else None,
            "amount": float(m.price * (m.qty_in or m.qty_out or 0)) if m.price else None,
            "notes": m.serial_number,
        }
        for i, m in enumerate(sorted(doc.movements, key=lambda x: x.id), 1)
    ]


def _doc_to_dict(doc: Document) -> dict:
    extra = doc.extra_data or {}
    return {
        "id": doc.id,
        "doc_type": doc.doc_type,
        "doc_type_label": doc.movements[0].doc_type if doc.movements else None,
        "doc_number": doc.doc_number,
        "doc_date": doc.doc_date,
        "from_unit": doc.from_unit,
        "to_unit": doc.to_unit,
        "basis": doc.basis,
        "service": doc.service,
        "status": doc.status,
        "signed_at": doc.signed_at.isoformat() if doc.signed_at else None,
        **{f: extra.get(f) for f in EXTRA_FIELDS},
        "items": _items_for_display(doc),
    }


def _get_or_404(doc_id: int, db: Session) -> Document:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return doc


def _apply_items(doc: Document, items: List[DocItemIn], db: Session):
    for it in list(doc.items):
        db.delete(it)
    db.flush()
    for idx, it in enumerate(items):
        db.add(DocumentItem(
            document_id=doc.id,
            sort_order=it.sort_order if it.sort_order is not None else idx,
            item_name=it.item_name,
            nomenclature_code=it.nomenclature_code,
            unit_of_measure=it.unit_of_measure,
            category=it.category,
            quantity=it.quantity,
            qty_received=it.qty_received,
            price=it.price,
            amount=it.amount,
            notes=it.notes,
        ))


# ── CRUD ───────────────────────────────────────────────────────────────────

@router.get("")
def list_documents(
    doc_type: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(Document)
    if doc_type:
        q = q.filter(Document.doc_type == doc_type)
    docs = q.order_by(Document.created_at.desc()).all()
    return [
        {
            "id": d.id,
            "doc_type": d.doc_type,
            "doc_type_label": d.movements[0].doc_type if d.movements else None,
            "doc_number": d.doc_number,
            "doc_date": d.doc_date,
            "from_unit": d.from_unit,
            "to_unit": d.to_unit,
            "status": d.status,
            "items_count": len(d.movements) if d.status != 'draft' else len(d.items),
        }
        for d in docs
    ]


@router.get("/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return _doc_to_dict(_get_or_404(doc_id, db))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_document(payload: DocIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if payload.doc_type not in DOC_TYPES:
        raise HTTPException(400, f"doc_type must be one of: {DOC_TYPES}")

    extra = {f: getattr(payload, f) for f in EXTRA_FIELDS}
    doc = Document(
        doc_type=payload.doc_type,
        doc_number=payload.doc_number,
        doc_date=payload.doc_date,
        from_unit=payload.from_unit,
        to_unit=payload.to_unit,
        basis=payload.basis,
        service=payload.service,
        status="draft",
        extra_data=extra,
        created_by=user.id,
    )
    db.add(doc)
    db.flush()
    _apply_items(doc, payload.items, db)
    db.commit()
    db.refresh(doc)
    return _doc_to_dict(doc)


@router.put("/{doc_id}")
def update_document(doc_id: int, payload: DocIn, db: Session = Depends(get_db), _=Depends(get_current_user)):
    doc = _get_or_404(doc_id, db)
    if doc.status != "draft":
        raise HTTPException(400, "Підписаний документ не можна редагувати. Спочатку зніміть підпис.")

    doc.doc_type = payload.doc_type
    doc.doc_number = payload.doc_number
    doc.doc_date = payload.doc_date
    doc.from_unit = payload.from_unit
    doc.to_unit = payload.to_unit
    doc.basis = payload.basis
    doc.service = payload.service
    doc.extra_data = {f: getattr(payload, f) for f in EXTRA_FIELDS}
    _apply_items(doc, payload.items, db)
    db.commit()
    db.refresh(doc)
    return _doc_to_dict(doc)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    doc = _get_or_404(doc_id, db)
    if doc.status != "draft":
        raise HTTPException(400, "Не можна видалити підписаний документ. Спочатку зніміть підпис.")
    db.delete(doc)
    db.commit()


# ── Sign / Unsign ──────────────────────────────────────────────────────────

@router.post("/{doc_id}/sign")
def sign_document(doc_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    doc = _get_or_404(doc_id, db)
    if doc.status != "draft":
        raise HTTPException(400, "Документ вже підписано.")

    # Validate required fields
    errors = []
    for field in REQUIRED_FIELDS.get(doc.doc_type, []):
        if not getattr(doc, field, None):
            errors.append(field)
    if not doc.items:
        errors.append("items (список позицій порожній)")
    if errors:
        raise HTTPException(422, {"detail": "Заповніть обов'язкові поля", "missing": errors})

    extra = doc.extra_data or {}
    mvo_from_id = extra.get("mvo_from_id") or extra.get("sender_id")
    mvo_to_id   = extra.get("mvo_to_id")   or extra.get("receiver_id")

    for it in _sorted_items(doc):
        is_incoming = (doc.doc_type == "надходження")
        m = Movement(
            document_id=doc.id,
            entry_date=doc.doc_date,
            item_name=it.item_name,
            unit_of_measure=it.unit_of_measure,
            category=it.category,
            nomenclature_code=it.nomenclature_code,
            qty_in=it.quantity if is_incoming else (it.qty_received or None),
            qty_out=None if is_incoming else it.quantity,
            from_unit=doc.from_unit,
            to_unit=doc.to_unit,
            basis=doc.basis,
            doc_date=doc.doc_date,
            doc_number=doc.doc_number,
            doc_type=doc.doc_type,
            service=doc.service,
            price=it.price,
            mvo_from_id=mvo_from_id,
            mvo_to_id=mvo_to_id,
            created_by=user.id,
        )
        db.add(m)

    doc.status = "signed"
    doc.signed_at = datetime.utcnow()
    doc.signed_by = user.id
    db.commit()
    db.refresh(doc)
    return _doc_to_dict(doc)


@router.post("/{doc_id}/unsign")
def unsign_document(doc_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    doc = _get_or_404(doc_id, db)
    if doc.status == "draft":
        raise HTTPException(400, "Документ вже у статусі чернетки.")

    db.query(Movement).filter(Movement.document_id == doc.id).delete(synchronize_session=False)
    doc.status = "draft"
    doc.signed_at = None
    doc.signed_by = None
    db.commit()
    db.refresh(doc)
    return _doc_to_dict(doc)


# ── Excel export (накладна_25) ─────────────────────────────────────────────

@router.get("/{doc_id}/export/xlsx")
def export_xlsx(doc_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    doc = _get_or_404(doc_id, db)

    import os
    from copy import copy as _copy
    from urllib.parse import quote
    try:
        from openpyxl import load_workbook
        from openpyxl.cell.cell import MergedCell
    except ImportError:
        raise HTTPException(500, "openpyxl not installed")

    extra    = doc.extra_data or {}
    settings = db.query(UnitSettings).first()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _person(pid):
        if not pid:
            return None
        return db.query(Person).filter(Person.id == int(pid)).first()

    def person_name(pid):
        p = _person(pid)
        if not p:
            return ""
        return " ".join(filter(None, [p.first_name or "", (p.last_name or "").upper()])).strip()

    def person_pos(pid):
        p = _person(pid)
        return (p.position or "") if p else ""

    unit_name = (settings.name   or "") if settings else ""
    edrpou    = (settings.edrpou or "") if settings else ""
    location  = extra.get("composed_location") or ((settings.location or "") if settings else "")

    # ── Load template ─────────────────────────────────────────────────────────
    tpl = os.path.join(os.path.dirname(__file__), '..', 'nakladna_template.xlsx')
    wb = load_workbook(tpl)
    ws = wb.active

    # ── Item rows — handle variable count ─────────────────────────────────────
    items_list = _items_for_display(doc)
    n_items    = len(items_list)
    TROWS      = 5    # template slots rows 20–24
    extra_rows = max(0, n_items - TROWS)
    S          = extra_rows  # SHIFT for all footer rows

    if extra_rows > 0:
        # Save row-20 format before inserting
        fmt20 = []
        for col in range(1, 11):
            cell = ws.cell(row=20, column=col)
            fmt20.append({
                'border':        _copy(cell.border),
                'alignment':     _copy(cell.alignment),
                'font':          _copy(cell.font),
                'number_format': cell.number_format,
            })

        # openpyxl insert_rows does not shift merged cell ranges —
        # manually unmerge footer ranges, insert, then re-merge shifted.
        footer_merges = [
            (mr.min_row, mr.min_col, mr.max_row, mr.max_col)
            for mr in list(ws.merged_cells.ranges)
            if mr.min_row >= 25
        ]
        for r1, c1, r2, c2 in footer_merges:
            ws.unmerge_cells(start_row=r1, start_column=c1, end_row=r2, end_column=c2)

        ws.insert_rows(25, extra_rows)

        for r1, c1, r2, c2 in footer_merges:
            ws.merge_cells(start_row=r1 + extra_rows, start_column=c1,
                           end_row=r2 + extra_rows, end_column=c2)

        # Apply item-row format to newly inserted rows
        for nr in range(25, 25 + extra_rows):
            for ci, fmt in enumerate(fmt20, 1):
                nc = ws.cell(row=nr, column=ci)
                nc.border        = fmt['border']
                nc.alignment     = fmt['alignment']
                nc.font          = fmt['font']
                nc.number_format = fmt['number_format']

    def sv(addr, value):
        ws[addr].value = value

    def sr(row, col, value):
        ws.cell(row=row, column=col).value = value

    # ── Header (rows 1–15, fixed positions) ───────────────────────────────────
    sv('B2', unit_name)
    sv('D4', edrpou)

    validity = extra.get("validity_date") or ""
    sv('B6', f'Дійсна до "{validity}"' if validity else 'Дійсна до "____" _________ ____ року')

    sv('E7', doc.doc_number or "")
    sv('I8',  location)
    sv('I10', extra.get("composed_date") or doc.doc_date or "")
    sr(12, 3, extra.get("operation_date") or "")
    sr(12, 9, doc.service or "")
    sv('C13', extra.get("op_type_text") or "")
    sv('I13', doc.basis or "")
    sv('C14', extra.get("responsible_recipient") or "")
    sv('C15', doc.from_unit or "")
    sv('I15', doc.to_unit or "")

    # ── Fill item rows ────────────────────────────────────────────────────────
    total_qty = Decimal(0)
    total_amt = Decimal(0)

    for idx, it in enumerate(items_list):
        r = 20 + idx
        qty = Decimal(str(it["quantity"])) if it["quantity"] is not None else Decimal(0)
        amt = Decimal(str(it["amount"]))   if it["amount"]   is not None else Decimal(0)
        sr(r, 1,  idx + 1)
        sr(r, 2,  it["item_name"] or "")
        sr(r, 3,  it["nomenclature_code"] or "")
        sr(r, 4,  it["unit_of_measure"] or "")
        sr(r, 5,  it["category"] or "")
        sr(r, 6,  float(it["price"]) if it["price"] is not None else "")
        sr(r, 7,  float(qty) if qty else "")
        sr(r, 8,  float(it["qty_received"]) if it["qty_received"] is not None else "")
        sr(r, 9,  float(amt) if amt else "")
        sr(r, 10, it["notes"] or "")
        total_qty += qty
        total_amt += amt

    # ── Всього row (25 + S) ───────────────────────────────────────────────────
    sr(25 + S, 7, float(total_qty) if total_qty else "")
    sr(25 + S, 8, float(total_qty) if total_qty else "")
    sr(25 + S, 9, float(total_amt) if total_amt else "")

    # ── Commander (27 + S) ────────────────────────────────────────────────────
    cmd_id = extra.get("commander_id")
    sr(27 + S, 1,  person_pos(cmd_id))
    sr(27 + S, 10, person_name(cmd_id))

    # ── Total words ───────────────────────────────────────────────────────────
    sr(29 + S, 3, extra.get("total_qty_words") or "")   # C29:I29 merged

    amt_words = extra.get("total_amount_words") or ""
    sr(31 + S, 1, f"на\xa0суму {amt_words}" if amt_words else "")  # A31:J31 merged

    # ── МВО (36, 39 + S) ─────────────────────────────────────────────────────
    mvo_from = extra.get("mvo_from_id") or extra.get("sender_id")
    sr(36 + S, 1,  person_pos(mvo_from))
    sr(36 + S, 10, person_name(mvo_from))

    mvo_to = extra.get("mvo_to_id") or extra.get("receiver_id")
    sr(39 + S, 1,  person_pos(mvo_to))
    sr(39 + S, 10, person_name(mvo_to))

    # ── Accountant (46 + S) ───────────────────────────────────────────────────
    acc_id = extra.get("accountant_id")
    sr(46 + S, 10, person_name(acc_id))

    # ── Fin chief (52 + S) ───────────────────────────────────────────────────
    fin_id = extra.get("fin_chief_id")
    sr(52 + S, 10, person_name(fin_id))

    # ── Stream ────────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    display_name = f"накладна_{doc.doc_number or doc.id}.xlsx"
    encoded = quote(display_name.encode("utf-8"))
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=\"nakladna.xlsx\"; filename*=UTF-8''{encoded}"},
    )

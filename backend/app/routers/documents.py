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
from app.models import Document, DocumentItem, Movement, Person, UnitSettings

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

    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        raise HTTPException(500, "openpyxl not installed")

    extra = doc.extra_data or {}
    settings = db.query(UnitSettings).first()

    def person_str(pid):
        if not pid:
            return ""
        p = db.query(Person).filter(Person.id == int(pid)).first()
        if not p:
            return ""
        parts = []
        if p.rank:
            parts.append(p.rank)
        name = " ".join(filter(None, [
            p.last_name or "",
            (p.first_name[0] + ".") if p.first_name else "",
            (p.patronymic[0] + ".") if p.patronymic else "",
        ]))
        parts.append(name.strip())
        return " ".join(parts).strip()

    def person_pos(pid):
        if not pid:
            return ""
        p = db.query(Person).filter(Person.id == int(pid)).first()
        return (p.position or "") if p else ""

    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left   = Alignment(horizontal="left",   vertical="center", wrap_text=True)
    bold   = Font(bold=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Накладна"

    col_widths = [4, 28, 16, 9, 9, 13, 11, 11, 13, 20]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    def mc(r1, c1, r2, c2, val="", fnt=None, aln=None):
        ws.merge_cells(start_row=r1, start_column=c1, end_row=r2, end_column=c2)
        c = ws.cell(row=r1, column=c1, value=val)
        if fnt: c.font = fnt
        if aln: c.alignment = aln
        return c

    r = 1
    unit_name = settings.name if settings else ""
    edrpou    = settings.edrpou if settings else ""
    mc(r, 1, r+1, 6, unit_name, fnt=bold, aln=left)
    mc(r, 7, r, 10, f"Термін дії: {extra.get('validity_date','')}", aln=left)
    r += 1
    mc(r, 7, r, 10, f"ЄДРПОУ: {edrpou}", aln=left); r += 1

    mc(r, 1, r, 10, f"НАКЛАДНА (ВИМОГА) № {doc.doc_number or ''}",
       fnt=Font(bold=True, size=13), aln=center)
    ws.row_dimensions[r].height = 22; r += 1

    location = extra.get("composed_location") or (settings.location if settings else "") or ""
    mc(r, 1, r, 5, f"Місце: {location}", aln=left)
    mc(r, 6, r, 10, f"Дата: {doc.doc_date or ''}", aln=left); r += 1

    mc(r, 1, r, 5, f"Служба: {doc.service or ''}", aln=left)
    mc(r, 6, r, 10, f"Вид операції: {extra.get('op_type_text','')}", aln=left); r += 1

    mc(r, 1, r, 10, f"Підстава: {doc.basis or ''}", aln=left); r += 1
    mc(r, 1, r, 5, f"Звідки: {doc.from_unit or ''}", aln=left)
    mc(r, 6, r, 10, f"Куди: {doc.to_unit or ''}", aln=left); r += 1
    mc(r, 1, r, 5, f"Передає: {person_pos(extra.get('sender_id'))} {person_str(extra.get('sender_id'))}", aln=left)
    mc(r, 6, r, 10, f"Приймає: {person_pos(extra.get('receiver_id'))} {person_str(extra.get('receiver_id'))}", aln=left); r += 1

    headers = [
        "№\nз/п", "Назва майна або однорідна група",
        "Код номен-клатури", "Од.\nвиміру", "Кате-горія",
        "Вартість за од.", "К-сть\nвідпр.", "К-сть\nприйн.", "Сума", "Примітка",
    ]
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=r, column=col, value=h)
        c.font = bold; c.alignment = center; c.border = border
    ws.row_dimensions[r].height = 36; r += 1

    total_qty = Decimal(0)
    total_amt = Decimal(0)
    for idx, it in enumerate(_sorted_items(doc), 1):
        row_vals = [
            idx, it.item_name or "", it.nomenclature_code or "",
            it.unit_of_measure or "", it.category or "",
            float(it.price) if it.price else "",
            float(it.quantity) if it.quantity else "",
            float(it.qty_received) if it.qty_received else "",
            float(it.amount) if it.amount else "",
            it.notes or "",
        ]
        for col, val in enumerate(row_vals, 1):
            c = ws.cell(row=r, column=col, value=val)
            c.border = border
            c.alignment = center if col != 2 else left
        ws.row_dimensions[r].height = 18; r += 1
        if it.quantity: total_qty += Decimal(str(it.quantity))
        if it.amount:   total_amt += Decimal(str(it.amount))

    mc(r, 1, r, 6, "Разом:", fnt=bold, aln=Alignment(horizontal="right"))
    ws.cell(row=r, column=7, value=float(total_qty)).border = border
    ws.cell(row=r, column=9, value=float(total_amt)).border = border
    for col in [1,2,3,4,5,6,8,10]:
        ws.cell(row=r, column=col).border = border
    ws.row_dimensions[r].height = 16; r += 2

    mc(r, 1, r, 4, f"Керівник: {person_pos(extra.get('commander_id'))}", aln=left)
    mc(r, 5, r, 7, "підпис ____________", aln=left)
    mc(r, 8, r, 10, person_str(extra.get('commander_id')), aln=left); r += 2

    mc(r, 1, r, 10,
       f"Всього передано: {extra.get('total_qty_words','')} одиниць, "
       f"на суму {extra.get('total_amount_words','')} гривень.", aln=left); r += 3

    mc(r, 1, r, 10, "ЗВОРОТНІЙ БІК", fnt=bold, aln=center); r += 2
    mc(r, 1, r, 4, f"МВО здав: {person_pos(extra.get('mvo_from_id'))}", aln=left)
    mc(r, 5, r, 7, "підпис ____________", aln=left)
    mc(r, 8, r, 10, person_str(extra.get('mvo_from_id')), aln=left); r += 3

    mc(r, 1, r, 4, f"МВО прийняв: {person_pos(extra.get('mvo_to_id'))}", aln=left)
    mc(r, 5, r, 7, "підпис ____________", aln=left)
    mc(r, 8, r, 10, person_str(extra.get('mvo_to_id')), aln=left)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"nakладна_{doc.doc_number or doc.id}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

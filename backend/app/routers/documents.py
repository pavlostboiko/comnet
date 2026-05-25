import io
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, model_validator
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.document_export import build_xlsx, has_snap
from app.document_snapshot import resolve_auto_number, snap_nakladna
from app.models import Document, DocumentItem, Item, Movement, User

router = APIRouter(prefix="/api/documents", tags=["documents"])

OPERATIONS = ("надходження", "переміщення")
FORMS = ("накладна", "акт")

# (operation, form) → required fields for sign. form=акт is only valid with
# operation=надходження (validated separately in DocIn).
REQUIRED_FIELDS = {
    ("надходження", "накладна"): ["doc_number", "doc_date", "to_unit"],
    ("надходження", "акт"):      ["doc_number", "doc_date", "to_unit"],
    ("переміщення", "накладна"): ["doc_number", "doc_date"],
}

# Human-readable label written to Movement.doc_type at sign time. Keyed by
# `form` (paper artefact). Legacy values in old movement rows (Н-440/25, ...)
# still render as-is.
MOVEMENT_DOC_LABEL = {
    "накладна": "Накладна (вимога)",
    "акт":      "Акт прийому-передачі",
}


# ── Schemas ────────────────────────────────────────────────────────────────

class DocItemIn(BaseModel):
    sort_order: Optional[int] = None
    item_id: Optional[int] = None              # FK → items.id (накладна_25 snap source)
    item_name: Optional[str] = None
    nomenclature_code: Optional[str] = None
    unit_of_measure: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[Decimal] = None         # qty_sent
    qty_received: Optional[Decimal] = None
    price: Optional[Decimal] = None
    amount: Optional[Decimal] = None
    notes: Optional[str] = None


class DocIn(BaseModel):
    operation: str = "переміщення"
    form: str = "накладна"
    doc_number: Optional[str] = None
    doc_date: Optional[str] = None
    date_operation: Optional[str] = None
    from_unit: Optional[str] = None
    to_unit: Optional[str] = None
    basis: Optional[str] = None
    op_type_id: Optional[int] = None
    service_id: Optional[int] = None
    sender_id: Optional[int] = None
    receiver_id: Optional[int] = None
    fin_id: Optional[int] = None
    items: List[DocItemIn] = []

    @model_validator(mode="after")
    def _check_combo(self):
        if self.operation not in OPERATIONS:
            raise ValueError(f"operation must be one of {OPERATIONS}")
        if self.form not in FORMS:
            raise ValueError(f"form must be one of {FORMS}")
        if (self.operation, self.form) not in REQUIRED_FIELDS:
            raise ValueError(
                f"Combination operation={self.operation!r} + form={self.form!r} "
                f"is not supported"
            )
        return self


def _apply_items(doc: Document, items: List[DocItemIn], db: Session, snap_from_items: bool):
    """Replace doc.items. For накладна_25 (`snap_from_items=True`), missing snap
    fields are filled from the items table using `item_id`.
    """
    for old in list(doc.items):
        db.delete(old)
    db.flush()
    for idx, src in enumerate(items):
        snap_name = src.item_name
        snap_code = src.nomenclature_code
        snap_unit = src.unit_of_measure
        snap_cat  = src.category
        snap_price = src.price

        if snap_from_items and src.item_id:
            ref = db.get(Item, src.item_id)
            if ref:
                snap_name  = ref.name
                snap_code  = ref.nomenclature_code
                snap_unit  = ref.unit_of_measure
                snap_cat   = ref.category
                snap_price = ref.price

        qty = src.quantity
        amount = src.amount
        if amount is None and qty is not None and snap_price is not None:
            amount = Decimal(str(qty)) * Decimal(str(snap_price))

        db.add(DocumentItem(
            document=doc,
            sort_order=src.sort_order if src.sort_order is not None else idx,
            item_id=src.item_id,
            item_name=snap_name,
            nomenclature_code=snap_code,
            unit_of_measure=snap_unit,
            category=snap_cat,
            quantity=qty,
            qty_received=src.qty_received,
            price=snap_price,
            amount=amount,
            notes=src.notes,
        ))
    db.flush()


def _sorted_items(doc: Document):
    return sorted(doc.items, key=lambda x: (x.sort_order or 0, x.id))


def _items_for_display(doc: Document) -> list:
    if doc.items:
        return [
            {
                "id": it.id,
                "sort_order": it.sort_order,
                "item_id": it.item_id,
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
    # Fallback for imported docs (built from movements)
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
        "operation": doc.operation,
        "form": doc.form,
        # `doc_type_label` is the human-readable Movement.doc_type written at
        # sign time. For unsigned docs we surface the canonical form label so
        # the list view shows something useful even before sign.
        "doc_type_label":
            doc.movements[0].doc_type if doc.movements
            else MOVEMENT_DOC_LABEL.get(doc.form, doc.form),
        "doc_number": doc.doc_number,
        "doc_date": doc.doc_date,
        "date_operation": doc.date_operation,
        "from_unit": doc.from_unit,
        "to_unit": doc.to_unit,
        "basis": doc.basis,
        "service": doc.service,
        "op_type_id": doc.op_type_id,
        "service_id": doc.service_id,
        "sender_id": doc.sender_id,
        "receiver_id": doc.receiver_id,
        "fin_id": doc.fin_id,
        "status": doc.status,
        "signed_at": doc.signed_at.isoformat() if doc.signed_at else None,
        "extra_data": extra,
        "items": _items_for_display(doc),
    }


def _get_or_404(doc_id: int, db: Session) -> Document:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return doc


# ── CRUD ───────────────────────────────────────────────────────────────────

@router.get("")
def list_documents(
    operation: Optional[str] = None,
    form: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(Document)
    if operation:
        q = q.filter(Document.operation == operation)
    if form:
        q = q.filter(Document.form == form)
    docs = q.order_by(Document.created_at.desc()).all()
    return [
        {
            "id": d.id,
            "operation": d.operation,
            "form": d.form,
            "doc_type_label":
                d.movements[0].doc_type if d.movements
                else MOVEMENT_DOC_LABEL.get(d.form, d.form),
            "doc_number": d.doc_number,
            "doc_date": d.doc_date,
            "from_unit": d.from_unit,
            "to_unit": d.to_unit,
            "status": d.status,
            "items_count": len(d.movements) if d.status != "draft" else len(d.items),
        }
        for d in docs
    ]


@router.get("/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return _doc_to_dict(_get_or_404(doc_id, db))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_document(payload: DocIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    doc = Document(
        operation=payload.operation,
        form=payload.form,
        doc_number=payload.doc_number,
        doc_date=payload.doc_date,
        date_operation=payload.date_operation or payload.doc_date,
        from_unit=payload.from_unit,
        to_unit=payload.to_unit,
        basis=payload.basis,
        op_type_id=payload.op_type_id,
        service_id=payload.service_id,
        sender_id=payload.sender_id,
        receiver_id=payload.receiver_id,
        fin_id=payload.fin_id,
        status="draft",
        extra_data={},
        created_by=user.id,
    )
    db.add(doc)
    db.flush()

    warnings = resolve_auto_number(doc, db)

    is_nakl = payload.form == "накладна"
    _apply_items(doc, payload.items, db, snap_from_items=is_nakl)

    if is_nakl:
        snap_nakladna(doc, db)

    db.commit()
    db.refresh(doc)
    out = _doc_to_dict(doc)
    if warnings:
        out["warnings"] = warnings
    return out


@router.put("/{doc_id}")
def update_document(doc_id: int, payload: DocIn, db: Session = Depends(get_db), _=Depends(get_current_user)):
    doc = _get_or_404(doc_id, db)
    if doc.status != "draft":
        raise HTTPException(400, "Підписаний документ не можна редагувати. Спочатку зніміть підпис.")

    doc.operation = payload.operation
    doc.form = payload.form
    doc.doc_number = payload.doc_number
    doc.doc_date = payload.doc_date
    doc.date_operation = payload.date_operation or payload.doc_date
    doc.from_unit = payload.from_unit
    doc.to_unit = payload.to_unit
    doc.basis = payload.basis
    doc.op_type_id = payload.op_type_id
    doc.service_id = payload.service_id
    doc.sender_id = payload.sender_id
    doc.receiver_id = payload.receiver_id
    doc.fin_id = payload.fin_id

    warnings = resolve_auto_number(doc, db)

    is_nakl = payload.form == "накладна"
    _apply_items(doc, payload.items, db, snap_from_items=is_nakl)

    if is_nakl:
        snap_nakladna(doc, db)

    db.commit()
    db.refresh(doc)
    out = _doc_to_dict(doc)
    if warnings:
        out["warnings"] = warnings
    return out


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

    errors = []
    for field in REQUIRED_FIELDS.get((doc.operation, doc.form), []):
        if not getattr(doc, field, None):
            errors.append(field)
    if not doc.items:
        errors.append("items (список позицій порожній)")
    if errors:
        raise HTTPException(422, {"detail": "Заповніть обов'язкові поля", "missing": errors})

    is_incoming = (doc.operation == "надходження")
    label = MOVEMENT_DOC_LABEL.get(doc.form, doc.form)
    for it in _sorted_items(doc):
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
            doc_type=label,
            service=doc.service,
            price=it.price,
            mvo_from_id=doc.sender_id,
            mvo_to_id=doc.receiver_id,
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


# ── Excel export (form=накладна, any operation) ────────────────────────────

@router.get("/{doc_id}/export/xlsx")
def export_xlsx(doc_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    doc = _get_or_404(doc_id, db)
    if doc.form != "накладна":
        raise HTTPException(400, "XLSX-експорт доступний лише для форми «Накладна (вимога)»")
    if not has_snap(doc):
        raise HTTPException(
            400,
            "Документ створено до переходу на снапшот-архітектуру. "
            "Відкрийте його в редакторі та збережіть, щоб згенерувати snap-поля.",
        )

    body = build_xlsx(doc, _items_for_display(doc))
    display_name = f"накладна_{doc.doc_number or doc.id}.xlsx"
    encoded = quote(display_name.encode("utf-8"))
    return StreamingResponse(
        io.BytesIO(body),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition":
                f'attachment; filename="nakladna.xlsx"; filename*=UTF-8\'\'{encoded}',
        },
    )

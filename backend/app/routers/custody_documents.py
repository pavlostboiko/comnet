"""v2 custody documents — накладна/акт над леджером custody_movements.

Документ = шапка (реквізити + snap) над уже проведеними рухами. Життєвий цикл:
draft (редагується, група змінна) → signed (snap заморожено, номер зафіксовано,
доступний XLSX Дод.25). ⚠️ sign/unsign НЕ створюють і НЕ видаляють рухи —
леджер проводиться при створенні руху (інваріант v2).
"""
import io
from datetime import datetime
from urllib.parse import quote
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.acl import check_movement_create, is_admin, scope_movements
from app.auth import get_current_user
from app.custody_export import build_xlsx_v2, has_snap
from app.custody_snapshot import resolve_auto_number, snap_nakladna
from app.database import get_db
from app.models import (
    CustodyDocument, CustodyMovement, Instance, Nomenclature, User, Warehouse,
)
from app.schemas import CustodyDocIn

router = APIRouter(prefix="/api/custody/documents", tags=["custody-documents"])

OPERATIONS = ("receipt", "transfer")
FORMS = ("накладна", "акт")

# Обов'язкові поля для підпису (мінімум для коректного друку).
REQUIRED_FIELDS = ["doc_number", "doc_date"]


# ── Serialization ──────────────────────────────────────────────────────────

def _wh_name(db: Session, wid: Optional[int]) -> Optional[str]:
    if not wid:
        return None
    wh = db.get(Warehouse, wid)
    return wh.name if wh else None


def _line_dict(db: Session, m: CustodyMovement) -> dict:
    nom = m.nomenclature or db.get(Nomenclature, m.nomenclature_id)
    serial = None
    if m.instance_id:
        inst = m.instance or db.get(Instance, m.instance_id)
        serial = inst.serial_no if inst else None
    return {
        "id": m.id,
        "nomenclature_id": m.nomenclature_id,
        "nomenclature_name": nom.name if nom else None,
        "nomenclature_code": nom.code if nom else None,
        "unit_of_measure": nom.unit_of_measure if nom else None,
        "category": nom.category if nom else None,
        "price": str(nom.price) if (nom and nom.price is not None) else None,
        "quantity": str(m.quantity),
        "is_official": m.is_official,
        "instance_id": m.instance_id,
        "serial_no": serial,
        "card_number": m.card_number,
        "from_warehouse_id": m.from_warehouse_id,
        "to_warehouse_id": m.to_warehouse_id,
    }


def _doc_dict(db: Session, doc: CustodyDocument, with_lines: bool = True) -> dict:
    out = {
        "id": doc.id,
        "operation": doc.operation,
        "form": doc.form,
        "doc_number": doc.doc_number,
        "doc_date": doc.doc_date,
        "date_operation": doc.date_operation,
        "from_warehouse_id": doc.from_warehouse_id,
        "to_warehouse_id": doc.to_warehouse_id,
        "from_unit": doc.from_unit or _wh_name(db, doc.from_warehouse_id),
        "to_unit": doc.to_unit or _wh_name(db, doc.to_warehouse_id),
        "counterparty": doc.counterparty,
        "basis": doc.basis,
        "service_id": doc.service_id,
        "op_type_id": doc.op_type_id,
        "sender_id": doc.sender_id,
        "receiver_id": doc.receiver_id,
        "fin_id": doc.fin_id,
        "status": doc.status,
        "signed_at": doc.signed_at.isoformat() if doc.signed_at else None,
        "extra_data": doc.extra_data or {},
        "items_count": len(doc.movements or []),
    }
    if with_lines:
        out["lines"] = [_line_dict(db, m) for m in sorted(doc.movements or [], key=lambda x: x.id)]
    return out


# ── Access helpers ─────────────────────────────────────────────────────────

def _get_or_404(doc_id: int, db: Session) -> CustodyDocument:
    doc = db.get(CustodyDocument, doc_id)
    if not doc:
        raise HTTPException(404, "Документ не знайдено")
    return doc


def _visible_doc_ids(db: Session, user: User):
    """Set of document ids the user may see (has ≥1 visible movement)."""
    q = scope_movements(
        db.query(CustodyMovement.document_id).filter(CustodyMovement.document_id.isnot(None)),
        user,
    )
    return {row[0] for row in q.all()}


def _load_movements(db: Session, user: User, ids: List[int]) -> List[CustodyMovement]:
    if not ids:
        raise HTTPException(400, "Не вибрано жодного руху")
    visible = {m.id for m in scope_movements(db.query(CustodyMovement), user).all()}
    movements = []
    for mid in ids:
        m = db.get(CustodyMovement, mid)
        if not m or m.id not in visible:
            raise HTTPException(400, f"Рух {mid} не знайдено або немає доступу")
        movements.append(m)
    return movements


def _apply_group(db: Session, user: User, doc: CustodyDocument, movements: List[CustodyMovement]):
    """Validate a movement set is groupable, attach it to `doc`, set from/to."""
    pairs = {(m.from_warehouse_id, m.to_warehouse_id) for m in movements}
    if len(pairs) != 1:
        raise HTTPException(400, "Рухи мають різні напрямки (звідки→куди)")
    for m in movements:
        if m.document_id and m.document_id != doc.id:
            raise HTTPException(400, f"Рух {m.id} уже входить в інший документ")
        nom = m.nomenclature or db.get(Nomenclature, m.nomenclature_id)
        check_movement_create(user, m.from_warehouse_id, nom)
    (frm, to) = next(iter(pairs))
    doc.from_warehouse_id = frm
    doc.to_warehouse_id = to
    # detach movements previously in this doc but no longer selected
    keep = {m.id for m in movements}
    for old in list(doc.movements or []):
        if old.id not in keep:
            old.document_id = None
    for m in movements:
        m.document_id = doc.id


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("")
def list_documents(operation: Optional[str] = None, form: Optional[str] = None,
                   status_f: Optional[str] = None,
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(CustodyDocument)
    if operation:
        q = q.filter(CustodyDocument.operation == operation)
    if form:
        q = q.filter(CustodyDocument.form == form)
    if status_f:
        q = q.filter(CustodyDocument.status == status_f)
    docs = q.order_by(CustodyDocument.doc_date.desc().nullslast(),
                      CustodyDocument.id.desc()).all()
    if not is_admin(user):
        vis = _visible_doc_ids(db, user)
        docs = [d for d in docs if d.id in vis]
    return [_doc_dict(db, d, with_lines=False) for d in docs]


@router.get("/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = _get_or_404(doc_id, db)
    if not is_admin(user) and doc.id not in _visible_doc_ids(db, user):
        raise HTTPException(403, "Немає доступу до цього документа")
    return _doc_dict(db, doc)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_document(payload: CustodyDocIn, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    if payload.operation not in OPERATIONS:
        raise HTTPException(400, "Невідома операція")
    if payload.form not in FORMS:
        raise HTTPException(400, "Невідома форма")
    movements = _load_movements(db, user, payload.movement_ids)
    doc = CustodyDocument(
        operation=payload.operation, form=payload.form,
        doc_number=payload.doc_number, doc_date=payload.doc_date,
        date_operation=payload.date_operation or payload.doc_date,
        counterparty=payload.counterparty, basis=payload.basis,
        service_id=payload.service_id, op_type_id=payload.op_type_id,
        sender_id=payload.sender_id, receiver_id=payload.receiver_id,
        fin_id=payload.fin_id, status="draft", extra_data={}, created_by=user.id,
    )
    db.add(doc)
    db.flush()
    _apply_group(db, user, doc, movements)
    db.flush()
    warnings = resolve_auto_number(doc, db)
    snap_nakladna(doc, db)
    db.commit()
    db.refresh(doc)
    out = _doc_dict(db, doc)
    if warnings:
        out["warnings"] = warnings
    return out


@router.put("/{doc_id}")
def update_document(doc_id: int, payload: CustodyDocIn, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    doc = _get_or_404(doc_id, db)
    if not is_admin(user) and doc.id not in _visible_doc_ids(db, user):
        raise HTTPException(403, "Немає доступу до цього документа")
    if doc.status != "draft":
        raise HTTPException(400, "Підписаний документ не можна редагувати. Спочатку зніміть підпис.")
    if payload.form not in FORMS:
        raise HTTPException(400, "Невідома форма")
    doc.operation = payload.operation
    doc.form = payload.form
    doc.doc_number = payload.doc_number
    doc.doc_date = payload.doc_date
    doc.date_operation = payload.date_operation or payload.doc_date
    doc.counterparty = payload.counterparty
    doc.basis = payload.basis
    doc.service_id = payload.service_id
    doc.op_type_id = payload.op_type_id
    doc.sender_id = payload.sender_id
    doc.receiver_id = payload.receiver_id
    doc.fin_id = payload.fin_id
    movements = _load_movements(db, user, payload.movement_ids)
    _apply_group(db, user, doc, movements)
    db.flush()
    warnings = resolve_auto_number(doc, db)
    snap_nakladna(doc, db)
    db.commit()
    db.refresh(doc)
    out = _doc_dict(db, doc)
    if warnings:
        out["warnings"] = warnings
    return out


@router.post("/{doc_id}/sign")
def sign_document(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = _get_or_404(doc_id, db)
    if not is_admin(user) and doc.id not in _visible_doc_ids(db, user):
        raise HTTPException(403, "Немає доступу до цього документа")
    if doc.status != "draft":
        raise HTTPException(400, "Документ вже підписано.")
    missing = [f for f in REQUIRED_FIELDS if not getattr(doc, f, None)]
    if not doc.movements:
        missing.append("items (список позицій порожній)")
    if missing:
        raise HTTPException(422, {"detail": "Заповніть обов'язкові поля", "missing": missing})
    snap_nakladna(doc, db)                 # freeze current directory state
    doc.status = "signed"
    doc.signed_at = datetime.utcnow()
    doc.signed_by = user.id
    db.commit()
    db.refresh(doc)
    return _doc_dict(db, doc)


@router.post("/{doc_id}/unsign")
def unsign_document(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = _get_or_404(doc_id, db)
    if not is_admin(user) and doc.id not in _visible_doc_ids(db, user):
        raise HTTPException(403, "Немає доступу до цього документа")
    if doc.status == "draft":
        raise HTTPException(400, "Документ вже у статусі чернетки.")
    # ⚠️ рухи НЕ чіпаємо — леджер лишається проведеним.
    doc.status = "draft"
    doc.signed_at = None
    doc.signed_by = None
    db.commit()
    db.refresh(doc)
    return _doc_dict(db, doc)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = _get_or_404(doc_id, db)
    if not is_admin(user) and doc.id not in _visible_doc_ids(db, user):
        raise HTTPException(403, "Немає доступу до цього документа")
    if doc.status != "draft":
        raise HTTPException(400, "Не можна видалити підписаний документ. Спочатку зніміть підпис.")
    for m in list(doc.movements or []):     # відв'язуємо рухи, не видаляємо
        m.document_id = None
    db.delete(doc)
    db.commit()


@router.get("/{doc_id}/export/xlsx")
def export_xlsx(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = _get_or_404(doc_id, db)
    if not is_admin(user) and doc.id not in _visible_doc_ids(db, user):
        raise HTTPException(403, "Немає доступу до цього документа")
    if not has_snap(doc):
        raise HTTPException(400, "Документ без snap-полів. Відкрийте його в редакторі та збережіть.")
    body = build_xlsx_v2(doc, db)
    display_name = f"накладна_{doc.doc_number or doc.id}.xlsx"
    encoded = quote(display_name.encode("utf-8"))
    return StreamingResponse(
        io.BytesIO(body),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition":
                 f'attachment; filename="nakladna.xlsx"; filename*=UTF-8\'\'{encoded}'},
    )

"""v2 custody documents — накладна/акт над леджером custody_movements.

Документ = шапка (реквізити + snap) над уже проведеними рухами. Життєвий цикл:
draft (редагується, група змінна) → signed (snap заморожено, номер зафіксовано,
доступний XLSX Дод.25). ⚠️ sign/unsign НЕ створюють і НЕ видаляють рухи —
леджер проводиться при створенні руху (інваріант v2).
"""
import io
from datetime import date as date_cls, datetime
from decimal import Decimal
from urllib.parse import quote
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.acl import (
    check_movement_create, check_nomenclature_cud, is_admin, scope_movements,
)
from app.auth import get_current_user
from app.custody_export import build_xlsx_v2, has_snap
from app.custody_snapshot import resolve_auto_number, snap_nakladna
from app.database import get_db
from app.models import (
    CustodyDocument, CustodyMovement, Instance, Nomenclature, User, Warehouse,
)
from app.schemas import CustodyDocIn, ReceiptCreate

router = APIRouter(prefix="/api/custody/documents", tags=["custody-documents"])

OPERATIONS = ("receipt", "transfer")
FORMS = ("накладна", "акт")
RECEIPT_NO_DOC = "без документа"   # неформальний прихід (НДМ): рухи без custody-документа

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
        status="draft", extra_data={}, created_by=user.id,
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


def _check_receipt(user: User, to_warehouse_id: int, nom: Nomenclature):
    """Приймання: admin — усе; service — своя служба; mvo — свій склад."""
    if is_admin(user):
        return
    if user.role == "service" and user.service_id == nom.service_id:
        return
    if user.role == "mvo" and user.warehouse_id == to_warehouse_id:
        return
    raise HTTPException(403, "Немає доступу до цього ресурсу")


@router.post("/receive", status_code=status.HTTP_201_CREATED)
def receive_document(payload: ReceiptCreate, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """Приймання майна ззовні одразу документом (акт/накладна) на склад.

    Створює рухи receipt (ззовні → склад) з document_id. Номенклатуру можна
    створити на льоту. is_official завжди береться з картки, не з payload.
    Форма «без документа» (НДМ) → рухи без custody-документа."""
    no_doc = payload.form == RECEIPT_NO_DOC
    if not no_doc and payload.form not in FORMS:
        raise HTTPException(400, "Невідома форма")
    to = db.get(Warehouse, payload.to_warehouse_id)
    if not to:
        raise HTTPException(400, "Склад не знайдено")
    if not payload.items:
        raise HTTPException(400, "Немає позицій")
    try:
        mdate = date_cls.fromisoformat(payload.doc_date) if payload.doc_date else date_cls.today()
    except ValueError:
        mdate = date_cls.today()

    doc = None
    if not no_doc:
        doc = CustodyDocument(
            operation="receipt", form=payload.form, doc_number=payload.doc_number,
            doc_date=payload.doc_date, date_operation=payload.doc_date,
            to_warehouse_id=to.id, counterparty=payload.counterparty, basis=payload.basis,
            service_id=payload.service_id, op_type_id=payload.op_type_id,
            status="draft", extra_data={}, created_by=user.id,
        )
        db.add(doc)
        db.flush()

    for it in payload.items:
        if it.new_nomenclature:
            nn = it.new_nomenclature
            check_nomenclature_cud(user, nn.service_id)      # ACL: чужу службу не можна
            nom = Nomenclature(
                name=nn.name, service_id=nn.service_id, category=nn.category,
                is_official=nn.is_official, is_serialized=nn.is_serialized,
                unit_of_measure=nn.unit_of_measure, code=nn.code, price=nn.price,
            )
            db.add(nom); db.flush()
        elif it.nomenclature_id:
            nom = db.get(Nomenclature, it.nomenclature_id)
            if not nom:
                raise HTTPException(400, f"Номенклатуру {it.nomenclature_id} не знайдено")
        else:
            raise HTTPException(400, "Позиція без номенклатури")
        _check_receipt(user, to.id, nom)

        is_official = nom.is_official                        # тип обліку — з картки
        instance = None
        if nom.is_serialized:
            if not it.serial_no:
                raise HTTPException(400, f"«{nom.name}»: потрібен серійний номер")
            if db.query(Instance).filter(Instance.serial_no == it.serial_no).first():
                raise HTTPException(400, f"Серійний {it.serial_no} уже існує")
            instance = Instance(
                nomenclature_id=nom.id, serial_no=it.serial_no, card_number=it.card_number,
                current_warehouse_id=to.id, is_official=is_official,
            )
            db.add(instance); db.flush()
            qty = Decimal(1)
        else:
            qty = Decimal(it.quantity or 0)
            if qty <= 0:
                raise HTTPException(400, f"«{nom.name}»: кількість має бути > 0")

        db.add(CustodyMovement(
            date=mdate, type="receipt", nomenclature_id=nom.id,
            from_warehouse_id=None, to_warehouse_id=to.id,
            instance_id=instance.id if instance else None,
            quantity=qty, is_official=is_official, card_number=it.card_number,
            document_id=doc.id if doc else None, created_by=user.id,
        ))

    if doc is None:                       # НДМ / без документа — лише рухи
        db.commit()
        return {"received": len(payload.items), "no_document": True}

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

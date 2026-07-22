"""v2 custody ledger — рухи склад→склад + баланси.

Баланс несерійного = SUM(qty у склад) − SUM(qty зі складу) по
(warehouse, nomenclature, is_official). Серійний залишок = фільтр instances
по current_warehouse. Видача особі (assignments) — окремий шар, custody не рухає.

Валідація — жорстка (400 при недостатності / неправильному складі екземпляра).
"""
from datetime import date as date_cls
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models import CustodyMovement, Instance, Nomenclature, User, Warehouse
from app.schemas import CustodyMovementCreate

router = APIRouter(prefix="/api/custody", tags=["custody"])

MOVEMENT_TYPES = {"receipt", "transfer", "writeoff"}


def balance_of(db: Session, warehouse_id: int, nomenclature_id: int, is_official: bool) -> Decimal:
    """Net non-serial balance for one (warehouse, nomenclature, is_official)."""
    q_in = (
        db.query(func.coalesce(func.sum(CustodyMovement.quantity), 0))
        .filter(CustodyMovement.to_warehouse_id == warehouse_id,
                CustodyMovement.nomenclature_id == nomenclature_id,
                CustodyMovement.is_official.is_(is_official),
                CustodyMovement.instance_id.is_(None))
        .scalar()
    )
    q_out = (
        db.query(func.coalesce(func.sum(CustodyMovement.quantity), 0))
        .filter(CustodyMovement.from_warehouse_id == warehouse_id,
                CustodyMovement.nomenclature_id == nomenclature_id,
                CustodyMovement.is_official.is_(is_official),
                CustodyMovement.instance_id.is_(None))
        .scalar()
    )
    return Decimal(q_in or 0) - Decimal(q_out or 0)


def _mv_dict(m: CustodyMovement) -> dict:
    return {
        "id": m.id,
        "date": m.date.isoformat() if m.date else None,
        "type": m.type,
        "from_warehouse_id": m.from_warehouse_id,
        "to_warehouse_id": m.to_warehouse_id,
        "nomenclature_id": m.nomenclature_id,
        "instance_id": m.instance_id,
        "quantity": str(m.quantity),
        "is_official": m.is_official,
    }


@router.get("/movements")
def list_movements(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.query(CustodyMovement).order_by(CustodyMovement.date.desc(), CustodyMovement.id.desc()).all()
    return [_mv_dict(m) for m in rows]


@router.post("/movements", status_code=status.HTTP_201_CREATED)
def create_movement(payload: CustodyMovementCreate, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    if payload.type not in MOVEMENT_TYPES:
        raise HTTPException(400, f"Тип має бути з {MOVEMENT_TYPES}")
    frm, to = payload.from_warehouse_id, payload.to_warehouse_id
    if frm is None and to is None:
        raise HTTPException(400, "Потрібен хоча б один склад")
    if frm is not None and frm == to:
        raise HTTPException(400, "Склади відправника й отримувача збігаються")
    for wid in (frm, to):
        if wid is not None and not db.get(Warehouse, wid):
            raise HTTPException(400, "Склад не знайдено")

    nom = db.get(Nomenclature, payload.nomenclature_id)
    if not nom:
        raise HTTPException(400, "Номенклатуру не знайдено")

    if nom.is_serialized:
        if not payload.instance_id:
            raise HTTPException(400, "Серійний рух потребує екземпляр")
        inst = db.get(Instance, payload.instance_id)
        if not inst or inst.nomenclature_id != nom.id:
            raise HTTPException(400, "Екземпляр не відповідає номенклатурі")
        quantity = Decimal(1)
        is_official = inst.is_official
        # Location check: екземпляр має бути на складі-відправнику
        if frm is not None and inst.current_warehouse_id != frm:
            raise HTTPException(400, "Екземпляр не на цьому складі")
        if frm is None and inst.current_warehouse_id is not None:
            raise HTTPException(400, "Екземпляр уже розміщений")
    else:
        if payload.instance_id:
            raise HTTPException(400, "Несерійна номенклатура — без екземпляра")
        quantity = Decimal(payload.quantity or 0)
        if quantity <= 0:
            raise HTTPException(400, "Кількість має бути > 0")
        is_official = payload.is_official
        # Sufficiency check для transfer/writeoff
        if frm is not None:
            bal = balance_of(db, frm, nom.id, is_official)
            if bal < quantity:
                raise HTTPException(400, f"Недостатньо: є {bal}, потрібно {quantity}")

    mv = CustodyMovement(
        date=date_cls.fromisoformat(payload.date),
        type=payload.type,
        from_warehouse_id=frm,
        to_warehouse_id=to,
        nomenclature_id=nom.id,
        instance_id=payload.instance_id,
        quantity=quantity,
        is_official=is_official,
        signed_by_person_id=payload.signed_by_person_id,
        created_by=user.id,
    )
    db.add(mv)
    # Денормалізація: оновлюємо поточне розташування екземпляра
    if nom.is_serialized:
        inst.current_warehouse_id = to  # None для writeoff
    db.commit()
    db.refresh(mv)
    return _mv_dict(mv)


@router.get("/balances")
def balances(warehouse_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Несерійні залишки складу, згруповані по (nomenclature, is_official)."""
    rows_in = (
        db.query(CustodyMovement.nomenclature_id, CustodyMovement.is_official,
                 func.coalesce(func.sum(CustodyMovement.quantity), 0))
        .filter(CustodyMovement.to_warehouse_id == warehouse_id, CustodyMovement.instance_id.is_(None))
        .group_by(CustodyMovement.nomenclature_id, CustodyMovement.is_official).all()
    )
    rows_out = (
        db.query(CustodyMovement.nomenclature_id, CustodyMovement.is_official,
                 func.coalesce(func.sum(CustodyMovement.quantity), 0))
        .filter(CustodyMovement.from_warehouse_id == warehouse_id, CustodyMovement.instance_id.is_(None))
        .group_by(CustodyMovement.nomenclature_id, CustodyMovement.is_official).all()
    )
    net: dict = {}
    for nid, off, qty in rows_in:
        net[(nid, off)] = net.get((nid, off), Decimal(0)) + Decimal(qty or 0)
    for nid, off, qty in rows_out:
        net[(nid, off)] = net.get((nid, off), Decimal(0)) - Decimal(qty or 0)

    out = []
    for (nid, off), qty in net.items():
        if qty > 0:
            nom = db.get(Nomenclature, nid)
            out.append({
                "nomenclature_id": nid,
                "name": nom.name if nom else None,
                "is_official": off,
                "qty": str(qty),
                "unit_of_measure": nom.unit_of_measure if nom else None,
                "price": str(nom.price) if nom and nom.price is not None else None,
            })
    out.sort(key=lambda x: (x["name"] or "", not x["is_official"]))
    return out


@router.get("/serial")
def serial_at_warehouse(warehouse_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Серійні екземпляри, що зараз на складі."""
    rows = db.query(Instance).filter(Instance.current_warehouse_id == warehouse_id).all()
    out = []
    for it in rows:
        nom = db.get(Nomenclature, it.nomenclature_id)
        out.append({
            "instance_id": it.id,
            "serial_no": it.serial_no,
            "nomenclature_id": it.nomenclature_id,
            "name": nom.name if nom else None,
            "is_official": it.is_official,
        })
    out.sort(key=lambda x: (x["name"] or "", x["serial_no"]))
    return out

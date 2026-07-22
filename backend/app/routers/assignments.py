"""v2 assignments — видача особовому складу.

Фізичне тримання в межах подотчіту складу підрозділу. НЕ рухає custody:
видача бійцю не знімає майно з балансу складу, лише фіксує, хто тримає.
"""
from datetime import date as date_cls
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    Assignment, Group, Instance, Nomenclature, Person, User, Warehouse,
)
from app.routers.custody import balance_of
from app.schemas import AssignmentCreate, AssignmentReturn

router = APIRouter(prefix="/api/assignments", tags=["assignments"])


def _active_issued(db: Session, warehouse_id: int, nomenclature_id: int, is_official: bool) -> Decimal:
    total = (
        db.query(func.coalesce(func.sum(Assignment.quantity), 0))
        .filter(Assignment.warehouse_id == warehouse_id,
                Assignment.nomenclature_id == nomenclature_id,
                Assignment.is_official.is_(is_official),
                Assignment.instance_id.is_(None),
                Assignment.returned_date.is_(None))
        .scalar()
    )
    return Decimal(total or 0)


def _dict(a: Assignment) -> dict:
    return {
        "id": a.id,
        "warehouse_id": a.warehouse_id,
        "person_id": a.person_id,
        "nomenclature_id": a.nomenclature_id,
        "instance_id": a.instance_id,
        "quantity": str(a.quantity),
        "is_official": a.is_official,
        "issued_date": a.issued_date.isoformat() if a.issued_date else None,
        "returned_date": a.returned_date.isoformat() if a.returned_date else None,
        "is_active": a.returned_date is None,
    }


@router.get("")
def list_assignments(
    warehouse_id: Optional[int] = None,
    person_id: Optional[int] = None,
    active: bool = True,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Assignment)
    if warehouse_id is not None:
        q = q.filter(Assignment.warehouse_id == warehouse_id)
    if person_id is not None:
        q = q.filter(Assignment.person_id == person_id)
    if active:
        q = q.filter(Assignment.returned_date.is_(None))
    return [_dict(a) for a in q.order_by(Assignment.issued_date.desc(), Assignment.id.desc()).all()]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_assignment(payload: AssignmentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    wh = db.get(Warehouse, payload.warehouse_id)
    if not wh:
        raise HTTPException(400, "Склад не знайдено")
    if wh.type != "unit":
        raise HTTPException(400, "Видача лише зі складу підрозділу")
    person = db.get(Person, payload.person_id)
    if not person:
        raise HTTPException(400, "Особу не знайдено")
    if person.unit_id is None or person.unit_id != wh.unit_id:
        raise HTTPException(400, "Особа з іншого підрозділу")
    nom = db.get(Nomenclature, payload.nomenclature_id)
    if not nom:
        raise HTTPException(400, "Номенклатуру не знайдено")

    issued_date = date_cls.fromisoformat(payload.issued_date) if payload.issued_date else date_cls.today()

    if nom.is_serialized:
        if not payload.instance_id:
            raise HTTPException(400, "Серійна видача потребує екземпляр")
        inst = db.get(Instance, payload.instance_id)
        if not inst or inst.nomenclature_id != nom.id:
            raise HTTPException(400, "Екземпляр не відповідає номенклатурі")
        if inst.current_warehouse_id != wh.id:
            raise HTTPException(400, "Екземпляр не на цьому складі")
        dup = db.query(Assignment).filter(
            Assignment.instance_id == inst.id, Assignment.returned_date.is_(None)
        ).first()
        if dup:
            raise HTTPException(400, "Екземпляр уже на руках")
        quantity = Decimal(1)
        is_official = inst.is_official
    else:
        if payload.instance_id:
            raise HTTPException(400, "Несерійна номенклатура — без екземпляра")
        quantity = Decimal(payload.quantity or 0)
        if quantity <= 0:
            raise HTTPException(400, "Кількість має бути > 0")
        is_official = payload.is_official
        bal = balance_of(db, wh.id, nom.id, is_official)
        issued = _active_issued(db, wh.id, nom.id, is_official)
        if issued + quantity > bal:
            free = bal - issued
            raise HTTPException(400, f"Видано більше, ніж є: вільно {free} з {bal}")

    a = Assignment(
        warehouse_id=wh.id, person_id=person.id, nomenclature_id=nom.id,
        instance_id=payload.instance_id, quantity=quantity, is_official=is_official,
        issued_date=issued_date, created_by=user.id,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return _dict(a)


@router.post("/{aid}/return")
def return_assignment(aid: int, payload: AssignmentReturn | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    payload = payload or AssignmentReturn()
    a = db.get(Assignment, aid)
    if not a:
        raise HTTPException(404, "Not found")
    if a.returned_date is not None:
        raise HTTPException(400, "Уже повернено")
    a.returned_date = date_cls.fromisoformat(payload.returned_date) if payload.returned_date else date_cls.today()
    a.returned_by = user.id
    db.commit()
    db.refresh(a)
    return _dict(a)


@router.get("/group/{group_id}")
def group_holdings(group_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Активні видачі всієї групи (командир + бійці): агрегація по особах."""
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(404, "Групу не знайдено")
    members = db.query(Person).filter(Person.group_id == group_id).all()
    member_ids = [p.id for p in members]
    result = {"group_id": group_id, "name": group.name, "members": []}
    if not member_ids:
        return result
    rows = (
        db.query(Assignment)
        .filter(Assignment.person_id.in_(member_ids), Assignment.returned_date.is_(None))
        .all()
    )
    by_person: dict = {p.id: {"person_id": p.id,
                              "is_commander": group.commander_id == p.id,
                              "items": []} for p in members}
    for a in rows:
        nom = db.get(Nomenclature, a.nomenclature_id)
        by_person[a.person_id]["items"].append({
            "nomenclature_id": a.nomenclature_id,
            "name": nom.name if nom else None,
            "instance_id": a.instance_id,
            "quantity": str(a.quantity),
            "is_official": a.is_official,
        })
    result["members"] = list(by_person.values())
    result["total_items"] = len(rows)
    return result

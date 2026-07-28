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

from app.acl import check_assignment_create, is_admin, scope_assignments
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
    user: User = Depends(get_current_user),
):
    q = scope_assignments(db.query(Assignment), user)
    if warehouse_id is not None:
        q = q.filter(Assignment.warehouse_id == warehouse_id)
    if person_id is not None:
        q = q.filter(Assignment.person_id == person_id)
    if active:
        q = q.filter(Assignment.returned_date.is_(None))
    out = []
    for a in q.order_by(Assignment.issued_date.desc(), Assignment.id.desc()).all():
        d = _dict(a)
        nom = db.get(Nomenclature, a.nomenclature_id)
        wh = db.get(Warehouse, a.warehouse_id)
        d["nomenclature_name"] = nom.name if nom else None
        d["unit_of_measure"] = nom.unit_of_measure if nom else None
        d["serial_no"] = db.get(Instance, a.instance_id).serial_no if a.instance_id else None
        d["warehouse_name"] = wh.name if wh else None
        out.append(d)
    return out


def issue_row(db: Session, user: User, warehouse_id: int, person_id: int,
              nomenclature_id: int, instance_id: Optional[int],
              quantity: Optional[Decimal], issued_date) -> Assignment:
    """Validate + create one Assignment (NO commit). Shared by the assignments
    endpoint and by movement flows that issue on transfer, so the rules live in
    one place. Caller commits."""
    wh = db.get(Warehouse, warehouse_id)
    if not wh:
        raise HTTPException(400, "Склад не знайдено")
    nom = db.get(Nomenclature, nomenclature_id)
    if not nom:
        raise HTTPException(400, "Номенклатуру не знайдено")

    # НДМ (не облікове) видається напряму зі складу СЛУЖБИ будь-якій особі
    # (без прив'язки до підрозділу). Облікове — лише зі складу підрозділу.
    ndm_direct = (not nom.is_official) and wh.type == "service"
    if not ndm_direct and wh.type != "unit":
        raise HTTPException(400, "Видача лише зі складу підрозділу")

    if ndm_direct:
        if not (is_admin(user) or (user.role == "service" and user.service_id == wh.service_id)):
            raise HTTPException(403, "Немає прав видавати з цього складу")
    else:
        check_assignment_create(user, wh.id)  # ACL: mvo свого складу / admin

    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(400, "Особу не знайдено")
    if not ndm_direct and (person.unit_id is None or person.unit_id != wh.unit_id):
        raise HTTPException(400, "Особа з іншого підрозділу")

    if nom.is_serialized:
        if not instance_id:
            raise HTTPException(400, "Серійна видача потребує екземпляр")
        inst = db.get(Instance, instance_id)
        if not inst or inst.nomenclature_id != nom.id:
            raise HTTPException(400, "Екземпляр не відповідає номенклатурі")
        if inst.current_warehouse_id != wh.id:
            raise HTTPException(400, "Екземпляр не на цьому складі")
        dup = db.query(Assignment).filter(
            Assignment.instance_id == inst.id, Assignment.returned_date.is_(None)
        ).first()
        if dup:
            raise HTTPException(400, "Екземпляр уже на руках")
        qty = Decimal(1)
        is_official = inst.is_official
    else:
        if instance_id:
            raise HTTPException(400, "Несерійна номенклатура — без екземпляра")
        qty = Decimal(quantity or 0)
        if qty <= 0:
            raise HTTPException(400, "Кількість має бути > 0")
        is_official = nom.is_official  # тип обліку — з картки
        bal = balance_of(db, wh.id, nom.id, is_official)
        issued = _active_issued(db, wh.id, nom.id, is_official)
        if issued + qty > bal:
            free = bal - issued
            raise HTTPException(400, f"Видано більше, ніж є: вільно {free} з {bal}")

    a = Assignment(
        warehouse_id=wh.id, person_id=person.id, nomenclature_id=nom.id,
        instance_id=instance_id, quantity=qty, is_official=is_official,
        issued_date=issued_date, created_by=user.id,
    )
    db.add(a)
    return a


@router.post("", status_code=status.HTTP_201_CREATED)
def create_assignment(payload: AssignmentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    issued_date = date_cls.fromisoformat(payload.issued_date) if payload.issued_date else date_cls.today()
    a = issue_row(db, user, payload.warehouse_id, payload.person_id, payload.nomenclature_id,
                  payload.instance_id, payload.quantity, issued_date)
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
    def _pname(p):
        return " ".join(x for x in [p.last_name, p.first_name] if x) or p.callsign or f"#{p.id}"
    by_person: dict = {p.id: {"person_id": p.id, "person_name": _pname(p),
                              "is_commander": group.commander_id == p.id,
                              "items": []} for p in members}
    for a in rows:
        nom = db.get(Nomenclature, a.nomenclature_id)
        by_person[a.person_id]["items"].append({
            "nomenclature_id": a.nomenclature_id,
            "name": nom.name if nom else None,
            "instance_id": a.instance_id,
            "serial_no": db.get(Instance, a.instance_id).serial_no if a.instance_id else None,
            "quantity": str(a.quantity),
            "is_official": a.is_official,
        })
    result["members"] = list(by_person.values())
    result["total_items"] = len(rows)
    return result

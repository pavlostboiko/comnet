"""v2 structure — units, groups, warehouses, mvo.

Warehouses are NOT created directly: exactly one is auto-created per service
and per unit (see ensure_warehouse_for_*), and it's stable — bound to the
service/unit, never to a person. МВО rotation touches only `mvo`.
"""
from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models import Group, Mvo, Person, Service, Unit, User, Warehouse
from app.schemas import (
    GroupCreate, GroupRead, GroupUpdate, MvoCreate, MvoRead, MvoUpdate,
    UnitCreate, UnitRead, UnitUpdate, WarehouseRead, WarehouseUpdate,
)

router = APIRouter(prefix="/api/structure", tags=["structure"])


# ── Warehouse auto-create helpers (imported by settings.py too) ──────────────

def ensure_warehouse_for_service(db: Session, service: Service) -> Warehouse:
    wh = db.query(Warehouse).filter(Warehouse.service_id == service.id).first()
    if not wh:
        wh = Warehouse(name=f"Склад {service.name}", type="service", service_id=service.id)
        db.add(wh)
        db.flush()
    return wh


def ensure_warehouse_for_unit(db: Session, unit: Unit) -> Warehouse:
    wh = db.query(Warehouse).filter(Warehouse.unit_id == unit.id).first()
    if not wh:
        wh = Warehouse(name=f"Склад {unit.name}", type="unit", unit_id=unit.id)
        db.add(wh)
        db.flush()
    return wh


# ── Units ────────────────────────────────────────────────────────────────────

@router.get("/units", response_model=List[UnitRead])
def list_units(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Unit).order_by(Unit.name).all()


@router.post("/units", response_model=UnitRead, status_code=status.HTTP_201_CREATED)
def create_unit(payload: UnitCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if db.query(Unit).filter(Unit.name == payload.name).first():
        raise HTTPException(409, "Підрозділ з такою назвою вже існує")
    unit = Unit(**payload.model_dump())
    db.add(unit)
    db.flush()
    ensure_warehouse_for_unit(db, unit)  # auto-склад
    db.commit()
    db.refresh(unit)
    return unit


@router.put("/units/{unit_id}", response_model=UnitRead)
def update_unit(unit_id: int, payload: UnitUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    unit = db.get(Unit, unit_id)
    if not unit:
        raise HTTPException(404, "Not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(unit, field, value)
    db.commit()
    db.refresh(unit)
    return unit


@router.delete("/units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_unit(unit_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    unit = db.get(Unit, unit_id)
    if not unit:
        raise HTTPException(404, "Not found")
    db.delete(unit)  # CASCADE прибирає склад підрозділу
    db.commit()


# ── Groups ───────────────────────────────────────────────────────────────────

@router.get("/groups", response_model=List[GroupRead])
def list_groups(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Group).order_by(Group.name).all()


@router.post("/groups", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
def create_group(payload: GroupCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if not db.get(Unit, payload.unit_id):
        raise HTTPException(400, "Підрозділ не знайдено")
    if payload.commander_id and not db.get(Person, payload.commander_id):
        raise HTTPException(400, "Командира не знайдено")
    group = Group(**payload.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.put("/groups/{group_id}", response_model=GroupRead)
def update_group(group_id: int, payload: GroupUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(404, "Not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(group, field, value)
    db.commit()
    db.refresh(group)
    return group


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(404, "Not found")
    db.delete(group)
    db.commit()


# ── Warehouses (read-only — auto-created) ────────────────────────────────────

@router.get("/warehouses", response_model=List[WarehouseRead])
def list_warehouses(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Warehouse).order_by(Warehouse.name).all()


@router.put("/warehouses/{wid}", response_model=WarehouseRead)
def rename_warehouse(wid: int, payload: WarehouseUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Тільки перейменування — тип і прив'язка (служба/підрозділ) незмінні."""
    wh = db.get(Warehouse, wid)
    if not wh:
        raise HTTPException(404, "Склад не знайдено")
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "Назва не може бути порожньою")
    wh.name = name
    db.commit()
    db.refresh(wh)
    return wh


# ── МВО (temporal assignment journal) ────────────────────────────────────────

def _mvo_dict(m: Mvo) -> dict:
    return {
        "id": m.id,
        "warehouse_id": m.warehouse_id,
        "person_id": m.person_id,
        "from_date": m.from_date.isoformat() if m.from_date else None,
        "to_date": m.to_date.isoformat() if m.to_date else None,
    }


@router.get("/mvo")
def list_mvo(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.query(Mvo).order_by(Mvo.from_date.desc(), Mvo.id.desc()).all()
    return [_mvo_dict(m) for m in rows]


@router.post("/mvo", status_code=status.HTTP_201_CREATED)
def create_mvo(payload: MvoCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    wh = db.get(Warehouse, payload.warehouse_id)
    if not wh:
        raise HTTPException(400, "Склад не знайдено")
    if wh.type != "unit":
        raise HTTPException(400, "МВО призначається лише на склад підрозділу")
    if not db.get(Person, payload.person_id):
        raise HTTPException(400, "Особу не знайдено")
    from_date = date.fromisoformat(payload.from_date)
    to_date = date.fromisoformat(payload.to_date) if payload.to_date else None
    if to_date and to_date < from_date:
        raise HTTPException(400, "Некоректний період")
    # Максимум один діючий (to_date IS NULL) на склад
    if to_date is None:
        active = db.query(Mvo).filter(
            Mvo.warehouse_id == wh.id, Mvo.to_date.is_(None)
        ).first()
        if active:
            raise HTTPException(409, "Уже є діючий МВО на цьому складі")
    row = Mvo(warehouse_id=wh.id, person_id=payload.person_id, from_date=from_date, to_date=to_date)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _mvo_dict(row)


@router.put("/mvo/{mvo_id}")
def update_mvo(mvo_id: int, payload: MvoUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Ротація: проставити to_date діючому запису (потім POST новий)."""
    row = db.get(Mvo, mvo_id)
    if not row:
        raise HTTPException(404, "Not found")
    if payload.to_date is not None:
        to_date = date.fromisoformat(payload.to_date)
        if to_date < row.from_date:
            raise HTTPException(400, "Некоректний період")
        row.to_date = to_date
    db.commit()
    db.refresh(row)
    return _mvo_dict(row)

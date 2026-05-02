from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import OpType, OpTypeDetail, Person, UnitSettings, User
from app.schemas import (
    OpTypeCreate, OpTypeDetailCreate, OpTypeDetailRead, OpTypeDetailUpdate,
    OpTypeRead, OpTypeUpdate, PersonCreate, PersonRead, PersonUpdate,
    UnitSettingsRead, UnitSettingsUpdate,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ── Unit ──────────────────────────────────────────────────────────────────────

@router.get("/unit", response_model=UnitSettingsRead)
def get_unit(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    row = db.query(UnitSettings).first()
    if not row:
        row = UnitSettings()
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.put("/unit", response_model=UnitSettingsRead)
def update_unit(
    payload: UnitSettingsUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    row = db.query(UnitSettings).first()
    if not row:
        row = UnitSettings()
        db.add(row)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


# ── Op Types ──────────────────────────────────────────────────────────────────

@router.get("/op-types", response_model=List[OpTypeRead])
def get_op_types(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(OpType).order_by(OpType.name).all()


@router.post("/op-types", response_model=OpTypeRead, status_code=status.HTTP_201_CREATED)
def create_op_type(
    payload: OpTypeCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    row = OpType(name=payload.name)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/op-types/{op_type_id}", response_model=OpTypeRead)
def update_op_type(
    op_type_id: int,
    payload: OpTypeUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    row = db.get(OpType, op_type_id)
    if not row:
        raise HTTPException(status_code=404, detail="OpType not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/op-types/{op_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_op_type(
    op_type_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    row = db.get(OpType, op_type_id)
    if not row:
        raise HTTPException(status_code=404, detail="OpType not found")
    db.delete(row)
    db.commit()


# ── Op Type Details ───────────────────────────────────────────────────────────

@router.get("/op-types-detail", response_model=List[OpTypeDetailRead])
def get_op_type_details(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(OpTypeDetail).order_by(OpTypeDetail.name).all()


@router.post(
    "/op-types-detail",
    response_model=OpTypeDetailRead,
    status_code=status.HTTP_201_CREATED,
)
def create_op_type_detail(
    payload: OpTypeDetailCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    row = OpTypeDetail(op_type_id=payload.op_type_id, name=payload.name)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/op-types-detail/{detail_id}", response_model=OpTypeDetailRead)
def update_op_type_detail(
    detail_id: int,
    payload: OpTypeDetailUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    row = db.get(OpTypeDetail, detail_id)
    if not row:
        raise HTTPException(status_code=404, detail="OpTypeDetail not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/op-types-detail/{detail_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_op_type_detail(
    detail_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    row = db.get(OpTypeDetail, detail_id)
    if not row:
        raise HTTPException(status_code=404, detail="OpTypeDetail not found")
    db.delete(row)
    db.commit()


# ── Persons ───────────────────────────────────────────────────────────────────

@router.get("/persons", response_model=List[PersonRead])
def get_persons(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Person).order_by(Person.last_name).all()


@router.post("/persons", response_model=PersonRead, status_code=status.HTTP_201_CREATED)
def create_person(
    payload: PersonCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    row = Person(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/persons/{person_id}", response_model=PersonRead)
def get_person(
    person_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    row = db.get(Person, person_id)
    if not row:
        raise HTTPException(status_code=404, detail="Person not found")
    return row


@router.put("/persons/{person_id}", response_model=PersonRead)
def update_person(
    person_id: int,
    payload: PersonUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    row = db.get(Person, person_id)
    if not row:
        raise HTTPException(status_code=404, detail="Person not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/persons/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(
    person_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    row = db.get(Person, person_id)
    if not row:
        raise HTTPException(status_code=404, detail="Person not found")
    db.delete(row)
    db.commit()

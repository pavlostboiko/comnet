"""v2 nomenclature — типи майна + серійні екземпляри.

Nomenclature = «АК-74 взагалі». Instances — тільки для is_serialized=true.
Несерійне живе кількістю в рухах/балансах (Фаза 3).
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.acl import check_nomenclature_cud
from app.auth import get_current_user
from app.database import get_db
from app.models import Instance, Nomenclature, Service, User, Warehouse
from app.schemas import (
    InstanceCreate, InstanceRead, NomenclatureCreate, NomenclatureRead,
    NomenclatureUpdate,
)

router = APIRouter(prefix="/api/nomenclature", tags=["nomenclature"])


def _get_or_404(db: Session, nid: int) -> Nomenclature:
    n = db.get(Nomenclature, nid)
    if not n:
        raise HTTPException(404, "Номенклатуру не знайдено")
    return n


@router.get("", response_model=List[NomenclatureRead])
def list_nomenclature(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Nomenclature).order_by(Nomenclature.name).all()


@router.post("", response_model=NomenclatureRead, status_code=status.HTTP_201_CREATED)
def create_nomenclature(payload: NomenclatureCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not db.get(Service, payload.service_id):
        raise HTTPException(400, "Службу не знайдено")
    check_nomenclature_cud(user, payload.service_id)
    n = Nomenclature(**payload.model_dump())
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


@router.put("/{nid}", response_model=NomenclatureRead)
def update_nomenclature(nid: int, payload: NomenclatureUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    n = _get_or_404(db, nid)
    check_nomenclature_cud(user, n.service_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("service_id") and not db.get(Service, data["service_id"]):
        raise HTTPException(400, "Службу не знайдено")
    # Не дозволяємо знімати серійність, якщо вже є екземпляри
    if data.get("is_serialized") is False and n.is_serialized:
        if db.query(Instance).filter(Instance.nomenclature_id == nid).first():
            raise HTTPException(400, "Є екземпляри — не можна зробити несерійним")
    for field, value in data.items():
        setattr(n, field, value)
    db.commit()
    db.refresh(n)
    return n


@router.delete("/{nid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_nomenclature(nid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    n = _get_or_404(db, nid)
    check_nomenclature_cud(user, n.service_id)
    db.delete(n)  # CASCADE прибирає instances
    db.commit()


# ── Instances (серійні екземпляри) ───────────────────────────────────────────

@router.get("/{nid}/instances", response_model=List[InstanceRead])
def list_instances(nid: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    _get_or_404(db, nid)
    return db.query(Instance).filter(Instance.nomenclature_id == nid).order_by(Instance.serial_no).all()


@router.post("/{nid}/instances", response_model=InstanceRead, status_code=status.HTTP_201_CREATED)
def create_instance(nid: int, payload: InstanceCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    n = _get_or_404(db, nid)
    check_nomenclature_cud(user, n.service_id)
    if not n.is_serialized:
        raise HTTPException(400, "Екземпляри лише для серійної номенклатури")
    if db.query(Instance).filter(Instance.serial_no == payload.serial_no).first():
        raise HTTPException(409, "Серійний номер уже існує")
    if payload.current_warehouse_id and not db.get(Warehouse, payload.current_warehouse_id):
        raise HTTPException(400, "Склад не знайдено")
    inst = Instance(nomenclature_id=nid, **payload.model_dump())
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


@router.delete("/{nid}/instances/{iid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_instance(nid: int, iid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    n = _get_or_404(db, nid)
    check_nomenclature_cud(user, n.service_id)
    inst = db.get(Instance, iid)
    if not inst or inst.nomenclature_id != nid:
        raise HTTPException(404, "Екземпляр не знайдено")
    db.delete(inst)
    db.commit()

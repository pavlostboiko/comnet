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

from app.acl import (
    check_movement_create, check_warehouse_read, is_admin, scope_movements,
)
from app.auth import get_current_user
from app.database import get_db
from app.models import (
    Assignment, CustodyMovement, Instance, Nomenclature, Person, User, Warehouse,
)
from app.schemas import CustodyMovementCreate, DocumentBatchCreate

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
        "doc_number": m.doc_number,
        "card_number": m.card_number,
    }


@router.get("/movements")
def list_movements(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = scope_movements(db.query(CustodyMovement), user)
    rows = q.order_by(CustodyMovement.date.desc(), CustodyMovement.id.desc()).all()
    return [_mv_dict(m) for m in rows]


@router.post("/movements", status_code=status.HTTP_201_CREATED)
def create_movement(payload: CustodyMovementCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
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
    check_movement_create(user, frm, nom)  # ACL

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
        is_official = nom.is_official  # тип обліку — з картки
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


@router.post("/document", status_code=status.HTTP_201_CREATED)
def create_document(payload: DocumentBatchCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Накладна на переміщення: N позицій зі складу-джерела на склад-отримувач
    одним номером. Валідація по кожній позиції; або всі проводяться, або жодна."""
    frm = db.get(Warehouse, payload.from_warehouse_id)
    to = db.get(Warehouse, payload.to_warehouse_id)
    if not frm or not to:
        raise HTTPException(400, "Склад не знайдено")
    if frm.id == to.id:
        raise HTTPException(400, "Склади збігаються")
    if not payload.items:
        raise HTTPException(400, "Немає позицій")
    date = date_cls.fromisoformat(payload.date)
    created = 0
    for it in payload.items:
        nom = db.get(Nomenclature, it.nomenclature_id)
        if not nom:
            raise HTTPException(400, f"Номенклатуру {it.nomenclature_id} не знайдено")
        check_movement_create(user, frm.id, nom)
        if nom.is_serialized:
            if not it.instance_id:
                raise HTTPException(400, f"«{nom.name}»: потрібен екземпляр")
            inst = db.get(Instance, it.instance_id)
            if not inst or inst.nomenclature_id != nom.id:
                raise HTTPException(400, f"«{nom.name}»: екземпляр не відповідає")
            if inst.current_warehouse_id != frm.id:
                raise HTTPException(400, f"«{nom.name}» ({inst.serial_no}): не на складі-джерелі")
            qty = Decimal(1)
        else:
            qty = Decimal(it.quantity or 0)
            if qty <= 0:
                raise HTTPException(400, f"«{nom.name}»: кількість має бути > 0")
            bal = balance_of(db, frm.id, nom.id, nom.is_official)
            if bal < qty:
                raise HTTPException(400, f"«{nom.name}»: недостатньо (є {bal}, треба {qty})")
        mv = CustodyMovement(
            date=date, type="transfer", nomenclature_id=nom.id,
            from_warehouse_id=frm.id, to_warehouse_id=to.id,
            instance_id=it.instance_id if nom.is_serialized else None,
            quantity=qty, is_official=nom.is_official,
            doc_number=payload.doc_number, created_by=user.id,
        )
        db.add(mv)
        if nom.is_serialized:
            inst.current_warehouse_id = to.id
        db.flush()
        created += 1
    db.commit()
    return {"created": created, "doc_number": payload.doc_number}


@router.get("/balances")
def balances(warehouse_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Несерійні залишки складу, згруповані по (nomenclature, is_official)."""
    check_warehouse_read(user, warehouse_id)
    svc_scope = user.service_id if (not is_admin(user) and user.role == "service") else None
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
            if svc_scope is not None and (not nom or nom.service_id != svc_scope):
                continue  # service бачить лише свою службу
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


@router.get("/totals")
def totals(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Сумарна кількість кожної номенклатури в системі (для списку «Майно»).
    Несерійне: сума ПОЗИТИВНИХ залишків по складах (як у балансах/«Де знаходиться»),
    щоб узгоджувалося з попапом навіть якщо надходження зайшло переміщенням.
    Серійне: кількість розміщених екземплярів."""
    # net per (nomenclature, warehouse)
    net: dict = {}
    for nid, wid, qty in (db.query(CustodyMovement.nomenclature_id, CustodyMovement.to_warehouse_id,
                                   func.coalesce(func.sum(CustodyMovement.quantity), 0))
                          .filter(CustodyMovement.instance_id.is_(None), CustodyMovement.to_warehouse_id.isnot(None))
                          .group_by(CustodyMovement.nomenclature_id, CustodyMovement.to_warehouse_id).all()):
        net[(nid, wid)] = net.get((nid, wid), Decimal(0)) + Decimal(qty or 0)
    for nid, wid, qty in (db.query(CustodyMovement.nomenclature_id, CustodyMovement.from_warehouse_id,
                                   func.coalesce(func.sum(CustodyMovement.quantity), 0))
                          .filter(CustodyMovement.instance_id.is_(None), CustodyMovement.from_warehouse_id.isnot(None))
                          .group_by(CustodyMovement.nomenclature_id, CustodyMovement.from_warehouse_id).all()):
        net[(nid, wid)] = net.get((nid, wid), Decimal(0)) - Decimal(qty or 0)

    out: dict = {}
    for (nid, _wid), qty in net.items():
        if qty > 0:                      # лише позитивні залишки складів
            out[nid] = out.get(nid, Decimal(0)) + qty
    # serial: placed instances
    for nid, cnt in (db.query(Instance.nomenclature_id, func.count(Instance.id))
                     .filter(Instance.current_warehouse_id.isnot(None))
                     .group_by(Instance.nomenclature_id).all()):
        out[nid] = out.get(nid, Decimal(0)) + Decimal(cnt or 0)
    return {str(nid): str(v) for nid, v in out.items() if v != 0}


@router.get("/where")
def where_is(nomenclature_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Де знаходиться конкретна номенклатура: розподіл по складах.
    Несерійне — кількість по (склад, держ/волонт); серійне — кожен екземпляр
    з поточним складом і на кому видано.

    ACL: admin — усе; service — лише своя служба (інакше 403); mvo — лише свій
    склад (розподіл звужується до нього); інші ролі — 403."""
    nom = db.get(Nomenclature, nomenclature_id)
    if not nom:
        raise HTTPException(404, "Номенклатуру не знайдено")

    only_warehouse = None  # для mvo — обмеження до свого складу
    if not is_admin(user):
        if user.role == "service":
            if user.service_id != nom.service_id:
                raise HTTPException(403, "Немає доступу до цієї номенклатури")
        elif user.role == "mvo" and user.warehouse_id:
            only_warehouse = user.warehouse_id
        else:
            raise HTTPException(403, "Немає доступу")

    def wh_name(wid):
        w = db.get(Warehouse, wid) if wid else None
        return w.name if w else None

    result = {"nomenclature_id": nom.id, "name": nom.name, "is_serialized": nom.is_serialized,
              "nonserial": [], "serial": []}

    if nom.is_serialized:
        q_inst = db.query(Instance).filter(
            Instance.nomenclature_id == nom.id, Instance.current_warehouse_id.isnot(None)
        )
        if only_warehouse is not None:
            q_inst = q_inst.filter(Instance.current_warehouse_id == only_warehouse)
        insts = q_inst.all()
        # holders: active assignments by instance
        holders = {
            a.instance_id: a.person_id
            for a in db.query(Assignment).filter(
                Assignment.instance_id.in_([i.id for i in insts]) if insts else False,
                Assignment.returned_date.is_(None),
            ).all()
        } if insts else {}
        for it in insts:
            pid = holders.get(it.id)
            person = db.get(Person, pid) if pid else None
            holder = None
            if person:
                holder = " ".join(x for x in [person.last_name, person.first_name] if x) or person.callsign
            result["serial"].append({
                "instance_id": it.id, "serial_no": it.serial_no, "card_number": it.card_number,
                "warehouse_id": it.current_warehouse_id, "warehouse_name": wh_name(it.current_warehouse_id),
                "is_official": it.is_official, "holder": holder,
            })
        result["serial"].sort(key=lambda x: (x["warehouse_name"] or "", x["serial_no"] or ""))
    else:
        rows_in = (
            db.query(CustodyMovement.to_warehouse_id, CustodyMovement.is_official,
                     func.coalesce(func.sum(CustodyMovement.quantity), 0))
            .filter(CustodyMovement.nomenclature_id == nom.id, CustodyMovement.instance_id.is_(None),
                    CustodyMovement.to_warehouse_id.isnot(None))
            .group_by(CustodyMovement.to_warehouse_id, CustodyMovement.is_official).all()
        )
        rows_out = (
            db.query(CustodyMovement.from_warehouse_id, CustodyMovement.is_official,
                     func.coalesce(func.sum(CustodyMovement.quantity), 0))
            .filter(CustodyMovement.nomenclature_id == nom.id, CustodyMovement.instance_id.is_(None),
                    CustodyMovement.from_warehouse_id.isnot(None))
            .group_by(CustodyMovement.from_warehouse_id, CustodyMovement.is_official).all()
        )
        net: dict = {}
        for wid, off, qty in rows_in:
            net[(wid, off)] = net.get((wid, off), Decimal(0)) + Decimal(qty or 0)
        for wid, off, qty in rows_out:
            net[(wid, off)] = net.get((wid, off), Decimal(0)) - Decimal(qty or 0)
        for (wid, off), qty in net.items():
            if qty > 0 and (only_warehouse is None or wid == only_warehouse):
                result["nonserial"].append({
                    "warehouse_id": wid, "warehouse_name": wh_name(wid),
                    "is_official": off, "qty": str(qty),
                })
        result["nonserial"].sort(key=lambda x: (x["warehouse_name"] or "", not x["is_official"]))
    return result


@router.get("/serial")
def serial_at_warehouse(warehouse_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Серійні екземпляри, що зараз на складі."""
    check_warehouse_read(user, warehouse_id)
    svc_scope = user.service_id if (not is_admin(user) and user.role == "service") else None
    rows = db.query(Instance).filter(Instance.current_warehouse_id == warehouse_id).all()
    out = []
    for it in rows:
        nom = db.get(Nomenclature, it.nomenclature_id)
        if svc_scope is not None and (not nom or nom.service_id != svc_scope):
            continue
        out.append({
            "instance_id": it.id,
            "serial_no": it.serial_no,
            "nomenclature_id": it.nomenclature_id,
            "name": nom.name if nom else None,
            "is_official": it.is_official,
        })
    out.sort(key=lambda x: (x["name"] or "", x["serial_no"]))
    return out

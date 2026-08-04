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
    check_movement_create, check_nomenclature_cud, check_warehouse_read, is_admin,
    scope_assignments, scope_movements, scope_point_events,
)
from app.auth import get_current_user
from app.custody_placement import place_instance
from app.custody_snapshot import doc_sort_key
from app.database import get_db
from app.point_events import log_point_change
from app.models import (
    Assignment, CustodyMovement, Instance, Nomenclature, NomenclaturePoint, Person,
    PointEvent, StoragePoint, User, Warehouse,
)
from app.schemas import CustodyMovementCreate, DocumentBatchCreate, StockPointSet

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


ISSUED_BLOCK = "Не можна відкликати: майно видане особі — спершу оформіть повернення"


def _point_names(db: Session, warehouse_id: int) -> dict:
    """{id точки: назва} для складу — щоб не смикати БД на кожен рядок."""
    return {p.id: p.name for p in db.query(StoragePoint).filter(
        StoragePoint.warehouse_id == warehouse_id).all()}


def issued_qty(db: Session, warehouse_id: int, nomenclature_id: int, is_official: bool) -> Decimal:
    """Скільки несерійного зі складу вже на руках (активні видачі)."""
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
        "document_id": m.document_id,
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
        place_instance(inst, to)        # None для writeoff; зміна складу скидає точку
    db.commit()
    db.refresh(mv)
    return _mv_dict(mv)


@router.delete("/movements/{mid}", status_code=status.HTTP_200_OK)
def delete_movement(mid: int, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    """Відкликати НЕПРОВЕДЕНИЙ рух (без документа): видалити леджер-рядок і
    відкотити розміщення (запис зникає з історії, ніби руху не було). Дозволено
    лише для `document_id IS NULL`. Серійне — тільки ОСТАННІЙ рух екземпляра
    (щоб не рвати ланцюг); склад перераховується з решти рухів (той самий
    `doc_sort_key`). Несерійне — блокуємо, якщо відкат зробив би баланс складу-
    отримувача від'ємним (майно вже розійшлося далі)."""
    mv = db.get(CustodyMovement, mid)
    if not mv:
        raise HTTPException(404, "Рух не знайдено")
    if mv.document_id is not None:
        raise HTTPException(400, "Рух у документі — спершу відкріпіть його від документа")
    nom = db.get(Nomenclature, mv.nomenclature_id)
    check_movement_create(user, mv.from_warehouse_id, nom)  # ACL

    if nom and nom.is_serialized and mv.instance_id:
        inst = db.get(Instance, mv.instance_id)
        all_mvs = db.query(CustodyMovement).filter(
            CustodyMovement.instance_id == mv.instance_id).all()
        key = lambda m: (m.date, doc_sort_key(m.doc_number), m.id)
        if max(all_mvs, key=key).id != mv.id:
            raise HTTPException(400, "Можна відкликати лише останній рух екземпляра")
        # Видача не рухає баланс, тож сама по собі відкат не блокує — але майно
        # на руках в особи, а рух повернув би його на попередній склад.
        if db.query(Assignment).filter(Assignment.instance_id == mv.instance_id,
                                       Assignment.returned_date.is_(None)).first():
            raise HTTPException(400, ISSUED_BLOCK)
        db.delete(mv)
        remaining = [m for m in all_mvs if m.id != mv.id]
        place_instance(inst, max(remaining, key=key).to_warehouse_id if remaining else None)
    else:
        if mv.to_warehouse_id is not None:
            bal = balance_of(db, mv.to_warehouse_id, mv.nomenclature_id, mv.is_official)
            if bal - mv.quantity < 0:
                raise HTTPException(400, "Не можна відкликати: майно вже розійшлося далі")
            # Видане особам лишається на складі-отримувачі — відкат не має
            # залазити в те, що вже на руках.
            if bal - mv.quantity < issued_qty(db, mv.to_warehouse_id, mv.nomenclature_id,
                                              mv.is_official):
                raise HTTPException(400, ISSUED_BLOCK)
        db.delete(mv)
    db.commit()
    return {"deleted": mid}


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
            place_instance(inst, to.id)
        db.flush()
        # Опційно: одразу видати особі (та сама транзакція — атомарно з рухом).
        # У накладну особа не пише — це окремий шар (assignments).
        if it.assign_person_id:
            from app.routers.assignments import issue_row  # lazy: уникнути циклічного імпорту
            issue_row(db, user, to.id, it.assign_person_id, nom.id,
                      it.instance_id if nom.is_serialized else None,
                      None if nom.is_serialized else qty, date)
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

    point_names = _point_names(db, warehouse_id)
    # Точка несерійного — одна на (картка, склад), незалежно від держ/волонт.
    nom_points = {p.nomenclature_id: p.storage_point_id for p in db.query(NomenclaturePoint)
                  .filter(NomenclaturePoint.warehouse_id == warehouse_id).all()}
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
                "storage_point_id": nom_points.get(nid),
                "storage_point": point_names.get(nom_points.get(nid)),
            })
    out.sort(key=lambda x: (x["name"] or "", not x["is_official"]))
    return out


@router.put("/stock-point")
def set_stock_point(payload: StockPointSet, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    """Точка зберігання НЕсерійного: одна на (картка, склад); `null` — прибрати.
    Кількість по точках не ділиться — це позначка «де воно лежить»."""
    check_warehouse_read(user, payload.warehouse_id)
    nom = db.get(Nomenclature, payload.nomenclature_id)
    if not nom:
        raise HTTPException(400, "Номенклатуру не знайдено")
    check_nomenclature_cud(user, nom.service_id)   # як для точки на екземплярі
    if nom.is_serialized:
        raise HTTPException(400, "Для серійного точка ставиться на екземплярі")
    row = db.query(NomenclaturePoint).filter(
        NomenclaturePoint.nomenclature_id == nom.id,
        NomenclaturePoint.warehouse_id == payload.warehouse_id).first()
    was_point = row.storage_point_id if row else None
    if payload.storage_point_id is None:
        if row:
            db.delete(row)
        log_point_change(db, nomenclature_id=nom.id, warehouse_id=payload.warehouse_id,
                         from_point_id=was_point, to_point_id=None, user=user)
        db.commit()
        return {"storage_point_id": None}
    point = db.get(StoragePoint, payload.storage_point_id)
    if not point or point.warehouse_id != payload.warehouse_id:
        raise HTTPException(400, "Точка не з цього складу")
    if row:
        row.storage_point_id = point.id
    else:
        db.add(NomenclaturePoint(nomenclature_id=nom.id, warehouse_id=payload.warehouse_id,
                                 storage_point_id=point.id))
    log_point_change(db, nomenclature_id=nom.id, warehouse_id=payload.warehouse_id,
                     from_point_id=was_point, to_point_id=point.id, user=user)
    db.commit()
    return {"storage_point_id": point.id}


@router.get("/totals")
def totals(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
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
    # service бачить лише свою службу (узгоджено зі списком «Майно»)
    if user.role == "service" and user.service_id:
        own = {nid for (nid,) in db.query(Nomenclature.id)
               .filter(Nomenclature.service_id == user.service_id)}
        out = {nid: v for nid, v in out.items() if nid in own}
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
                "is_official": it.is_official, "holder": holder, "note": it.note,
                "storage_point": (db.get(StoragePoint, it.storage_point_id).name
                                  if it.storage_point_id else None),
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


@router.get("/history")
def item_history(nomenclature_id: int, instance_id: Optional[int] = None,
                 db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Об'єднана історія майна: рухи склад↔склад + видачі/повернення особам,
    хронологічно (новіші зверху). ACL як у /where (service — своя служба;
    mvo — лише події, що торкаються його складу)."""
    nom = db.get(Nomenclature, nomenclature_id)
    if not nom:
        raise HTTPException(404, "Номенклатуру не знайдено")

    only_warehouse = None
    if not is_admin(user):
        if user.role == "service":
            if user.service_id != nom.service_id:
                raise HTTPException(403, "Немає доступу до цієї номенклатури")
        elif user.role == "mvo" and user.warehouse_id:
            only_warehouse = user.warehouse_id
        else:
            raise HTTPException(403, "Немає доступу")

    wh_cache: dict = {}
    def wh_name(wid):
        if not wid:
            return None
        if wid not in wh_cache:
            w = db.get(Warehouse, wid)
            wh_cache[wid] = w.name if w else None
        return wh_cache[wid]

    def serial_of(iid):
        if not iid:
            return None
        inst = db.get(Instance, iid)
        return inst.serial_no if inst else None

    def person_name(pid):
        p = db.get(Person, pid) if pid else None
        if not p:
            return None
        return " ".join(x for x in [p.last_name, p.first_name] if x) or p.callsign

    mq = db.query(CustodyMovement).filter(CustodyMovement.nomenclature_id == nom.id)
    aq = db.query(Assignment).filter(Assignment.nomenclature_id == nom.id)
    if instance_id:
        mq = mq.filter(CustodyMovement.instance_id == instance_id)
        aq = aq.filter(Assignment.instance_id == instance_id)

    events = []
    for m in mq.all():
        if only_warehouse is not None and only_warehouse not in (m.from_warehouse_id, m.to_warehouse_id):
            continue
        events.append({
            "date": m.date.isoformat() if m.date else None,
            "kind": "movement", "type": m.type,
            "from_warehouse": wh_name(m.from_warehouse_id),
            "to_warehouse": wh_name(m.to_warehouse_id),
            "qty": str(m.quantity), "serial_no": serial_of(m.instance_id),
            "card_number": m.card_number, "doc_number": m.doc_number,
            "source": "movement", "source_id": m.id, "created_at": m.created_at,
        })
    for a in aq.all():
        if only_warehouse is not None and a.warehouse_id != only_warehouse:
            continue
        serial = serial_of(a.instance_id)
        events.append({
            "date": a.issued_date.isoformat() if a.issued_date else None,
            "kind": "issued", "person": person_name(a.person_id),
            "warehouse": wh_name(a.warehouse_id), "qty": str(a.quantity),
            "serial_no": serial, "source": "assignment", "source_id": a.id,
            "created_at": a.created_at,
        })
        if a.returned_date is not None:
            events.append({
                "date": a.returned_date.isoformat(),
                "kind": "returned", "person": person_name(a.person_id),
                "warehouse": wh_name(a.warehouse_id), "qty": str(a.quantity),
                "serial_no": serial, "source": "assignment", "source_id": a.id,
                "created_at": a.created_at,
            })

    pq = db.query(PointEvent).filter(PointEvent.nomenclature_id == nom.id)
    if instance_id:
        pq = pq.filter(PointEvent.instance_id == instance_id)
    for p in pq.all():
        if only_warehouse is not None and p.warehouse_id != only_warehouse:
            continue
        events.append(_point_event_dict(p, nom, wh_name(p.warehouse_id), serial_of(p.instance_id)))

    # Порядок (новіші зверху): дата → номер накладної (пізніша зверху; важливо
    # для імпортованих рухів однієї дати) → час запису `created_at` (розрізняє
    # недокументовані події однієї дати, напр. переміщення vs видача в одній
    # транзакції) → id. `created_at` — ПІСЛЯ doc_sort_key, бо в імпорті created_at
    # ~однаковий і хронологію дає лише номер накладної (задача 10).
    events.sort(key=lambda e: (e["date"] is None, e["date"] or "",
                               doc_sort_key(e.get("doc_number")),
                               e["created_at"], e["source_id"]),
                reverse=True)
    return {"nomenclature_id": nom.id, "name": nom.name,
            "is_serialized": nom.is_serialized, "events": events}


def _point_event_dict(p: PointEvent, nom, warehouse_name, serial_no) -> dict:
    """Подія «переїхало в іншу точку» у форматі стрічки/історії картки."""
    return {
        "date": p.date.isoformat() if p.date else None,
        "kind": "point", "type": None,
        "nomenclature_id": p.nomenclature_id,
        "nomenclature_name": nom.name if nom else None,
        "from_warehouse": p.from_point_name, "to_warehouse": p.to_point_name,
        "warehouse": warehouse_name, "person": None,
        "qty": str(p.quantity) if p.quantity is not None else None,
        "is_official": nom.is_official if nom else None,
        "serial_no": serial_no, "card_number": None,
        "doc_number": None, "document_id": None,
        "source": "point_event", "source_id": p.id, "created_at": p.created_at,
    }


@router.get("/feed")
def history_feed(warehouse_id: Optional[int] = None, date_from: Optional[str] = None,
                 date_to: Optional[str] = None, limit: int = 500,
                 db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Загальна історія по всіх картках: рухи склад↔склад + видачі/повернення,
    хронологічно (новіші зверху) — те саме, що в картці майна, але по всій частині.

    Скоуп ролі як усюди (`scope_movements`/`scope_assignments`). Видача дає до
    двох подій (видано/повернуто), тож дати фільтруються по КОЖНІЙ події, а SQL
    лише грубо звужує вибірку."""
    d_from = date_cls.fromisoformat(date_from) if date_from else None
    d_to = date_cls.fromisoformat(date_to) if date_to else None

    mq = scope_movements(db.query(CustodyMovement), user)
    aq = scope_assignments(db.query(Assignment), user)
    pq = scope_point_events(db.query(PointEvent), user)
    if warehouse_id:
        mq = mq.filter((CustodyMovement.from_warehouse_id == warehouse_id)
                       | (CustodyMovement.to_warehouse_id == warehouse_id))
        aq = aq.filter(Assignment.warehouse_id == warehouse_id)
        pq = pq.filter(PointEvent.warehouse_id == warehouse_id)
    if d_from:
        mq = mq.filter(CustodyMovement.date >= d_from)
        aq = aq.filter((Assignment.issued_date >= d_from) | (Assignment.returned_date >= d_from))
        pq = pq.filter(PointEvent.date >= d_from)
    if d_to:
        mq = mq.filter(CustodyMovement.date <= d_to)
        aq = aq.filter((Assignment.issued_date <= d_to) | (Assignment.returned_date <= d_to))
        pq = pq.filter(PointEvent.date <= d_to)

    movements = mq.all()
    assignments = aq.all()
    point_events = pq.all()

    # Довідники разом, а не по рядку — інакше сотні запитів на сторінку.
    noms = {n.id: n for n in db.query(Nomenclature).all()}
    whs = {w.id: w.name for w in db.query(Warehouse).all()}
    inst_ids = {m.instance_id for m in movements if m.instance_id} | \
               {a.instance_id for a in assignments if a.instance_id} | \
               {p.instance_id for p in point_events if p.instance_id}
    serials = {i.id: i.serial_no for i in db.query(Instance).filter(Instance.id.in_(inst_ids))} \
        if inst_ids else {}
    person_ids = {a.person_id for a in assignments}
    persons = {p.id: (" ".join(x for x in [p.last_name, p.first_name] if x) or p.callsign)
               for p in db.query(Person).filter(Person.id.in_(person_ids))} if person_ids else {}

    def in_range(d):
        return not ((d_from and d < d_from) or (d_to and d > d_to))

    events = []
    for m in movements:
        nom = noms.get(m.nomenclature_id)
        events.append({
            "date": m.date.isoformat() if m.date else None,
            "kind": "movement", "type": m.type,
            "nomenclature_id": m.nomenclature_id, "nomenclature_name": nom.name if nom else None,
            "from_warehouse": whs.get(m.from_warehouse_id), "to_warehouse": whs.get(m.to_warehouse_id),
            "person": None, "qty": str(m.quantity), "is_official": m.is_official,
            "serial_no": serials.get(m.instance_id), "card_number": m.card_number,
            "doc_number": m.doc_number, "document_id": m.document_id,
            "source": "movement", "source_id": m.id, "created_at": m.created_at,
        })
    for a in assignments:
        nom = noms.get(a.nomenclature_id)
        base = {
            "type": None, "nomenclature_id": a.nomenclature_id,
            "nomenclature_name": nom.name if nom else None,
            "from_warehouse": None, "to_warehouse": whs.get(a.warehouse_id),
            "person": persons.get(a.person_id), "qty": str(a.quantity),
            "is_official": a.is_official, "serial_no": serials.get(a.instance_id),
            "card_number": None, "doc_number": None, "document_id": None,
            "source": "assignment", "source_id": a.id, "created_at": a.created_at,
        }
        if a.issued_date and in_range(a.issued_date):
            events.append({**base, "date": a.issued_date.isoformat(), "kind": "issued"})
        if a.returned_date and in_range(a.returned_date):
            events.append({**base, "date": a.returned_date.isoformat(), "kind": "returned"})

    for p in point_events:
        events.append(_point_event_dict(p, noms.get(p.nomenclature_id),
                                        whs.get(p.warehouse_id), serials.get(p.instance_id)))

    events.sort(key=lambda e: (e["date"] is None, e["date"] or "",
                               doc_sort_key(e.get("doc_number")),
                               e["created_at"], e["source_id"]),
                reverse=True)
    total = len(events)
    return {"events": events[:limit], "total": total, "limit": limit}


@router.get("/serial")
def serial_at_warehouse(warehouse_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Серійні екземпляри, що зараз на складі."""
    check_warehouse_read(user, warehouse_id)
    svc_scope = user.service_id if (not is_admin(user) and user.role == "service") else None
    rows = db.query(Instance).filter(Instance.current_warehouse_id == warehouse_id).all()
    point_names = _point_names(db, warehouse_id)
    out = []
    for it in rows:
        nom = db.get(Nomenclature, it.nomenclature_id)
        if svc_scope is not None and (not nom or nom.service_id != svc_scope):
            continue
        out.append({
            "instance_id": it.id,
            "serial_no": it.serial_no,
            "card_number": it.card_number,
            "nomenclature_id": it.nomenclature_id,
            "name": nom.name if nom else None,
            "is_official": it.is_official,
            "unit_of_measure": nom.unit_of_measure if nom else None,
            "price": str(nom.price) if nom and nom.price is not None else None,
            "note": it.note,
            "storage_point_id": it.storage_point_id,
            "storage_point": point_names.get(it.storage_point_id),
        })
    out.sort(key=lambda x: (x["name"] or "", x["serial_no"]))
    return out

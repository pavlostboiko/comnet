"""v2 Items import (Фаза 6).

Один файл Items → розкладається на v2-сутності (find-or-create по ходу):
  рядок → служба + номенклатура (+ instance якщо серійне)
        → склад підрозділу (з колонки «Де») → receipt-рух
        → якщо в «Де» є людина → assignment на неї.

Колонка «Де» = «<підрозділ> [людина]». Підрозділ визначається найдовшим
збігом з ІСНУЮЧИМИ підрозділами (тому їх варто завести до імпорту); решта = ПІБ.
is_official за замовчуванням True (державне).
"""
from datetime import date as date_cls
from decimal import Decimal
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.models import (
    Assignment, CustodyMovement, Instance, Nomenclature, Person, Service,
    Unit, User, Warehouse,
)
from app.routers.admin import _clean, _normalize_serial, _parse_decimal, _parse_date
from app.routers.structure import ensure_warehouse_for_service, ensure_warehouse_for_unit

router = APIRouter(prefix="/api/admin/v2", tags=["admin-v2"])

# Значення «Де», що означають «склад служби» (не підрозділ, не видано особі).
WAREHOUSE_TOKENS = {"склад", "на складі", "склад служби"}


def is_service_warehouse_location(raw) -> bool:
    return (str(raw).strip().lower() if raw is not None else "") in WAREHOUSE_TOKENS

# header → logical key
COLS = {
    "Назва": "name", "Товар": "name",
    "Служба": "service",
    "Категорія": "category",
    "Серійний номер": "serial",
    "Од. виміру": "uom", "Од.виміру": "uom",
    "Вартість": "price",
    "Кіл-сть": "qty", "Кількість": "qty",
    "Код номер": "code", "Код": "code",
    "Де": "location", "Де знаходиться": "location",
    "Дата видачі": "issued_at",
}


def _find_header_row(ws) -> Optional[int]:
    for row in ws.iter_rows(max_row=20):
        for cell in row:
            v = str(cell.value).strip() if cell.value else ""
            if v in ("Назва", "Товар"):
                return cell.row
    return None


def _col_map(ws, header_row: int) -> dict:
    m = {}
    for cell in ws[header_row]:
        raw = str(cell.value).strip() if cell.value else ""
        if raw in COLS:
            m[cell.column] = COLS[raw]
    return m


@router.post("/wipe", status_code=status.HTTP_200_OK)
def wipe_v2_inventory(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Скидає v2 інвентарний шар для повторного імпорту: видачі, рухи,
    екземпляри, номенклатуру. Довідники (служби/підрозділи/склади/особи)
    лишаються — імпорт їх find-or-create."""
    counts = {
        "assignments": db.query(Assignment).delete(synchronize_session=False),
        "custody_movements": db.query(CustodyMovement).delete(synchronize_session=False),
        "instances": db.query(Instance).delete(synchronize_session=False),
        "nomenclature": db.query(Nomenclature).delete(synchronize_session=False),
    }
    db.commit()
    return {"deleted": counts}


@router.post("/import/items", status_code=status.HTTP_200_OK)
def import_items_v2(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    try:
        wb = load_workbook(BytesIO(file.file.read()), data_only=True)
    except Exception as e:
        raise HTTPException(400, f"Не вдалось прочитати XLSX: {e}")
    ws = wb.active
    header_row = _find_header_row(ws)
    if not header_row:
        raise HTTPException(400, "Не знайдено заголовок «Назва»/«Товар»")
    cmap = _col_map(ws, header_row)

    # Items = КАТАЛОГ: лише номенклатура + серійні екземпляри. Розміщення на
    # складах (баланси) робить окремий імпорт Переміщень (рішення 2026-07-24),
    # щоб не подвоювати. Колонка «Де» тут ігнорується.
    services = {s.name.strip().lower(): s for s in db.query(Service).all()}
    noms = {(n.name.strip().lower(), n.service_id): n for n in db.query(Nomenclature).all()}

    counts = {"rows": 0, "nomenclature": 0, "instances": 0, "services_created": 0}
    errors = []

    def get_service(name):
        key = name.strip().lower()
        s = services.get(key)
        if not s:
            s = Service(name=name.strip())
            db.add(s); db.flush()
            ensure_warehouse_for_service(db, s)  # склад служби знадобиться Переміщенням
            services[key] = s
            counts["services_created"] += 1
        return s

    def get_nomenclature(name, service, is_serial, uom, price, code, category):
        key = (name.strip().lower(), service.id)
        n = noms.get(key)
        if not n:
            n = Nomenclature(name=name.strip(), service_id=service.id, category=category,
                             is_serialized=is_serial, unit_of_measure=uom, price=price, code=code)
            db.add(n); db.flush()
            noms[key] = n
            counts["nomenclature"] += 1
        return n

    def col(row, key):
        for c, k in cmap.items():
            if k == key:
                return row[c - 1].value
        return None

    for row in ws.iter_rows(min_row=header_row + 1):
        name = _clean(col(row, "name"))
        if not name:
            continue
        counts["rows"] += 1
        try:
            svc_name = _clean(col(row, "service"))
            if not svc_name:
                errors.append(f"«{name}»: порожня служба — пропущено")
                continue
            service = get_service(svc_name)
            serial = _normalize_serial(col(row, "serial"))
            is_serial = serial is not None
            nom = get_nomenclature(
                name, service, is_serial,
                _clean(col(row, "uom")), _parse_decimal(col(row, "price")), _clean(col(row, "code")),
                _clean(col(row, "category")),
            )
            # серійний екземпляр — без розміщення (склад заповнить Переміщення)
            if is_serial and not db.query(Instance).filter(Instance.serial_no == serial).first():
                db.add(Instance(nomenclature_id=nom.id, serial_no=serial, is_official=True))
                counts["instances"] += 1
        except Exception as e:
            errors.append(f"«{name}»: {e}")

    db.commit()
    return {**counts, "errors": errors}


# ── Переміщення (custody movements) — жорсткий layout v1 ─────────────────────

MV_COLS = {
    "entry_date": 0, "item_name": 1, "unit_of_measure": 3, "qty_in": 5,
    "qty_out": 6, "from_unit": 7, "to_unit": 8, "doc_date": 12, "doc_number": 13,
    "serial_number": 15, "price": 19, "service": 20,
}


@router.post("/import/movements", status_code=status.HTTP_200_OK)
def import_movements_v2(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Файл Переміщень (той самий layout, що v1) → custody_movements.
    from_unit/to_unit резолвляться у склади: «склад»/назва служби → склад служби,
    інакше → склад підрозділу (find-or-create). Історичні дані НЕ валідуються
    (вставляються як є); поточне розташування серійного = останній to-склад."""
    try:
        wb = load_workbook(BytesIO(file.file.read()), data_only=True)
    except Exception as e:
        raise HTTPException(400, f"Не вдалось прочитати XLSX: {e}")
    ws = wb.active

    services = {s.name.strip().lower(): s for s in db.query(Service).all()}
    units = {u.name.strip().lower(): u for u in db.query(Unit).all()}
    noms = {(n.name.strip().lower(), n.service_id): n for n in db.query(Nomenclature).all()}

    counts = {"rows": 0, "movements": 0, "skipped": 0,
              "services_created": 0, "units_created": 0, "instances_created": 0}
    errors = []

    def get_service(name):
        key = name.strip().lower()
        s = services.get(key)
        if not s:
            s = Service(name=name.strip()); db.add(s); db.flush()
            ensure_warehouse_for_service(db, s)
            services[key] = s; counts["services_created"] += 1
        return s

    def get_unit(name):
        key = name.strip().lower()
        u = units.get(key)
        if not u:
            u = Unit(name=name.strip()); db.add(u); db.flush()
            ensure_warehouse_for_unit(db, u)
            units[key] = u; counts["units_created"] += 1
        return u

    def wh_of_service(s):
        return db.query(Warehouse).filter(Warehouse.service_id == s.id).first()

    def wh_of_unit(u):
        return db.query(Warehouse).filter(Warehouse.unit_id == u.id).first()

    def resolve_wh(name, service):
        s = (name or "").strip()
        if not s:
            return None  # зовні (надходження/списання)
        if is_service_warehouse_location(s):        # «склад» → склад цієї служби
            return wh_of_service(service)
        if s.lower() in services:                   # назва служби → її склад
            return wh_of_service(services[s.lower()])
        return wh_of_unit(get_unit(s))              # інакше — склад підрозділу

    def get_nomenclature(name, service, is_serial, uom, price):
        key = (name.strip().lower(), service.id)
        n = noms.get(key)
        if not n:
            n = Nomenclature(name=name.strip(), service_id=service.id,
                             is_serialized=is_serial, unit_of_measure=uom, price=price)
            db.add(n); db.flush(); noms[key] = n
        return n

    def mc(row, key):
        idx = MV_COLS[key]
        return row[idx].value if idx < len(row) else None

    for i, row in enumerate(ws.iter_rows(min_row=3, values_only=False), start=3):
        cells = row
        name = _clean(mc(cells, "item_name"))
        if not name:
            continue
        counts["rows"] += 1
        try:
            svc_name = _clean(mc(cells, "service"))
            if not svc_name:
                counts["skipped"] += 1
                errors.append(f"рядок {i} «{name}»: порожня служба")
                continue
            service = get_service(svc_name)
            serial = _normalize_serial(mc(cells, "serial_number"))
            is_serial = serial is not None
            uom = _clean(mc(cells, "unit_of_measure"))
            price = _parse_decimal(mc(cells, "price"))
            nom = get_nomenclature(name, service, is_serial, uom, price)

            qin = _parse_decimal(mc(cells, "qty_in")) or Decimal(0)
            qout = _parse_decimal(mc(cells, "qty_out")) or Decimal(0)
            from_wh = resolve_wh(mc(cells, "from_unit"), service)
            to_wh = resolve_wh(mc(cells, "to_unit"), service)

            if from_wh and to_wh:
                mtype = "transfer"
            elif to_wh:
                mtype = "receipt"
            elif from_wh:
                mtype = "writeoff"
            else:
                counts["skipped"] += 1
                errors.append(f"рядок {i} «{name}»: немає складів (from/to)")
                continue

            instance = None
            if is_serial:
                instance = db.query(Instance).filter(Instance.serial_no == serial).first()
                if not instance:
                    instance = Instance(nomenclature_id=nom.id, serial_no=serial, is_official=True)
                    db.add(instance); db.flush()
                    counts["instances_created"] += 1
                qty = Decimal(1)
            else:
                qty = qin if qin > 0 else qout
                if qty <= 0:
                    counts["skipped"] += 1
                    errors.append(f"рядок {i} «{name}»: нульова кількість")
                    continue

            iso = _parse_date(mc(cells, "entry_date")) or _parse_date(mc(cells, "doc_date"))
            try:
                mdate = date_cls.fromisoformat(iso) if iso else date_cls.today()
            except ValueError:
                mdate = date_cls.today()

            db.add(CustodyMovement(
                date=mdate, type=mtype, nomenclature_id=nom.id,
                from_warehouse_id=from_wh.id if from_wh else None,
                to_warehouse_id=to_wh.id if to_wh else None,
                instance_id=instance.id if instance else None,
                quantity=qty, is_official=True, created_by=user.id,
            ))
            counts["movements"] += 1
            if instance:
                instance.current_warehouse_id = to_wh.id if to_wh else None
        except Exception as e:
            counts["skipped"] += 1
            errors.append(f"рядок {i} «{name}»: {e}")

    db.commit()
    return {**counts, "errors": errors[:100]}

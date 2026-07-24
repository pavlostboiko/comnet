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

    # Caches / find-or-create — ВСІ сідяться з БД, щоб повторний імпорт не плодив дублі
    services = {s.name.strip().lower(): s for s in db.query(Service).all()}
    units = {u.name.strip().lower(): u for u in db.query(Unit).all()}
    noms = {(n.name.strip().lower(), n.service_id): n for n in db.query(Nomenclature).all()}
    persons_cache = {
        (p.last_name.strip().lower(), p.unit_id): p
        for p in db.query(Person).all() if p.last_name and p.unit_id
    }

    counts = {"rows": 0, "nomenclature": 0, "movements": 0, "assignments": 0,
              "services_created": 0, "units_created": 0, "persons_created": 0}
    errors = []

    def get_service(name):
        key = name.strip().lower()
        s = services.get(key)
        if not s:
            s = Service(name=name.strip())
            db.add(s); db.flush()
            services[key] = s
            counts["services_created"] += 1
        # Ensure a warehouse even for pre-existing (v1) services — idempotent.
        ensure_warehouse_for_service(db, s)
        return s

    def get_unit(name):
        key = name.strip().lower()
        u = units.get(key)
        if not u:
            u = Unit(name=name.strip())
            db.add(u); db.flush()
            units[key] = u
            counts["units_created"] += 1
        ensure_warehouse_for_unit(db, u)  # idempotent
        return u

    def wh_of_unit(u):
        return db.query(Warehouse).filter(Warehouse.unit_id == u.id).first()

    def wh_of_service(s):
        return db.query(Warehouse).filter(Warehouse.service_id == s.id).first()

    def get_nomenclature(name, service, is_serial, uom, price, code):
        key = (name.strip().lower(), service.id)
        n = noms.get(key)
        if not n:
            n = Nomenclature(name=name.strip(), service_id=service.id,
                             is_serialized=is_serial, unit_of_measure=uom, price=price, code=code)
            db.add(n); db.flush()
            noms[key] = n
            counts["nomenclature"] += 1
        return n

    def parse_location(raw):
        """Return (unit_or_None, person_name_or_None) from «<підрозділ> [людина]».
        Порожнє або токен складу («СКЛАД») → (None, None) → склад служби."""
        s = (raw or "").strip()
        if not s or is_service_warehouse_location(s):
            return None, None
        low = s.lower()
        # longest existing-unit prefix
        best = None
        for uname_key, u in units.items():
            if low == uname_key or low.startswith(uname_key + " "):
                if best is None or len(uname_key) > len(best[0]):
                    best = (uname_key, u)
        if best:
            person = s[len(best[0]):].strip()
            return best[1], (person or None)
        # no known unit prefix → treat entire string as a unit, no person
        return get_unit(s), None

    def get_person(name, unit):
        key = (name.strip().lower(), unit.id)
        p = persons_cache.get(key)
        if not p:
            p = db.query(Person).filter(Person.last_name == name.strip(),
                                        Person.unit_id == unit.id).first()
        if not p:
            p = Person(last_name=name.strip(), unit_id=unit.id, is_active=True)
            db.add(p); db.flush()
            counts["persons_created"] += 1
        persons_cache[key] = p
        return p

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
            uom = _clean(col(row, "uom"))
            price = _parse_decimal(col(row, "price"))
            code = _clean(col(row, "code"))
            qty = _parse_decimal(col(row, "qty")) or Decimal("1")
            nom = get_nomenclature(name, service, is_serial, uom, price, code)

            unit, person_name = parse_location(col(row, "location"))
            if unit:
                target_wh = wh_of_unit(unit)
            else:
                target_wh = wh_of_service(service)
            if not target_wh:
                errors.append(f"«{name}»: не знайдено склад — пропущено")
                continue

            iso = _parse_date(col(row, "issued_at"))
            issued_at = None
            if iso:
                try:
                    issued_at = date_cls.fromisoformat(iso)
                except ValueError:
                    issued_at = None

            # instance for serial
            instance = None
            if is_serial:
                instance = db.query(Instance).filter(Instance.serial_no == serial).first()
                if not instance:
                    instance = Instance(nomenclature_id=nom.id, serial_no=serial, is_official=True)
                    db.add(instance); db.flush()

            # receipt movement into target warehouse
            mv = CustodyMovement(
                date=date_cls.today(), type="receipt", nomenclature_id=nom.id,
                to_warehouse_id=target_wh.id, instance_id=instance.id if instance else None,
                quantity=Decimal(1) if is_serial else qty, is_official=True, created_by=user.id,
            )
            db.add(mv)
            counts["movements"] += 1
            if instance:
                instance.current_warehouse_id = target_wh.id

            # assignment to person (only for unit warehouses)
            if person_name and unit:
                person = get_person(person_name, unit)
                db.add(Assignment(
                    warehouse_id=target_wh.id, person_id=person.id, nomenclature_id=nom.id,
                    instance_id=instance.id if instance else None,
                    quantity=Decimal(1) if is_serial else qty, is_official=True,
                    issued_date=issued_at or date_cls.today(), created_by=user.id,
                ))
                counts["assignments"] += 1
        except Exception as e:
            errors.append(f"«{name}»: {e}")

    db.commit()
    return {**counts, "errors": errors}

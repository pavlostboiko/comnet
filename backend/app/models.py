from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric,
    String, Text, UniqueConstraint, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=True)              # v2: коротка абревіатура
    chief_name = Column(String, nullable=True)        # для тексту накладних
    chief_position = Column(String, nullable=True)


class Unit(Base):
    """v2: підрозділ як окрема сутність (замість free-text persons.unit).
    Плоска структура — без ієрархії."""
    __tablename__ = "units"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    code = Column(String, nullable=True)
    name_locative = Column(String, nullable=True)     # «у 1-й роті» — для документів
    is_external = Column(Boolean, nullable=False, default=False)  # зовнішній підрозділ (джерело приймання)


class Group(Base):
    """v2: група всередині підрозділу; командир — person."""
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    unit_id = Column(Integer, ForeignKey("units.id", ondelete="CASCADE"), nullable=False)
    commander_id = Column(Integer, ForeignKey("persons.id", ondelete="SET NULL"), nullable=True)

    unit = relationship("Unit")
    commander = relationship("Person", foreign_keys=[commander_id])


class Warehouse(Base):
    """v2: облікова точка (склад служби АБО склад підрозділу).
    Стабільна — прив'язана до служби/підрозділу, НЕ до особи.
    Інваріант: type=service → service_id заповнено, unit_id порожньо (і навпаки)."""
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)             # 'service' | 'unit'
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=True)
    unit_id = Column(Integer, ForeignKey("units.id", ondelete="CASCADE"), nullable=True)

    service = relationship("Service")
    unit = relationship("Unit")


class StoragePoint(Base):
    """v2: фізична точка зберігання всередині складу («Бокс 3», «Гараж»).

    Довідкова вісь, НЕ облікова: баланси й документи далі рахуються по складу.
    Назва унікальна в межах складу."""
    __tablename__ = "storage_points"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)

    warehouse = relationship("Warehouse")


class NomenclaturePoint(Base):
    """v2: точка зберігання несерійного — одна на (картка, склад).

    Без розподілу кількості: «все, що з цієї картки лежить на цьому складі,
    лежить тут». Розподіл к-сті по точках вимагав би окремого леджера."""
    __tablename__ = "nomenclature_points"

    id = Column(Integer, primary_key=True)
    nomenclature_id = Column(Integer, ForeignKey("nomenclature.id", ondelete="CASCADE"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    storage_point_id = Column(Integer, ForeignKey("storage_points.id", ondelete="CASCADE"), nullable=False)

    storage_point = relationship("StoragePoint")


class Mvo(Base):
    """v2: журнал підписантів документів (історичний) — не лише МВО.
    Діючий = to_date IS NULL; максимум один діючий на склад/службу/систему."""
    __tablename__ = "mvo"

    id = Column(Integer, primary_key=True)
    # kind='warehouse' → МВО складу (warehouse_id заповнено);
    # kind='fin' → глобальна фінслужба (warehouse_id NULL, одна діюча на систему);
    # kind='service_chief' → начальник служби (service_id заповнено, один на службу)
    kind = Column(String, nullable=False, default="warehouse")
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=True)
    person_id = Column(Integer, ForeignKey("persons.id", ondelete="CASCADE"), nullable=False)
    # Посада/звання підписанта на період цього призначення (для snap документів).
    position = Column(String, nullable=True)
    rank = Column(String, nullable=True)
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, nullable=True)

    warehouse = relationship("Warehouse")
    person = relationship("Person", foreign_keys=[person_id])


class Nomenclature(Base):
    """v2: тип майна («АК-74 взагалі»), не фізичний предмет.
    `service` — вісь розмежування доступу. `is_serialized` — гілка обліку."""
    __tablename__ = "nomenclature"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="RESTRICT"), nullable=False)
    category = Column(String, nullable=True)          # група майна всередині служби
    is_official = Column(Boolean, nullable=False, default=True)  # облік / ндм
    is_serialized = Column(Boolean, nullable=False, default=False)
    unit_of_measure = Column(String, nullable=True)   # шт, компл, пара, кг, м, л
    code = Column(String, nullable=True)              # номенклатурний номер / артикул
    price = Column(Numeric(15, 2), nullable=True)     # вартісний облік

    service = relationship("Service")


class Instance(Base):
    """v2: екземпляр серійного майна (1 запис = 1 предмет).
    current_warehouse — денормалізоване: to_warehouse останнього руху (заповниться
    у Фазі 3, коли з'являться v2-рухи)."""
    __tablename__ = "instances"

    id = Column(Integer, primary_key=True)
    nomenclature_id = Column(Integer, ForeignKey("nomenclature.id", ondelete="CASCADE"), nullable=False)
    serial_no = Column(String, nullable=False, unique=True)
    card_number = Column(String, nullable=True)       # Items «№» — join з Переміщеннями
    current_warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    is_official = Column(Boolean, nullable=False, default=True)  # державне / волонтерське
    note = Column(String, nullable=True)              # примітка на екземплярі
    # Фізична точка всередині складу (довідкова, не облікова): скидається, коли
    # екземпляр переїжджає на інший склад — точка належить старому складу.
    storage_point_id = Column(Integer, ForeignKey("storage_points.id", ondelete="SET NULL"), nullable=True)

    nomenclature = relationship("Nomenclature")
    current_warehouse = relationship("Warehouse")
    storage_point = relationship("StoragePoint")


class CustodyMovement(Base):
    """v2: рух custody між обліковими точками (склад → склад). Ядро леджера.

    Серійне: instance заповнено, quantity=1. Несерійне: instance порожньо, quantity>0.
    is_official — державне/волонтерське; для несерійного визначає лінію балансу."""
    __tablename__ = "custody_movements"

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    type = Column(String, nullable=False)             # receipt | transfer | writeoff
    from_warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    to_warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    nomenclature_id = Column(Integer, ForeignKey("nomenclature.id", ondelete="RESTRICT"), nullable=False)
    instance_id = Column(Integer, ForeignKey("instances.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Numeric(15, 4), nullable=False)
    is_official = Column(Boolean, nullable=False, default=True)
    card_number = Column(String, nullable=True)        # Переміщення «Поле 12»
    doc_number = Column(String, nullable=True)         # номер накладної
    document_id = Column(Integer, ForeignKey("custody_documents.id", ondelete="SET NULL"), nullable=True)  # шапка накладної/акта
    signed_by_person_id = Column(Integer, ForeignKey("persons.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    nomenclature = relationship("Nomenclature")
    instance = relationship("Instance")
    from_warehouse = relationship("Warehouse", foreign_keys=[from_warehouse_id])
    to_warehouse = relationship("Warehouse", foreign_keys=[to_warehouse_id])
    document = relationship("CustodyDocument", back_populates="movements", foreign_keys=[document_id])


class CustodyDocument(Base):
    """v2: шапка документа (накладна/акт) над леджером custody_movements.

    Реквізити тримаються тут ОДИН раз; рядки лінкуються через
    custody_movements.document_id. status: draft (редагується) → signed (snap
    заморожено, номер зафіксовано, доступний XLSX Дод.25). Sign/unsign НЕ рухають
    леджер — рухи проводяться при створенні (інваріант v2)."""
    __tablename__ = "custody_documents"

    id = Column(Integer, primary_key=True)
    operation = Column(String, nullable=False)         # receipt | transfer
    form = Column(String, nullable=False)              # накладна | акт
    doc_number = Column(String, nullable=True)
    doc_date = Column(String, nullable=True)
    date_operation = Column(String, nullable=True)
    from_warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    to_warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    from_unit = Column(String, nullable=True)          # snap-назва складу-джерела
    to_unit = Column(String, nullable=True)            # snap-назва складу-отримувача
    counterparty = Column(String, nullable=True)       # від кого (приймання ззовні)
    basis = Column(String, nullable=True)
    service = Column(String, nullable=True)            # денормалізована назва служби
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True)
    op_type_id = Column(Integer, ForeignKey("op_types.id", ondelete="SET NULL"), nullable=True)
    # Підписанти (Здав/Прийняв/Фін) НЕ зберігаються — резолвляться з журналу МВО
    # за датою документа (див. custody_snapshot.mvo_at).
    status = Column(String, nullable=False, default="draft")
    signed_at = Column(DateTime, nullable=True)
    signed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    from_warehouse = relationship("Warehouse", foreign_keys=[from_warehouse_id])
    to_warehouse = relationship("Warehouse", foreign_keys=[to_warehouse_id])
    movements = relationship(
        "CustodyMovement", back_populates="document",
        foreign_keys="CustodyMovement.document_id",
    )


class Assignment(Base):
    """v2: видача особовому складу (фізичне тримання). НЕ рухає custody.

    warehouse — склад підрозділу; person.unit має = warehouse.unit.
    Активна = returned_date IS NULL. Серійне: instance заповнено, один активний
    на екземпляр. is_official — для несерійного визначає лінію балансу-джерела."""
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    person_id = Column(Integer, ForeignKey("persons.id", ondelete="CASCADE"), nullable=False)
    nomenclature_id = Column(Integer, ForeignKey("nomenclature.id", ondelete="RESTRICT"), nullable=False)
    instance_id = Column(Integer, ForeignKey("instances.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Numeric(15, 4), nullable=False)
    is_official = Column(Boolean, nullable=False, default=True)
    # Де воно фізично лежить, поки на руках (для серійного точка живе на екземплярі).
    storage_point_id = Column(Integer, ForeignKey("storage_points.id", ondelete="SET NULL"), nullable=True)
    issued_date = Column(Date, nullable=False)
    returned_date = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    returned_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    warehouse = relationship("Warehouse")
    person = relationship("Person", foreign_keys=[person_id])
    nomenclature = relationship("Nomenclature")
    instance = relationship("Instance")
    storage_point = relationship("StoragePoint")


class UnitSettings(Base):
    __tablename__ = "unit_settings"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    short_name = Column(String, nullable=True)
    edrpou = Column(String, nullable=True)
    location = Column(String, nullable=True)


class OpType(Base):
    __tablename__ = "op_types"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    number_prefix = Column(String, nullable=True)

    details = relationship("OpTypeDetail", back_populates="op_type", cascade="all, delete-orphan")


class OpTypeDetail(Base):
    __tablename__ = "op_type_details"

    id = Column(Integer, primary_key=True)
    op_type_id = Column(Integer, ForeignKey("op_types.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False, unique=True)

    op_type = relationship("OpType", back_populates="details")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="operator")  # admin|operator|service|mvo
    is_active = Column(Boolean, nullable=False, default=True)
    person_id = Column(Integer, ForeignKey("persons.id", ondelete="SET NULL"), nullable=True)
    # v2 two-axis scope
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True)
    unit_id = Column(Integer, ForeignKey("units.id", ondelete="SET NULL"), nullable=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)

    person = relationship("Person", foreign_keys=[person_id])

    @property
    def person_unit(self):
        return self.person.unit if self.person else None


class Person(Base):
    __tablename__ = "persons"

    id = Column(Integer, primary_key=True)
    # Посада/звання перенесено на записи журналу mvo (міграція 027).
    last_name = Column(String, nullable=True)
    last_name_genitive = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    first_name_genitive = Column(String, nullable=True)
    patronymic = Column(String, nullable=True)
    patronymic_genitive = Column(String, nullable=True)
    search_name = Column(String, nullable=True)
    unit = Column(String, nullable=True)              # v1 free-text; прибереться в пізній фазі
    unit_locative = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    # v2 additions
    unit_id = Column(Integer, ForeignKey("units.id", ondelete="SET NULL"), nullable=True)
    callsign = Column(String, nullable=True)          # влиті recipients (позивні)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True)
    ipn = Column(String, nullable=True)               # ІПН — заповнюється вручну

    unit_ref = relationship("Unit", foreign_keys=[unit_id])
    group = relationship("Group", foreign_keys=[group_id])


class AuditLog(Base):
    """Журнал змін БД: хто/коли/дія/сутність + diff полів. Пишеться автоматично
    хуком after_flush (див. app/audit.py). username — знімок (переживає видалення)."""
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    ts = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    username = Column(String, nullable=True)
    action = Column(String, nullable=False)          # create | update | delete
    entity_type = Column(String, nullable=False, index=True)
    entity_id = Column(Integer, nullable=True)
    changes = Column(JSON, nullable=True)            # {поле: [було, стало]}

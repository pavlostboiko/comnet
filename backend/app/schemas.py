from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel


# --- Services ---

class ServiceRead(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
    chief_name: Optional[str] = None
    chief_position: Optional[str] = None

    model_config = {"from_attributes": True}


class ServiceCreate(BaseModel):
    name: str
    code: Optional[str] = None
    chief_name: Optional[str] = None
    chief_position: Optional[str] = None


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    chief_name: Optional[str] = None
    chief_position: Optional[str] = None


# --- v2 structure: units, groups, warehouses, mvo ---

class UnitRead(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
    name_locative: Optional[str] = None
    is_external: bool = False
    model_config = {"from_attributes": True}


class UnitCreate(BaseModel):
    name: str
    code: Optional[str] = None
    name_locative: Optional[str] = None
    is_external: bool = False


class UnitUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    name_locative: Optional[str] = None
    is_external: Optional[bool] = None


class GroupRead(BaseModel):
    id: int
    name: str
    unit_id: int
    commander_id: Optional[int] = None
    model_config = {"from_attributes": True}


class GroupCreate(BaseModel):
    name: str
    unit_id: int
    commander_id: Optional[int] = None


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    unit_id: Optional[int] = None
    commander_id: Optional[int] = None


class WarehouseRead(BaseModel):
    id: int
    name: str
    type: str
    service_id: Optional[int] = None
    unit_id: Optional[int] = None
    model_config = {"from_attributes": True}


class WarehouseUpdate(BaseModel):
    name: str


class MvoRead(BaseModel):
    id: int
    kind: str = "warehouse"
    warehouse_id: Optional[int] = None
    person_id: int
    position: Optional[str] = None
    rank: Optional[str] = None
    from_date: str
    to_date: Optional[str] = None
    model_config = {"from_attributes": True}


class MvoCreate(BaseModel):
    kind: str = "warehouse"                 # warehouse | fin
    warehouse_id: Optional[int] = None      # обов'язковий для kind=warehouse
    person_id: int
    position: Optional[str] = None
    rank: Optional[str] = None
    from_date: str
    to_date: Optional[str] = None


class MvoUpdate(BaseModel):
    person_id: Optional[int] = None
    position: Optional[str] = None
    rank: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None


# --- v2 nomenclature + instances ---

class NomenclatureRead(BaseModel):
    id: int
    name: str
    service_id: int
    category: Optional[str] = None
    is_official: bool = True
    is_serialized: bool
    unit_of_measure: Optional[str] = None
    code: Optional[str] = None
    price: Optional[Decimal] = None
    model_config = {"from_attributes": True}


class NomenclatureCreate(BaseModel):
    name: str
    service_id: int
    category: Optional[str] = None
    is_official: bool = True
    is_serialized: bool = False
    unit_of_measure: Optional[str] = None
    code: Optional[str] = None
    price: Optional[Decimal] = None


class NomenclatureUpdate(BaseModel):
    name: Optional[str] = None
    service_id: Optional[int] = None
    category: Optional[str] = None
    is_official: Optional[bool] = None
    is_serialized: Optional[bool] = None
    unit_of_measure: Optional[str] = None
    code: Optional[str] = None
    price: Optional[Decimal] = None


class InstanceRead(BaseModel):
    id: int
    nomenclature_id: int
    serial_no: str
    card_number: Optional[str] = None
    current_warehouse_id: Optional[int] = None
    is_official: bool
    note: Optional[str] = None
    model_config = {"from_attributes": True}


class InstanceCreate(BaseModel):
    serial_no: str
    is_official: bool = True
    current_warehouse_id: Optional[int] = None
    note: Optional[str] = None


class InstanceUpdate(BaseModel):
    note: Optional[str] = None


# --- v2 custody movements ---

class CustodyMovementCreate(BaseModel):
    date: str                                   # ISO
    type: str                                   # receipt | transfer | writeoff
    nomenclature_id: int
    from_warehouse_id: Optional[int] = None
    to_warehouse_id: Optional[int] = None
    instance_id: Optional[int] = None
    quantity: Optional[Decimal] = None          # серійне → 1 автоматично
    is_official: bool = True
    signed_by_person_id: Optional[int] = None


# --- batch transfer (накладна на переміщення) ---

class DocumentItemIn(BaseModel):
    nomenclature_id: int
    instance_id: Optional[int] = None
    quantity: Optional[Decimal] = None          # серійне → 1
    assign_person_id: Optional[int] = None      # опц.: одразу видати особі (склад-отримувач = підрозділ)


class DocumentBatchCreate(BaseModel):
    date: str
    from_warehouse_id: int
    to_warehouse_id: int
    doc_number: Optional[str] = None
    items: List[DocumentItemIn]


# --- v2 custody documents (накладна/акт-шапка над рухами) ---

class CustodyDocIn(BaseModel):
    operation: str = "transfer"                  # receipt | transfer
    form: str = "накладна"                        # накладна | акт
    doc_number: Optional[str] = None
    doc_date: Optional[str] = None
    date_operation: Optional[str] = None
    from_warehouse_id: Optional[int] = None
    to_warehouse_id: Optional[int] = None
    counterparty: Optional[str] = None
    basis: Optional[str] = None
    service_id: Optional[int] = None
    op_type_id: Optional[int] = None
    movement_ids: List[int] = []                  # рухи, що входять у документ


# --- v2 receipt document (приймання ззовні одразу документом) ---

class NewNomIn(BaseModel):
    name: str
    service_id: int
    category: Optional[str] = None
    is_official: bool = True
    is_serialized: bool = False
    unit_of_measure: Optional[str] = None
    code: Optional[str] = None
    price: Optional[Decimal] = None


class ReceiptItemIn(BaseModel):
    nomenclature_id: Optional[int] = None          # існуюча картка
    new_nomenclature: Optional[NewNomIn] = None    # або створити на льоту
    quantity: Optional[Decimal] = None             # несерійне
    serial_no: Optional[str] = None                # серійне
    card_number: Optional[str] = None


class ReceiptCreate(BaseModel):
    to_warehouse_id: int
    form: str = "накладна"                          # накладна | акт
    counterparty: Optional[str] = None             # від кого
    doc_number: Optional[str] = None
    doc_date: Optional[str] = None
    basis: Optional[str] = None
    service_id: Optional[int] = None
    op_type_id: Optional[int] = None
    items: List[ReceiptItemIn] = []


# --- v2 assignments ---

class AssignmentCreate(BaseModel):
    warehouse_id: int
    person_id: int
    nomenclature_id: int
    instance_id: Optional[int] = None
    quantity: Optional[Decimal] = None          # серійне → 1 автоматично
    is_official: bool = True
    issued_date: Optional[str] = None           # ISO; default сьогодні


class AssignmentReturn(BaseModel):
    returned_date: Optional[str] = None


# --- Auth ---

class Token(BaseModel):
    access_token: str
    token_type: str


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    person_id: Optional[int] = None
    person_unit: Optional[str] = None  # persons.unit via property
    # v2 scope
    service_id: Optional[int] = None
    unit_id: Optional[int] = None
    warehouse_id: Optional[int] = None

    model_config = {"from_attributes": True}


# --- User admin (CRUD by admin) ---

class UserAdminCreate(BaseModel):
    username: str
    password: str
    role: str = "admin"          # 'admin' | 'operator' | 'service' | 'mvo'
    is_active: bool = True
    person_id: Optional[int] = None
    # v2 scope
    service_id: Optional[int] = None
    unit_id: Optional[int] = None
    warehouse_id: Optional[int] = None


class UserAdminUpdate(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    person_id: Optional[int] = None
    # v2 scope
    service_id: Optional[int] = None
    unit_id: Optional[int] = None
    warehouse_id: Optional[int] = None


class PasswordSet(BaseModel):
    password: str


# --- Unit Settings ---

class UnitSettingsRead(BaseModel):
    id: int
    name: Optional[str] = None
    short_name: Optional[str] = None
    edrpou: Optional[str] = None
    location: Optional[str] = None

    model_config = {"from_attributes": True}


class UnitSettingsUpdate(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    edrpou: Optional[str] = None
    location: Optional[str] = None


# --- Op Types ---

class OpTypeDetailRead(BaseModel):
    id: int
    op_type_id: int
    name: str

    model_config = {"from_attributes": True}


class OpTypeDetailCreate(BaseModel):
    op_type_id: int
    name: str


class OpTypeDetailUpdate(BaseModel):
    name: Optional[str] = None
    op_type_id: Optional[int] = None


class OpTypeRead(BaseModel):
    id: int
    name: str
    number_prefix: Optional[str] = None
    details: List[OpTypeDetailRead] = []

    model_config = {"from_attributes": True}


class OpTypeCreate(BaseModel):
    name: str
    number_prefix: Optional[str] = None


class OpTypeUpdate(BaseModel):
    name: Optional[str] = None
    number_prefix: Optional[str] = None


# --- Persons ---

class PersonRead(BaseModel):
    id: int
    last_name: Optional[str] = None
    last_name_genitive: Optional[str] = None
    first_name: Optional[str] = None
    first_name_genitive: Optional[str] = None
    patronymic: Optional[str] = None
    patronymic_genitive: Optional[str] = None
    search_name: Optional[str] = None
    unit: Optional[str] = None
    unit_locative: Optional[str] = None
    is_active: bool
    # v2
    unit_id: Optional[int] = None
    callsign: Optional[str] = None
    group_id: Optional[int] = None
    ipn: Optional[str] = None

    model_config = {"from_attributes": True}


class PersonCreate(BaseModel):
    last_name: Optional[str] = None
    last_name_genitive: Optional[str] = None
    first_name: Optional[str] = None
    first_name_genitive: Optional[str] = None
    patronymic: Optional[str] = None
    patronymic_genitive: Optional[str] = None
    search_name: Optional[str] = None
    unit: Optional[str] = None
    unit_locative: Optional[str] = None
    is_active: bool = True
    # v2
    unit_id: Optional[int] = None
    callsign: Optional[str] = None
    group_id: Optional[int] = None
    ipn: Optional[str] = None


class PersonUpdate(BaseModel):
    last_name: Optional[str] = None
    last_name_genitive: Optional[str] = None
    first_name: Optional[str] = None
    first_name_genitive: Optional[str] = None
    patronymic: Optional[str] = None
    patronymic_genitive: Optional[str] = None
    search_name: Optional[str] = None
    unit: Optional[str] = None
    unit_locative: Optional[str] = None
    is_active: Optional[bool] = None
    # v2
    unit_id: Optional[int] = None
    callsign: Optional[str] = None
    group_id: Optional[int] = None
    ipn: Optional[str] = None


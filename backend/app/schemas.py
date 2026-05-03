from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel


# --- Auth ---

class Token(BaseModel):
    access_token: str
    token_type: str


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


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
    details: List[OpTypeDetailRead] = []

    model_config = {"from_attributes": True}


class OpTypeCreate(BaseModel):
    name: str


class OpTypeUpdate(BaseModel):
    name: Optional[str] = None


# --- Persons ---

class PersonRead(BaseModel):
    id: int
    position: Optional[str] = None
    position_genitive: Optional[str] = None
    rank: Optional[str] = None
    rank_genitive: Optional[str] = None
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

    model_config = {"from_attributes": True}


class PersonCreate(BaseModel):
    position: Optional[str] = None
    position_genitive: Optional[str] = None
    rank: Optional[str] = None
    rank_genitive: Optional[str] = None
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


class PersonUpdate(BaseModel):
    position: Optional[str] = None
    position_genitive: Optional[str] = None
    rank: Optional[str] = None
    rank_genitive: Optional[str] = None
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


# --- Asset Documents ---

class AssetDocumentRead(BaseModel):
    id: int
    doc_type: Optional[str] = None
    doc_number: Optional[str] = None
    doc_date: Optional[str] = None

    model_config = {"from_attributes": True}


class AssetDocumentCreate(BaseModel):
    doc_type: Optional[str] = None
    doc_number: Optional[str] = None
    doc_date: Optional[str] = None


# --- Items ---

class ItemListRead(BaseModel):
    id: int
    number: str
    name: Optional[str] = None
    category: Optional[str] = None
    serial_number: Optional[str] = None
    unit_of_measure: Optional[str] = None
    price: Optional[Decimal] = None
    quantity: Optional[Decimal] = None
    item_type: Optional[str] = None
    is_official: bool

    model_config = {"from_attributes": True}


class ItemRead(BaseModel):
    id: int
    number: str
    name: Optional[str] = None
    category: Optional[str] = None
    nomenclature_code: Optional[str] = None
    serial_number: Optional[str] = None
    unit_of_measure: Optional[str] = None
    price: Optional[Decimal] = None
    quantity: Optional[Decimal] = None
    item_type: Optional[str] = None
    batch_id: Optional[str] = None
    notes: Optional[str] = None
    is_official: bool
    documents: List[AssetDocumentRead] = []

    model_config = {"from_attributes": True}


class ItemCreate(BaseModel):
    number: str
    name: str
    category: Optional[str] = None
    nomenclature_code: Optional[str] = None
    serial_number: Optional[str] = None
    unit_of_measure: Optional[str] = None
    price: Optional[Decimal] = None
    quantity: Optional[Decimal] = None
    item_type: Optional[str] = None
    batch_id: Optional[str] = None
    notes: Optional[str] = None
    is_official: bool = True
    documents: List[AssetDocumentCreate] = []


class ItemUpdate(BaseModel):
    number: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    nomenclature_code: Optional[str] = None
    serial_number: Optional[str] = None
    unit_of_measure: Optional[str] = None
    price: Optional[Decimal] = None
    quantity: Optional[Decimal] = None
    item_type: Optional[str] = None
    batch_id: Optional[str] = None
    notes: Optional[str] = None
    is_official: Optional[bool] = None
    documents: Optional[List[AssetDocumentCreate]] = None


# --- Movements ---

class MovementListRead(BaseModel):
    id: int
    entry_date: Optional[str] = None
    doc_type: Optional[str] = None
    doc_number: Optional[str] = None
    doc_date: Optional[str] = None
    from_unit: Optional[str] = None
    to_unit: Optional[str] = None
    mvo_from_name: Optional[str] = None
    mvo_to_name: Optional[str] = None
    category: Optional[str] = None
    item_name: Optional[str] = None
    item_card_num: Optional[str] = None
    unit_of_measure: Optional[str] = None
    qty_in: Optional[Decimal] = None
    qty_out: Optional[Decimal] = None
    price: Optional[Decimal] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_movement(cls, m):
        return cls(
            id=m.id,
            entry_date=m.entry_date,
            doc_type=m.doc_type,
            doc_number=m.doc_number,
            doc_date=m.doc_date,
            from_unit=m.from_unit,
            to_unit=m.to_unit,
            mvo_from_name=m.mvo_from.search_name if m.mvo_from else None,
            mvo_to_name=m.mvo_to.search_name if m.mvo_to else None,
            category=m.category,
            item_name=m.item_name,
            item_card_num=m.item_card_num,
            unit_of_measure=m.unit_of_measure,
            qty_in=m.qty_in,
            qty_out=m.qty_out,
            price=m.price,
        )


class MovementRead(BaseModel):
    id: int
    entry_date: Optional[str] = None
    item_name: Optional[str] = None
    item_card_num: Optional[str] = None
    unit_of_measure: Optional[str] = None
    category: Optional[str] = None
    qty_in: Optional[Decimal] = None
    qty_out: Optional[Decimal] = None
    from_unit: Optional[str] = None
    to_unit: Optional[str] = None
    mvo_from_id: Optional[int] = None
    mvo_to_id: Optional[int] = None
    basis: Optional[str] = None
    doc_date: Optional[str] = None
    doc_number: Optional[str] = None
    doc_type: Optional[str] = None
    serial_number: Optional[str] = None
    notes: Optional[str] = None
    executor_id: Optional[int] = None
    nomenclature_code: Optional[str] = None
    price: Optional[Decimal] = None
    service: Optional[str] = None
    op_type_id: Optional[int] = None
    op_type_detail_id: Optional[int] = None
    recipient_category: Optional[str] = None

    model_config = {"from_attributes": True}


class MovementCreate(BaseModel):
    entry_date: Optional[str] = None
    item_name: Optional[str] = None
    item_card_num: Optional[str] = None
    unit_of_measure: Optional[str] = None
    category: Optional[str] = None
    qty_in: Optional[Decimal] = None
    qty_out: Optional[Decimal] = None
    from_unit: Optional[str] = None
    to_unit: Optional[str] = None
    mvo_from_id: Optional[int] = None
    mvo_to_id: Optional[int] = None
    basis: Optional[str] = None
    doc_date: Optional[str] = None
    doc_number: Optional[str] = None
    doc_type: Optional[str] = None
    serial_number: Optional[str] = None
    notes: Optional[str] = None
    executor_id: Optional[int] = None
    nomenclature_code: Optional[str] = None
    price: Optional[Decimal] = None
    service: Optional[str] = None
    op_type_id: Optional[int] = None
    op_type_detail_id: Optional[int] = None
    recipient_category: Optional[str] = None


class MovementUpdate(MovementCreate):
    pass


# --- Invoices (Накладна вимога Додаток 25) ---

class InvoiceItemCreate(BaseModel):
    sort_order: Optional[int] = None
    item_name: Optional[str] = None
    nomenclature_code: Optional[str] = None
    unit_of_measure: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[Decimal] = None
    qty_received: Optional[Decimal] = None
    price: Optional[Decimal] = None
    amount: Optional[Decimal] = None
    notes: Optional[str] = None


class InvoiceItemRead(InvoiceItemCreate):
    id: int

    model_config = {"from_attributes": True}


class InvoiceCreate(BaseModel):
    doc_number: Optional[str] = None
    doc_date: Optional[str] = None
    from_unit: Optional[str] = None
    to_unit: Optional[str] = None
    status: str = "draft"
    # накладна-specific header stored in extra_data
    validity_date: Optional[str] = None
    composed_date: Optional[str] = None
    composed_location: Optional[str] = None
    operation_date: Optional[str] = None
    service: Optional[str] = None
    op_type_text: Optional[str] = None
    basis: Optional[str] = None
    responsible_recipient: Optional[str] = None
    sender_id: Optional[int] = None
    receiver_id: Optional[int] = None
    commander_id: Optional[int] = None
    mvo_from_id: Optional[int] = None
    mvo_to_id: Optional[int] = None
    total_qty_words: Optional[str] = None
    total_amount_words: Optional[str] = None
    items: List[InvoiceItemCreate] = []


class InvoiceRead(BaseModel):
    id: int
    doc_number: Optional[str] = None
    doc_date: Optional[str] = None
    from_unit: Optional[str] = None
    to_unit: Optional[str] = None
    status: str
    validity_date: Optional[str] = None
    composed_date: Optional[str] = None
    composed_location: Optional[str] = None
    operation_date: Optional[str] = None
    service: Optional[str] = None
    op_type_text: Optional[str] = None
    basis: Optional[str] = None
    responsible_recipient: Optional[str] = None
    sender_id: Optional[int] = None
    receiver_id: Optional[int] = None
    commander_id: Optional[int] = None
    mvo_from_id: Optional[int] = None
    mvo_to_id: Optional[int] = None
    total_qty_words: Optional[str] = None
    total_amount_words: Optional[str] = None
    items: List[InvoiceItemRead] = []

    model_config = {"from_attributes": True}


class InvoiceListRead(BaseModel):
    id: int
    doc_number: Optional[str] = None
    doc_date: Optional[str] = None
    from_unit: Optional[str] = None
    to_unit: Optional[str] = None
    status: str

    model_config = {"from_attributes": True}


class InvoiceUpdate(InvoiceCreate):
    pass

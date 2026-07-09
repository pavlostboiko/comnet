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
    chief_name = Column(String, nullable=True)
    chief_position = Column(String, nullable=True)


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
    role = Column(String, nullable=False, default="operator")
    is_active = Column(Boolean, nullable=False, default=True)
    person_id = Column(Integer, ForeignKey("persons.id", ondelete="SET NULL"), nullable=True)

    person = relationship("Person", foreign_keys=[person_id])

    @property
    def person_unit(self):
        return self.person.unit if self.person else None


class Person(Base):
    __tablename__ = "persons"

    id = Column(Integer, primary_key=True)
    position = Column(String, nullable=True)
    position_genitive = Column(String, nullable=True)
    rank = Column(String, nullable=True)
    rank_genitive = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    last_name_genitive = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    first_name_genitive = Column(String, nullable=True)
    patronymic = Column(String, nullable=True)
    patronymic_genitive = Column(String, nullable=True)
    search_name = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    unit_locative = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)


class Recipient(Base):
    __tablename__ = "recipients"

    id = Column(Integer, primary_key=True)
    callsign = Column(String, nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    number = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=True)
    category = Column(String, nullable=True)
    nomenclature_code = Column(String, nullable=True)
    serial_number = Column(String, nullable=True)
    unit_of_measure = Column(String, nullable=True)
    price = Column(Numeric(15, 2), nullable=True)
    quantity = Column(Numeric(15, 4), nullable=True)
    item_type = Column(String, nullable=True)
    batch_id = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    is_official = Column(Boolean, nullable=False, default=True)
    issued_to_recipient_id = Column(Integer, ForeignKey("recipients.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    documents = relationship("AssetDocument", secondary="item_documents", viewonly=True)
    issued_to = relationship("Recipient", foreign_keys=[issued_to_recipient_id])

    @property
    def issued_to_name(self):
        # Surfaced through Pydantic schemas via `from_attributes=True`
        # (Pydantic treats this property the same as a column).
        return self.issued_to.callsign if self.issued_to else None

    splits = relationship(
        "ItemSplit",
        primaryjoin="Item.id == foreign(ItemSplit.item_id)",
        viewonly=True,
    )

    @property
    def total_issued(self):
        """SUM of qty for active (not-yet-returned) splits."""
        if not self.splits:
            return Decimal(0)
        total = Decimal(0)
        for s in self.splits:
            if s.returned_at is None:
                total += Decimal(s.qty or 0)
        return total

    @property
    def free_qty(self):
        return Decimal(self.quantity or 0) - self.total_issued


class AssetDocument(Base):
    __tablename__ = "asset_documents"

    id = Column(Integer, primary_key=True)
    doc_type = Column(String, nullable=True)
    doc_number = Column(String, nullable=True)
    doc_date = Column(String, nullable=True)


class ItemDocument(Base):
    __tablename__ = "item_documents"

    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True)
    doc_id = Column(Integer, ForeignKey("asset_documents.id", ondelete="CASCADE"), primary_key=True)


class Movement(Base):
    __tablename__ = "movements"

    id = Column(Integer, primary_key=True)
    entry_date = Column(String, nullable=True)
    item_name = Column(String, nullable=True)
    item_card_num = Column(String, ForeignKey("items.number", ondelete="SET NULL"), nullable=True)
    unit_of_measure = Column(String, nullable=True)
    category = Column(String, nullable=True)
    qty_in = Column(Numeric(15, 4), nullable=True)
    qty_out = Column(Numeric(15, 4), nullable=True)
    from_unit = Column(String, nullable=True)
    to_unit = Column(String, nullable=True)
    mvo_from_id = Column(Integer, ForeignKey("persons.id", ondelete="SET NULL"), nullable=True)
    mvo_to_id = Column(Integer, ForeignKey("persons.id", ondelete="SET NULL"), nullable=True)
    basis = Column(String, nullable=True)
    doc_date = Column(String, nullable=True)
    doc_number = Column(String, nullable=True)
    serial_number = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    executor_id = Column(Integer, ForeignKey("persons.id", ondelete="SET NULL"), nullable=True)
    nomenclature_code = Column(String, nullable=True)
    price = Column(Numeric(15, 2), nullable=True)
    service = Column(String, nullable=True)
    op_type_id = Column(Integer, ForeignKey("op_types.id", ondelete="SET NULL"), nullable=True)
    op_type_detail_id = Column(Integer, ForeignKey("op_type_details.id", ondelete="SET NULL"), nullable=True)
    doc_type = Column(String, nullable=True)
    recipient_category = Column(String, nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    document = relationship("Document", back_populates="movements")
    mvo_from = relationship("Person", foreign_keys=[mvo_from_id])
    mvo_to   = relationship("Person", foreign_keys=[mvo_to_id])


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    operation = Column(String, nullable=False)  # 'надходження' | 'переміщення'
    form = Column(String, nullable=False)       # 'накладна' | 'акт'
    doc_number = Column(String, nullable=True)
    doc_date = Column(String, nullable=True)           # date_compiled
    date_operation = Column(String, nullable=True)
    from_unit = Column(String, nullable=True)
    to_unit = Column(String, nullable=True)
    basis = Column(String, nullable=True)
    service = Column(String, nullable=True)
    op_type_id = Column(Integer, ForeignKey("op_types.id", ondelete="SET NULL"), nullable=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True)
    sender_id = Column(Integer, ForeignKey("persons.id", ondelete="SET NULL"), nullable=True)
    receiver_id = Column(Integer, ForeignKey("persons.id", ondelete="SET NULL"), nullable=True)
    fin_id = Column(Integer, ForeignKey("persons.id", ondelete="SET NULL"), nullable=True)
    status = Column(String, nullable=False, default="draft")  # draft | signed | receiver_signed
    signed_at = Column(DateTime, nullable=True)
    signed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    items = relationship("DocumentItem", back_populates="document", cascade="all, delete-orphan")
    movements = relationship("Movement", back_populates="document")


class DocumentItem(Base):
    __tablename__ = "document_items"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    sort_order = Column(Integer, nullable=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="SET NULL"), nullable=True)
    item_name = Column(String, nullable=True)
    nomenclature_code = Column(String, nullable=True)
    unit_of_measure = Column(String, nullable=True)
    category = Column(String, nullable=True)
    quantity = Column(Numeric(15, 4), nullable=True)
    qty_received = Column(Numeric(15, 4), nullable=True)
    price = Column(Numeric(15, 2), nullable=True)
    amount = Column(Numeric(15, 2), nullable=True)
    notes = Column(Text, nullable=True)

    document = relationship("Document", back_populates="items")


class ItemSplit(Base):
    """Per-recipient issuance of a non-serial item's qty.

    Free-on-hand for an item = item.quantity - SUM(qty WHERE returned_at IS NULL).
    """
    __tablename__ = "item_splits"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("recipients.id", ondelete="SET NULL"), nullable=True)
    qty = Column(Numeric(15, 4), nullable=False)
    issued_at = Column(Date, nullable=False)
    returned_at = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    return_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    item = relationship("Item")
    recipient = relationship("Recipient")

    @property
    def is_active(self) -> bool:
        return self.returned_at is None

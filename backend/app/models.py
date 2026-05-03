from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, Numeric,
    String, Text, UniqueConstraint, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base


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
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    documents = relationship("AssetDocument", secondary="item_documents", viewonly=True)


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
    doc_type = Column(String, nullable=False)  # 'надходження' | 'переміщення' | 'накладна_25'
    doc_number = Column(String, nullable=True)
    doc_date = Column(String, nullable=True)
    from_unit = Column(String, nullable=True)
    to_unit = Column(String, nullable=True)
    basis = Column(String, nullable=True)
    service = Column(String, nullable=True)
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

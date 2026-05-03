"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-02 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("unit_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("short_name", sa.String(), nullable=True),
        sa.Column("edrpou", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=True))
    op.create_table("op_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True))
    op.create_table("op_type_details",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("op_type_id", sa.Integer(), sa.ForeignKey("op_types.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(), nullable=False, unique=True))
    op.create_table("users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="operator"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.create_table("persons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("position", sa.String(), nullable=True),
        sa.Column("position_genitive", sa.String(), nullable=True),
        sa.Column("rank", sa.String(), nullable=True),
        sa.Column("rank_genitive", sa.String(), nullable=True),
        sa.Column("last_name", sa.String(), nullable=True),
        sa.Column("last_name_genitive", sa.String(), nullable=True),
        sa.Column("first_name", sa.String(), nullable=True),
        sa.Column("first_name_genitive", sa.String(), nullable=True),
        sa.Column("patronymic", sa.String(), nullable=True),
        sa.Column("patronymic_genitive", sa.String(), nullable=True),
        sa.Column("search_name", sa.String(), nullable=True),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("unit_locative", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.create_table("items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("number", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("nomenclature_code", sa.String(), nullable=True),
        sa.Column("serial_number", sa.String(), nullable=True),
        sa.Column("unit_of_measure", sa.String(), nullable=True),
        sa.Column("price", sa.Numeric(15, 2), nullable=True),
        sa.Column("quantity", sa.Numeric(15, 4), nullable=True),
        sa.Column("item_type", sa.String(), nullable=True),
        sa.Column("batch_id", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_official", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    op.create_table("asset_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("doc_type", sa.String(), nullable=True),
        sa.Column("doc_number", sa.String(), nullable=True),
        sa.Column("doc_date", sa.String(), nullable=True))
    op.create_table("item_documents",
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("doc_id", sa.Integer(), sa.ForeignKey("asset_documents.id", ondelete="CASCADE"), primary_key=True))
    op.create_table("movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entry_date", sa.String(), nullable=True),
        sa.Column("item_name", sa.String(), nullable=True),
        sa.Column("item_card_num", sa.String(), sa.ForeignKey("items.number", ondelete="SET NULL"), nullable=True),
        sa.Column("unit_of_measure", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("qty_in", sa.Numeric(15, 4), nullable=True),
        sa.Column("qty_out", sa.Numeric(15, 4), nullable=True),
        sa.Column("from_unit", sa.String(), nullable=True),
        sa.Column("to_unit", sa.String(), nullable=True),
        sa.Column("mvo_from_id", sa.Integer(), sa.ForeignKey("persons.id", ondelete="SET NULL"), nullable=True),
        sa.Column("mvo_to_id", sa.Integer(), sa.ForeignKey("persons.id", ondelete="SET NULL"), nullable=True),
        sa.Column("basis", sa.String(), nullable=True),
        sa.Column("doc_date", sa.String(), nullable=True),
        sa.Column("doc_number", sa.String(), nullable=True),
        sa.Column("serial_number", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("executor_id", sa.Integer(), sa.ForeignKey("persons.id", ondelete="SET NULL"), nullable=True),
        sa.Column("nomenclature_code", sa.String(), nullable=True),
        sa.Column("price", sa.Numeric(15, 2), nullable=True),
        sa.Column("service", sa.String(), nullable=True),
        sa.Column("op_type_id", sa.Integer(), sa.ForeignKey("op_types.id", ondelete="SET NULL"), nullable=True),
        sa.Column("op_type_detail_id", sa.Integer(), sa.ForeignKey("op_type_details.id", ondelete="SET NULL"), nullable=True),
        sa.Column("doc_type", sa.String(), nullable=True),
        sa.Column("recipient_category", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    op.create_table("print_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("doc_type", sa.String(), nullable=True),
        sa.Column("doc_number", sa.String(), nullable=True),
        sa.Column("doc_date", sa.String(), nullable=True),
        sa.Column("from_unit", sa.String(), nullable=True),
        sa.Column("to_unit", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    op.create_table("print_document_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("print_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_name", sa.String(), nullable=True),
        sa.Column("nomenclature_code", sa.String(), nullable=True),
        sa.Column("unit_of_measure", sa.String(), nullable=True),
        sa.Column("quantity", sa.Numeric(15, 4), nullable=True),
        sa.Column("price", sa.Numeric(15, 2), nullable=True),
        sa.Column("amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("vat", sa.Numeric(15, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_table("print_document_items")
    op.drop_table("print_documents")
    op.drop_table("movements")
    op.drop_table("item_documents")
    op.drop_table("asset_documents")
    op.drop_table("items")
    op.drop_table("persons")
    op.drop_table("users")
    op.drop_table("op_type_details")
    op.drop_table("op_types")
    op.drop_table("unit_settings")

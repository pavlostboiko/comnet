"""replace print_documents with documents + document_items, add document_id to movements

Revision ID: 003
Revises: 002
Create Date: 2026-05-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old print tables (no real data)
    op.drop_table("print_document_items")
    op.drop_table("print_documents")

    # Main documents table — all doc types: 'надходження' | 'переміщення' | 'накладна_25'
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("doc_type", sa.String(), nullable=False),
        sa.Column("doc_number", sa.String(), nullable=True),
        sa.Column("doc_date", sa.String(), nullable=True),
        sa.Column("from_unit", sa.String(), nullable=True),
        sa.Column("to_unit", sa.String(), nullable=True),
        sa.Column("basis", sa.String(), nullable=True),
        sa.Column("service", sa.String(), nullable=True),
        # status: draft | signed | receiver_signed
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "signed_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Line items for documents
    op.create_table(
        "document_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("item_name", sa.String(), nullable=True),
        sa.Column("nomenclature_code", sa.String(), nullable=True),
        sa.Column("unit_of_measure", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("quantity", sa.Numeric(15, 4), nullable=True),
        sa.Column("qty_received", sa.Numeric(15, 4), nullable=True),
        sa.Column("price", sa.Numeric(15, 2), nullable=True),
        sa.Column("amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    # Link movements to their source document
    op.add_column(
        "movements",
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("movements", "document_id")
    op.drop_table("document_items")
    op.drop_table("documents")

    op.create_table(
        "print_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("doc_type", sa.String(), nullable=True),
        sa.Column("doc_number", sa.String(), nullable=True),
        sa.Column("doc_date", sa.String(), nullable=True),
        sa.Column("from_unit", sa.String(), nullable=True),
        sa.Column("to_unit", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_table(
        "print_document_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("print_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_name", sa.String(), nullable=True),
        sa.Column("nomenclature_code", sa.String(), nullable=True),
        sa.Column("unit_of_measure", sa.String(), nullable=True),
        sa.Column("quantity", sa.Numeric(15, 4), nullable=True),
        sa.Column("price", sa.Numeric(15, 2), nullable=True),
        sa.Column("amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("vat", sa.Numeric(15, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )

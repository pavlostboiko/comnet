"""add category and qty_received to print_document_items (legacy, superseded by 003)

Revision ID: 002
Revises: 001
Create Date: 2026-05-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("print_document_items", sa.Column("category", sa.String(), nullable=True))
    op.add_column("print_document_items", sa.Column("qty_received", sa.Numeric(15, 4), nullable=True))
    op.add_column("print_document_items", sa.Column("sort_order", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("print_document_items", "sort_order")
    op.drop_column("print_document_items", "qty_received")
    op.drop_column("print_document_items", "category")

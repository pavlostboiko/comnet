"""add op_types.number_prefix and document FK columns for snapshot doc model

Revision ID: 005
Revises: 004
Create Date: 2026-05-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("op_types", sa.Column("number_prefix", sa.String(), nullable=True))

    op.add_column(
        "documents",
        sa.Column(
            "op_type_id",
            sa.Integer(),
            sa.ForeignKey("op_types.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "service_id",
            sa.Integer(),
            sa.ForeignKey("services.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "sender_id",
            sa.Integer(),
            sa.ForeignKey("persons.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "receiver_id",
            sa.Integer(),
            sa.ForeignKey("persons.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "fin_id",
            sa.Integer(),
            sa.ForeignKey("persons.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("documents", sa.Column("date_operation", sa.String(), nullable=True))

    op.add_column(
        "document_items",
        sa.Column(
            "item_id",
            sa.Integer(),
            sa.ForeignKey("items.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("document_items", "item_id")
    op.drop_column("documents", "date_operation")
    op.drop_column("documents", "fin_id")
    op.drop_column("documents", "receiver_id")
    op.drop_column("documents", "sender_id")
    op.drop_column("documents", "service_id")
    op.drop_column("documents", "op_type_id")
    op.drop_column("op_types", "number_prefix")

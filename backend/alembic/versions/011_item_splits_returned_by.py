"""add item_splits.returned_by → users FK

Revision ID: 011
Revises: 010
Create Date: 2026-07-10

Track who processed the return of an item_split. Complements the existing
created_by (who issued it). Together with issued_at/returned_at they answer
«хто і коли» for the issuance ledger — no separate audit-log required for
this specific event pair.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "item_splits",
        sa.Column(
            "returned_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("item_splits", "returned_by")

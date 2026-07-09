"""create item_splits — per-recipient issuance ledger for non-serial items

Revision ID: 009
Revises: 008
Create Date: 2026-07-09

Non-serial items sit as a single card with quantity=N. `item_splits` records
who received how much, when, and if/when they returned it. Free-on-hand =
item.quantity − SUM(active splits.qty). Serial items keep the quick
issued_to_recipient_id shortcut.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "item_splits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "item_id",
            sa.Integer(),
            sa.ForeignKey("items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "recipient_id",
            sa.Integer(),
            sa.ForeignKey("recipients.id", ondelete="SET NULL"),
            nullable=True,  # SET NULL keeps history when a recipient is removed
        ),
        sa.Column("qty", sa.Numeric(15, 4), nullable=False),
        sa.Column("issued_at", sa.Date(), nullable=False),
        sa.Column("returned_at", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("return_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_item_splits_item", "item_splits", ["item_id"])
    op.create_index("ix_item_splits_active", "item_splits", ["item_id"],
                    postgresql_where=sa.text("returned_at IS NULL"))


def downgrade() -> None:
    op.drop_index("ix_item_splits_active", table_name="item_splits")
    op.drop_index("ix_item_splits_item", table_name="item_splits")
    op.drop_table("item_splits")

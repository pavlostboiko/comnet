"""create recipients table; rename items.issued_to_person_id → issued_to_recipient_id

Revision ID: 008
Revises: 007
Create Date: 2026-06-06

`persons` keeps chiefs / signatories (МВО, командири, начальники служб).
`recipients` is the everyday personnel list (бійці), identified by callsign.
Items получають issued_to_recipient_id (FK → recipients) — the «Видане»
column now points at a callsign, not at a chief from persons.

Existing items.issued_to_person_id data is nulled — feature was recent and
its entries are test-only (confirmed with user 2026-06-06).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recipients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("callsign", sa.String(), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Drop the old FK pointing at persons; null the column data first
    op.execute("UPDATE items SET issued_to_person_id = NULL")
    op.drop_column("items", "issued_to_person_id")

    op.add_column(
        "items",
        sa.Column(
            "issued_to_recipient_id",
            sa.Integer(),
            sa.ForeignKey("recipients.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("items", "issued_to_recipient_id")
    op.add_column(
        "items",
        sa.Column(
            "issued_to_person_id",
            sa.Integer(),
            sa.ForeignKey("persons.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.drop_table("recipients")

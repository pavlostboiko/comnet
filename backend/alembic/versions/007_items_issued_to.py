"""add items.issued_to_person_id — denormalized current-holder pointer

Revision ID: 007
Revises: 006
Create Date: 2026-05-28

For volunteer items, the user adds them directly via /items + immediately
points them at a recipient person. For serial official items it works as a
quick «who has it» pointer. For split non-serial assignments (5 to person A,
3 to person B) — use the future issuances ledger (backlog).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "items",
        sa.Column(
            "issued_to_person_id",
            sa.Integer(),
            sa.ForeignKey("persons.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("items", "issued_to_person_id")

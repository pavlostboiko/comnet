"""add users.person_id → persons FK

Revision ID: 010
Revises: 009
Create Date: 2026-07-09

Links a login account to a Person from the persons directory. Non-admin
users use this link to scope their view to their own subdivision
(persons.unit) — e.g. МВО login → see only the residues for their unit.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "person_id",
            sa.Integer(),
            sa.ForeignKey("persons.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "person_id")

"""v2: units.is_external (внутрішній / зовнішній підрозділ)

Revision ID: 021
Revises: 020
Create Date: 2026-07-26

Зовнішні підрозділи передають нам майно (джерело приймання). По внутрішніх —
переміщення; залишки цікавлять лише по внутрішніх. Наявні підрозділи = внутрішні.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("units", sa.Column("is_external", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("units", "is_external")

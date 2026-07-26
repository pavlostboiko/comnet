"""v2: instances.note (примітка на екземплярі серійного майна)

Revision ID: 022
Revises: 021
Create Date: 2026-07-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("instances", sa.Column("note", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("instances", "note")

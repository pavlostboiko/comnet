"""add services table

Revision ID: 004
Revises: 003
Create Date: 2026-05-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("chief_name", sa.String(), nullable=True),
        sa.Column("chief_position", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("services")

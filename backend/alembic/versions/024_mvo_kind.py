"""mvo.kind ('warehouse'|'fin') + warehouse_id nullable — глобальний фін-МВО

Revision ID: 024
Revises: 023
Create Date: 2026-07-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mvo", sa.Column("kind", sa.String(), nullable=False, server_default="warehouse"))
    op.alter_column("mvo", "warehouse_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.alter_column("mvo", "warehouse_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("mvo", "kind")

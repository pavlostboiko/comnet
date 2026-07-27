"""v2 Phase 4: user two-axis scope fields

Revision ID: 016
Revises: 015
Create Date: 2026-07-22

Розширює users полями доступу: service_id (роль service), unit_id + warehouse_id
(роль mvo). Ролі service/mvo додаються без окремої таблиці — щоб не переписувати
JWT/auth.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("service_id", sa.Integer(),
                  sa.ForeignKey("services.id", ondelete="SET NULL"), nullable=True))
    op.add_column("users", sa.Column("unit_id", sa.Integer(),
                  sa.ForeignKey("units.id", ondelete="SET NULL"), nullable=True))
    op.add_column("users", sa.Column("warehouse_id", sa.Integer(),
                  sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "warehouse_id")
    op.drop_column("users", "unit_id")
    op.drop_column("users", "service_id")

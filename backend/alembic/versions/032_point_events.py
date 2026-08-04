"""журнал переміщень майна між точками зберігання

Зміна точки — така сама подія обліку, як рух чи видача, і має бути в загальній
історії. Свідомо НЕ виводимо її з `audit_log`: той журнал технічний і буде
перероблятись, а доменна подія має жити окремо.

Одна з трьох прив'язок заповнена: `instance_id` (серійне), `assignment_id`
(видане несерійне) або лише `nomenclature_id` (мітка залишку картки на складі).

Revision ID: 032
Revises: 031
Create Date: 2026-08-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "032"
down_revision: Union[str, None] = "031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "point_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("nomenclature_id", sa.Integer(),
                  sa.ForeignKey("nomenclature.id", ondelete="CASCADE"), nullable=False),
        sa.Column("instance_id", sa.Integer(),
                  sa.ForeignKey("instances.id", ondelete="CASCADE"), nullable=True),
        sa.Column("assignment_id", sa.Integer(),
                  sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=True),
        sa.Column("warehouse_id", sa.Integer(),
                  sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        # Точки можуть зникнути з довідника — подія лишається, назви беремо знімком.
        sa.Column("from_point_id", sa.Integer(),
                  sa.ForeignKey("storage_points.id", ondelete="SET NULL"), nullable=True),
        sa.Column("to_point_id", sa.Integer(),
                  sa.ForeignKey("storage_points.id", ondelete="SET NULL"), nullable=True),
        sa.Column("from_point_name", sa.String(), nullable=True),
        sa.Column("to_point_name", sa.String(), nullable=True),
        sa.Column("quantity", sa.Numeric(15, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_point_events_wh", "point_events", ["warehouse_id"])
    op.create_index("ix_point_events_nom", "point_events", ["nomenclature_id"])


def downgrade() -> None:
    op.drop_index("ix_point_events_nom", table_name="point_events")
    op.drop_index("ix_point_events_wh", table_name="point_events")
    op.drop_table("point_events")

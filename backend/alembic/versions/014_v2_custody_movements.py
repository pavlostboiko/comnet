"""v2 Phase 3a: custody_movements

Revision ID: 014
Revises: 013
Create Date: 2026-07-22

Additive — v1 `movements` untouched (dropped at cutover). Це v2-леджер custody:
рух склад→склад. Баланси рахуються з нього (не окрема таблиця).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "custody_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("from_warehouse_id", sa.Integer(),
                  sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("to_warehouse_id", sa.Integer(),
                  sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("nomenclature_id", sa.Integer(),
                  sa.ForeignKey("nomenclature.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("instance_id", sa.Integer(),
                  sa.ForeignKey("instances.id", ondelete="SET NULL"), nullable=True),
        sa.Column("quantity", sa.Numeric(15, 4), nullable=False),
        sa.Column("is_official", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("signed_by_person_id", sa.Integer(),
                  sa.ForeignKey("persons.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_custody_nom", "custody_movements", ["nomenclature_id"])
    op.create_index("ix_custody_instance", "custody_movements", ["instance_id"])


def downgrade() -> None:
    op.drop_index("ix_custody_instance", table_name="custody_movements")
    op.drop_index("ix_custody_nom", table_name="custody_movements")
    op.drop_table("custody_movements")

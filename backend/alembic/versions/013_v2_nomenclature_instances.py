"""v2 Phase 2: nomenclature + instances

Revision ID: 013
Revises: 012
Create Date: 2026-07-22

Additive — v1 `items` untouched. `nomenclature` = тип майна (заміна items-як-картки),
`instances` = серійні екземпляри. current_warehouse_id заповниться у Фазі 3.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "nomenclature",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("service_id", sa.Integer(),
                  sa.ForeignKey("services.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("is_serialized", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("unit_of_measure", sa.String(), nullable=True),
        sa.Column("code", sa.String(), nullable=True),
        sa.Column("price", sa.Numeric(15, 2), nullable=True),
    )
    op.create_table(
        "instances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nomenclature_id", sa.Integer(),
                  sa.ForeignKey("nomenclature.id", ondelete="CASCADE"), nullable=False),
        sa.Column("serial_no", sa.String(), nullable=False, unique=True),
        sa.Column("current_warehouse_id", sa.Integer(),
                  sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_official", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_table("instances")
    op.drop_table("nomenclature")

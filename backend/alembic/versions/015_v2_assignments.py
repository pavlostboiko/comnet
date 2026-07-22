"""v2 Phase 3b: assignments

Revision ID: 015
Revises: 014
Create Date: 2026-07-22

Видача особовому складу. НЕ рухає custody — окремий шар «хто тримає на руках».
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("warehouse_id", sa.Integer(),
                  sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("person_id", sa.Integer(),
                  sa.ForeignKey("persons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nomenclature_id", sa.Integer(),
                  sa.ForeignKey("nomenclature.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("instance_id", sa.Integer(),
                  sa.ForeignKey("instances.id", ondelete="SET NULL"), nullable=True),
        sa.Column("quantity", sa.Numeric(15, 4), nullable=False),
        sa.Column("is_official", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("issued_date", sa.Date(), nullable=False),
        sa.Column("returned_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("returned_by", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_assign_warehouse", "assignments", ["warehouse_id"])
    op.create_index("ix_assign_person", "assignments", ["person_id"])


def downgrade() -> None:
    op.drop_index("ix_assign_person", table_name="assignments")
    op.drop_index("ix_assign_warehouse", table_name="assignments")
    op.drop_table("assignments")

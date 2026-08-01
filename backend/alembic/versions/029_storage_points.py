"""точки зберігання: фізичне розміщення всередині складу

Майно обліково висить на ОДНОМУ складі (з нього ж іде в документи), але фізично
може лежати в різних точках. Точка — довідник, прив'язаний до складу, і атрибут
розміщення: для серійного — на екземплярі, для несерійного — позначка на пару
(картка, склад) без розподілу кількості. Леджер/баланси не змінюються.

Revision ID: 029
Revises: 028
Create Date: 2026-08-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "029"
down_revision: Union[str, None] = "028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "storage_points",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(),
                  sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("warehouse_id", "name", name="uq_storage_point_name"),
    )
    op.add_column("instances", sa.Column("storage_point_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_instance_storage_point", "instances", "storage_points",
                          ["storage_point_id"], ["id"], ondelete="SET NULL")

    # Несерійне: одна точка на (картка, склад) — «все це лежить тут».
    op.create_table(
        "nomenclature_points",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nomenclature_id", sa.Integer(),
                  sa.ForeignKey("nomenclature.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", sa.Integer(),
                  sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("storage_point_id", sa.Integer(),
                  sa.ForeignKey("storage_points.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("nomenclature_id", "warehouse_id", name="uq_nom_point"),
    )


def downgrade() -> None:
    op.drop_table("nomenclature_points")
    op.drop_constraint("fk_instance_storage_point", "instances", type_="foreignkey")
    op.drop_column("instances", "storage_point_id")
    op.drop_table("storage_points")

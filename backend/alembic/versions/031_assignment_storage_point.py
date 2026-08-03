"""точка зберігання для виданого несерійного (на конкретній видачі)

Точка несерійного — мітка на парі (картка, склад), спільна для всього залишку.
Для виданого це не годиться: у кожної видачі своє місце. Серійному вистачає
`instances.storage_point_id` (екземпляр і після видачі числиться на складі), а
несерійному потрібне поле на самій видачі.

Revision ID: 031
Revises: 030
Create Date: 2026-08-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "031"
down_revision: Union[str, None] = "030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("assignments", sa.Column("storage_point_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_assignment_storage_point", "assignments", "storage_points",
                          ["storage_point_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_assignment_storage_point", "assignments", type_="foreignkey")
    op.drop_column("assignments", "storage_point_id")

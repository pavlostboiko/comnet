"""mvo.service_id — начальник служби як третій вид підписанта

Начальник служби підписує накладну поряд з МВО складів і фінслужбою, але досі
жив вільним текстом у `services.chief_name/chief_position` — без історії, тож
стара накладна показувала поточного начальника, а не того, хто підписував.

Додаємо `mvo.service_id` для записів `kind='service_chief'` (один діючий на
службу). `services.chief_*` лишаються фолбеком, доки служби не заведені в
журнал: бекфіл неможливий — це вільний текст без звʼязку з `persons`.

Revision ID: 028
Revises: 027
Create Date: 2026-07-31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "028"
down_revision: Union[str, None] = "027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mvo", sa.Column("service_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_mvo_service", "mvo", "services", ["service_id"], ["id"],
                          ondelete="CASCADE")


def downgrade() -> None:
    op.drop_constraint("fk_mvo_service", "mvo", type_="foreignkey")
    op.drop_column("mvo", "service_id")

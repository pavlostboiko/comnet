"""v2: nomenclature.is_official (облік / ндм)

Revision ID: 019
Revises: 018
Create Date: 2026-07-25

Тип обліку — властивість картки (номенклатури): облік (is_official=true) або
ндм (false). Рухи/екземпляри успадковують його. Раніше is_official був лише
виміром балансу; тепер задається при створенні картки.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("nomenclature", sa.Column("is_official", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("nomenclature", "is_official")

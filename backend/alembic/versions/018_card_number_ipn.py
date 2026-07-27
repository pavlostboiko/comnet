"""v2: card_number linking + doc_number + person ipn

Revision ID: 018
Revises: 017
Create Date: 2026-07-24

- instances.card_number — фактичний номер картки (Items «№»), join з Переміщеннями
- custody_movements.card_number (Переміщення «Поле 12») + doc_number (номер накладної)
- persons.ipn — ІПН (заповнюється вручну)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("instances", sa.Column("card_number", sa.String(), nullable=True))
    op.add_column("custody_movements", sa.Column("card_number", sa.String(), nullable=True))
    op.add_column("custody_movements", sa.Column("doc_number", sa.String(), nullable=True))
    op.add_column("persons", sa.Column("ipn", sa.String(), nullable=True))
    op.create_index("ix_instances_card", "instances", ["card_number"])


def downgrade() -> None:
    op.drop_index("ix_instances_card", table_name="instances")
    op.drop_column("persons", "ipn")
    op.drop_column("custody_movements", "doc_number")
    op.drop_column("custody_movements", "card_number")
    op.drop_column("instances", "card_number")

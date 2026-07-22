"""v2 foundations: units, groups, warehouses, mvo + services/persons extend

Revision ID: 012
Revises: 011
Create Date: 2026-07-22

Phase 1 of the v2 rewrite (see database_v2_plan.md). ADDITIVE only — старі
таблиці/колонки лишаються, доки їхні залежності не приберуться в пізніших фазах.
Кінцевий стан (після cutover) старих inventory-таблиць не містить.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # services.code
    op.add_column("services", sa.Column("code", sa.String(), nullable=True))

    # units
    op.create_table(
        "units",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("code", sa.String(), nullable=True),
        sa.Column("name_locative", sa.String(), nullable=True),
    )

    # groups (commander → persons, вже існує)
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("unit_id", sa.Integer(),
                  sa.ForeignKey("units.id", ondelete="CASCADE"), nullable=False),
        sa.Column("commander_id", sa.Integer(),
                  sa.ForeignKey("persons.id", ondelete="SET NULL"), nullable=True),
    )

    # persons v2 columns
    op.add_column("persons", sa.Column("unit_id", sa.Integer(),
                  sa.ForeignKey("units.id", ondelete="SET NULL"), nullable=True))
    op.add_column("persons", sa.Column("callsign", sa.String(), nullable=True))
    op.add_column("persons", sa.Column("group_id", sa.Integer(),
                  sa.ForeignKey("groups.id", ondelete="SET NULL"), nullable=True))

    # warehouses
    op.create_table(
        "warehouses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),  # 'service' | 'unit'
        sa.Column("service_id", sa.Integer(),
                  sa.ForeignKey("services.id", ondelete="CASCADE"), nullable=True),
        sa.Column("unit_id", sa.Integer(),
                  sa.ForeignKey("units.id", ondelete="CASCADE"), nullable=True),
    )

    # mvo
    op.create_table(
        "mvo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("warehouse_id", sa.Integer(),
                  sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("person_id", sa.Integer(),
                  sa.ForeignKey("persons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_date", sa.Date(), nullable=False),
        sa.Column("to_date", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("mvo")
    op.drop_table("warehouses")
    op.drop_column("persons", "group_id")
    op.drop_column("persons", "callsign")
    op.drop_column("persons", "unit_id")
    op.drop_table("groups")
    op.drop_table("units")
    op.drop_column("services", "code")

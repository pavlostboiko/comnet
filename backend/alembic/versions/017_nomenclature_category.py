"""v2: nomenclature.category

Revision ID: 017
Revises: 016
Create Date: 2026-07-24

Категорія майна всередині служби (номенклатурна група) — для каталогу
«Майно» з фільтром по службі + категорії.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("nomenclature", sa.Column("category", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("nomenclature", "category")

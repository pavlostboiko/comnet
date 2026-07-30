"""move посада/звання from persons to mvo journal entries

Post + rank are only meaningful for МВО signatories, and belong to an
*assignment period* rather than to a person globally (a person's post can
change over time). Add mvo.position/mvo.rank, backfill from the linked person
for currently-active entries, then drop the person columns (incl. the dead
*_genitive pair).

⚠️ Down-migration re-adds the person columns but cannot restore their data.

Revision ID: 027
Revises: 026
Create Date: 2026-07-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "027"
down_revision: Union[str, None] = "026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mvo", sa.Column("position", sa.String(), nullable=True))
    op.add_column("mvo", sa.Column("rank", sa.String(), nullable=True))

    # Backfill active (to_date IS NULL) journal entries from the linked person.
    op.execute(
        'UPDATE mvo SET "position" = p."position", "rank" = p."rank" '
        "FROM persons p WHERE mvo.person_id = p.id AND mvo.to_date IS NULL"
    )

    for col in ("position", "rank", "position_genitive", "rank_genitive"):
        op.drop_column("persons", col)


def downgrade() -> None:
    for col in ("position", "rank", "position_genitive", "rank_genitive"):
        op.add_column("persons", sa.Column(col, sa.String(), nullable=True))
    op.drop_column("mvo", "rank")
    op.drop_column("mvo", "position")

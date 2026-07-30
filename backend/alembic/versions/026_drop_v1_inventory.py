"""drop v1 inventory tables (items/movements/documents/residues/splits/recipients)

The v1 inventory system is retired in favour of the v2 custody/assignment
model. Its tables carry no FK from any v2 table, so they can be dropped
outright. `op_type_details` is intentionally KEPT (still a live dictionary).

⚠️ IRREVERSIBLE: this deletes all v1 data. Take a pg_dump before deploying.
downgrade() cannot restore the data and is therefore not implemented.

Revision ID: 026
Revises: 025
Create Date: 2026-07-30
"""
from typing import Sequence, Union

from alembic import op

revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Child tables first; CASCADE + IF EXISTS make this robust to FK order and to
# prod databases where some tables may already be absent.
_V1_TABLES = (
    "item_documents",
    "item_splits",
    "document_items",
    "movements",
    "documents",
    "items",
    "asset_documents",
    "recipients",
)


def upgrade() -> None:
    for table in _V1_TABLES:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")


def downgrade() -> None:
    raise NotImplementedError(
        "Dropping the v1 inventory tables is irreversible; restore from a "
        "pre-deploy pg_dump backup instead."
    )

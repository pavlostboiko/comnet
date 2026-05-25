"""split documents.doc_type into operation + form columns

Revision ID: 006
Revises: 005
Create Date: 2026-05-25

Two-axis model:
  operation ∈ {надходження, переміщення}    — business intent
  form      ∈ {накладна, акт}                — paper artefact

Legacy doc_type values backfill to:
  надходження                  → operation=надходження, form=акт
  переміщення  / накладна_25   → operation=переміщення, form=накладна
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("operation", sa.String(), nullable=True))
    op.add_column("documents", sa.Column("form",      sa.String(), nullable=True))

    op.execute("""
        UPDATE documents
        SET operation = 'надходження', form = 'акт'
        WHERE doc_type = 'надходження'
    """)
    op.execute("""
        UPDATE documents
        SET operation = 'переміщення', form = 'накладна'
        WHERE doc_type IN ('переміщення', 'накладна_25')
    """)
    # Defensive: any unexpected legacy value lands in receipt-as-act
    op.execute("""
        UPDATE documents
        SET operation = 'надходження', form = 'акт'
        WHERE operation IS NULL OR form IS NULL
    """)

    op.alter_column("documents", "operation", nullable=False)
    op.alter_column("documents", "form",      nullable=False)
    op.drop_column("documents", "doc_type")


def downgrade() -> None:
    op.add_column("documents", sa.Column("doc_type", sa.String(), nullable=True))
    op.execute("""
        UPDATE documents
        SET doc_type = CASE
            WHEN operation = 'переміщення' AND form = 'накладна' THEN 'накладна_25'
            WHEN operation = 'надходження' THEN 'надходження'
            ELSE 'переміщення'
        END
    """)
    op.alter_column("documents", "doc_type", nullable=False)
    op.drop_column("documents", "form")
    op.drop_column("documents", "operation")

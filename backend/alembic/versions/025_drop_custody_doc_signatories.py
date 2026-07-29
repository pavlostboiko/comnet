"""custody_documents: drop sender_id/receiver_id/fin_id (МВО з журналу по даті)

Revision ID: 025
Revises: 024
Create Date: 2026-07-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for col in ("sender_id", "receiver_id", "fin_id"):
        op.drop_column("custody_documents", col)


def downgrade() -> None:
    for col in ("sender_id", "receiver_id", "fin_id"):
        op.add_column("custody_documents",
                      sa.Column(col, sa.Integer(), nullable=True))

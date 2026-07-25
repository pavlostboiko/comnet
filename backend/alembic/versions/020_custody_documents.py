"""v2: custody_documents (шапка накладної/акта) + custody_movements.document_id FK

Revision ID: 020
Revises: 019
Create Date: 2026-07-25

Документ v2 — шар паперу над леджером. Реквізити (номер, форма, дати, звідки/куди,
контрагент, МВО-підписанти, службу, snap) тримаються ОДИН раз у custody_documents;
рядки custody_movements лінкуються через document_id. Рухи проводяться одразу —
sign/unsign НЕ створюють і НЕ видаляють леджер-рядки (свідоме відхилення від v1).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "custody_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("operation", sa.String(), nullable=False),   # receipt | transfer
        sa.Column("form", sa.String(), nullable=False),        # накладна | акт
        sa.Column("doc_number", sa.String(), nullable=True),
        sa.Column("doc_date", sa.String(), nullable=True),
        sa.Column("date_operation", sa.String(), nullable=True),
        sa.Column("from_warehouse_id", sa.Integer(),
                  sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("to_warehouse_id", sa.Integer(),
                  sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("from_unit", sa.String(), nullable=True),    # snap-назва складу-джерела
        sa.Column("to_unit", sa.String(), nullable=True),      # snap-назва складу-отримувача
        sa.Column("counterparty", sa.String(), nullable=True), # від кого (приймання ззовні)
        sa.Column("basis", sa.String(), nullable=True),
        sa.Column("service", sa.String(), nullable=True),      # денормалізована назва
        sa.Column("service_id", sa.Integer(),
                  sa.ForeignKey("services.id", ondelete="SET NULL"), nullable=True),
        sa.Column("op_type_id", sa.Integer(),
                  sa.ForeignKey("op_types.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sender_id", sa.Integer(),
                  sa.ForeignKey("persons.id", ondelete="SET NULL"), nullable=True),
        sa.Column("receiver_id", sa.Integer(),
                  sa.ForeignKey("persons.id", ondelete="SET NULL"), nullable=True),
        sa.Column("fin_id", sa.Integer(),
                  sa.ForeignKey("persons.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
        sa.Column("signed_by", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    # custody_movements.document_id уже існує як простий Integer → додаємо FK.
    op.create_foreign_key(
        "fk_custody_movements_document_id", "custody_movements",
        "custody_documents", ["document_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_custody_movements_document_id", "custody_movements", type_="foreignkey")
    op.drop_table("custody_documents")

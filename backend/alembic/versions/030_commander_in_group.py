"""бекфіл: командир групи стає її членом

`groups.commander_id` (хто командир) і `persons.group_id` (членство) ніде не
були звʼязані, тож група з призначеним командиром лишалась порожньою — звіт
«Видане на групу» не показував нічого. Роутер тепер проставляє членство сам;
цією міграцією доганяємо вже створені групи.

Чіпаємо лише командирів БЕЗ групи — свідомо введене членство не переписуємо.

Revision ID: 030
Revises: 029
Create Date: 2026-08-02
"""
from typing import Sequence, Union

from alembic import op

revision: str = "030"
down_revision: Union[str, None] = "029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE persons SET group_id = g.id FROM groups g "
        "WHERE g.commander_id = persons.id AND persons.group_id IS NULL"
    )


def downgrade() -> None:
    # Членство не відрізнити від введеного вручну — відкат нічого не знімає.
    pass

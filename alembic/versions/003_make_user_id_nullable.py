"""Make bot_daily_reports.user_id nullable

Revision ID: 003_make_user_id_nullable
Revises: 002_add_chat_bindings_indexes
Create Date: 2026-03-09 10:17:32.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_make_user_id_nullable'
down_revision: Union[str, None] = '002_add_chat_bindings_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Изменяем foreign key на ON DELETE SET NULL и делаем column nullable
    op.drop_constraint('bot_daily_reports_user_id_fkey', 'bot_daily_reports', type_='foreignkey')
    op.alter_column('bot_daily_reports', 'user_id',
               existing_type=sa.BigInteger(),
               nullable=True)
    op.create_foreign_key(
        'bot_daily_reports_user_id_fkey',
        'bot_daily_reports',
        'bot_users',
        ['user_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Возвращаем NOT NULL и ON DELETE CASCADE
    op.drop_constraint('bot_daily_reports_user_id_fkey', 'bot_daily_reports', type_='foreignkey')
    op.alter_column('bot_daily_reports', 'user_id',
               existing_type=sa.BigInteger(),
               nullable=False)
    op.create_foreign_key(
        'bot_daily_reports_user_id_fkey',
        'bot_daily_reports',
        'bot_users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )

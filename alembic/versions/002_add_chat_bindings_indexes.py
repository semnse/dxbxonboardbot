"""add_chat_bindings_indexes

Revision ID: 002_add_chat_bindings_indexes
Revises: 001_bot_tables
Create Date: 2026-03-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_chat_bindings_indexes'
down_revision: Union[str, None] = '001_bot_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляет индексы для оптимизации запросов chat_bindings"""
    
    # Индекс для поиска по чату + топику (основной запрос в get_by_chat_and_thread)
    op.create_index(
        'idx_chat_bindings_chat_thread',
        'chat_bindings',
        ['chat_id', 'message_thread_id'],
        unique=False
    )
    
    # Покрывающий индекс для частых запросов (chat_id + is_active)
    op.create_index(
        'idx_chat_bindings_chat_active',
        'chat_bindings',
        ['chat_id', 'is_active'],
        unique=False
    )


def downgrade() -> None:
    """Откатывает индексы"""
    op.drop_index('idx_chat_bindings_chat_active', table_name='chat_bindings')
    op.drop_index('idx_chat_bindings_chat_thread', table_name='chat_bindings')

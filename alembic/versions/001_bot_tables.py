"""create bot tables - users, subscriptions, daily_reports

Revision ID: 001_bot_tables
Revises: 
Create Date: 2026-03-04 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_bot_tables'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Таблица users
    op.create_table(
        'bot_users',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tg_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bot_users_tg_id'), 'bot_users', ['tg_id'], unique=True)
    op.create_index(op.f('ix_bot_users_is_active'), 'bot_users', ['is_active'], unique=False)

    # Таблица subscriptions
    op.create_table(
        'bot_subscriptions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('bitrix_item_id', sa.String(length=100), nullable=False),
        sa.Column('bitrix_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['bot_users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bot_subscriptions_user_id'), 'bot_subscriptions', ['user_id'], unique=False)
    op.create_index(op.f('ix_bot_subscriptions_bitrix_item_id'), 'bot_subscriptions', ['bitrix_item_id'], unique=False)

    # Таблица daily_reports
    op.create_table(
        'bot_daily_reports',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, default='success'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('items_count', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['bot_users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bot_daily_reports_user_id'), 'bot_daily_reports', ['user_id'], unique=False)
    op.create_index(op.f('ix_bot_daily_reports_sent_at'), 'bot_daily_reports', ['sent_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_bot_daily_reports_sent_at'), table_name='bot_daily_reports')
    op.drop_index(op.f('ix_bot_daily_reports_user_id'), table_name='bot_daily_reports')
    op.drop_table('bot_daily_reports')

    op.drop_index(op.f('ix_bot_subscriptions_bitrix_item_id'), table_name='bot_subscriptions')
    op.drop_index(op.f('ix_bot_subscriptions_user_id'), table_name='bot_subscriptions')
    op.drop_table('bot_subscriptions')

    op.drop_index(op.f('ix_bot_users_is_active'), table_name='bot_users')
    op.drop_index(op.f('ix_bot_users_tg_id'), table_name='bot_users')
    op.drop_table('bot_users')

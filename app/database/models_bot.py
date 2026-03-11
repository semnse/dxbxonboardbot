"""
Модели базы данных для Telegram бота и Celery задач

Новые модели для поддержки:
- Привязка пользователей Telegram к карточкам Bitrix24
- Ежедневная рассылка отчётов
- Кэширование статусов в Redis
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, String, Boolean, ForeignKey, DateTime, func, Text, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class User(Base):
    """Пользователь Telegram бота."""

    __tablename__ = "bot_users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Связи
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    reports: Mapped[list["DailyReport"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(tg_id={self.tg_id}, username={self.username})>"


class Subscription(Base):
    """Подписка пользователя на карточку Bitrix24."""

    __tablename__ = "bot_subscriptions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("bot_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bitrix_item_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    bitrix_fields: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Связи
    user: Mapped["User"] = relationship(back_populates="subscriptions")

    def __repr__(self) -> str:
        return f"<Subscription(user_id={self.user_id}, bitrix_item_id={self.bitrix_item_id})>"


class DailyReport(Base):
    """Лог отправки ежедневного отчёта пользователю."""

    __tablename__ = "bot_daily_reports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("bot_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sent_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    status: Mapped[str] = mapped_column(String(50), default="success")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    items_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Связи
    user: Mapped[Optional["User"]] = relationship(back_populates="reports")

    def __repr__(self) -> str:
        return f"<DailyReport(user_id={self.user_id}, status={self.status})>"

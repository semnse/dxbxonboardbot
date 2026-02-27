"""
SQLAlchemy модели базы данных
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    BigInteger,
    Text,
    ForeignKey,
    DateTime,
    UniqueConstraint,
    Index,
    JSON,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.database.connection import Base


# ============================================
# КЛИЕНТЫ (Торговые точки)
# ============================================
class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bitrix_deal_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    telegram_chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    telegram_chat_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    products = relationship("ClientProduct", back_populates="client", cascade="all, delete-orphan")
    deal_state = relationship("DealState", back_populates="client", uselist=False, cascade="all, delete-orphan")
    message_logs = relationship("MessageLog", back_populates="client", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_clients_bitrix_deal_id", "bitrix_deal_id"),
        Index("idx_clients_telegram_chat_id", "telegram_chat_id", postgresql_where=telegram_chat_id.isnot(None)),
    )

    def __repr__(self):
        return f"<Client(id={self.id}, name='{self.company_name}')>"


# ============================================
# ПРОДУКТЫ (Купленные модули)
# ============================================
class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    features = relationship("ProductFeature", back_populates="product")
    clients = relationship("ClientProduct", back_populates="product")

    def __repr__(self):
        return f"<Product(code='{self.code}', name='{self.name}')>"


# ============================================
# ФУНКЦИИ ПРОДУКТОВ
# ============================================
class ProductFeature(Base):
    __tablename__ = "product_features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_code: Mapped[str] = mapped_column(String(50), ForeignKey("products.code"), nullable=False)
    feature_text: Mapped[str] = mapped_column(String(255), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    product = relationship("Product", back_populates="features")

    __table_args__ = (
        UniqueConstraint("product_code", "feature_text"),
    )

    def __repr__(self):
        return f"<ProductFeature(product='{self.product_code}', feature='{self.feature_text}')>"


# ============================================
# СВЯЗЬ КЛИЕНТ-ПРОДУКТЫ
# ============================================
class ClientProduct(Base):
    __tablename__ = "client_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    product_code: Mapped[str] = mapped_column(String(50), ForeignKey("products.code"), nullable=False)
    purchased_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    client = relationship("Client", back_populates="products")
    product = relationship("Product", back_populates="clients")

    __table_args__ = (
        UniqueConstraint("client_id", "product_code"),
        Index("idx_client_products_client_id", "client_id"),
    )

    def __repr__(self):
        return f"<ClientProduct(client_id={self.client_id}, product='{self.product_code}')>"


# ============================================
# ПРИЧИНЫ ОЖИДАНИЯ
# ============================================
class WaitReason(Base):
    __tablename__ = "wait_reasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    bitrix_field_value: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    product_code: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("products.code"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    product = relationship("Product")
    risk_messages = relationship("RiskMessage", back_populates="reason", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_wait_reasons_code", "code"),
    )

    def __repr__(self):
        return f"<WaitReason(code='{self.code}', name='{self.name}')>"


# ============================================
# РИСКИ (Маппинг Причина → Риск)
# ============================================
class RiskMessage(Base):
    __tablename__ = "risk_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reason_code: Mapped[str] = mapped_column(String(50), ForeignKey("wait_reasons.code"), nullable=False)
    risk_text: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    reason = relationship("WaitReason", back_populates="risk_messages")

    __table_args__ = (
        UniqueConstraint("reason_code", "risk_text"),
        Index("idx_risk_messages_reason_code", "reason_code"),
    )

    def __repr__(self):
        return f"<RiskMessage(reason='{self.reason_code}', risk='{self.risk_text[:30]}...')>"


# ============================================
# СТАДИИ СДЕЛОК
# ============================================
class DealStage(Base):
    __tablename__ = "deal_stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bitrix_stage_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    stage_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_wait_stage: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    deal_states = relationship("DealState", back_populates="current_stage")

    def __repr__(self):
        return f"<DealStage(id='{self.bitrix_stage_id}', name='{self.stage_name}')>"


# ============================================
# ТЕКУЩИЕ СОСТОЯНИЯ СДЕЛОК
# ============================================
class DealState(Base):
    __tablename__ = "deal_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    current_stage_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("deal_stages.id"), nullable=True)
    wait_reasons: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    entered_wait_stage_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_message_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    messages_sent_count: Mapped[int] = mapped_column(Integer, default=0)
    is_bot_active: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    client = relationship("Client", back_populates="deal_state")
    current_stage = relationship("DealStage", back_populates="deal_states")

    __table_args__ = (
        UniqueConstraint("client_id"),
        Index("idx_deal_states_stage_id", "current_stage_id"),
        Index("idx_deal_states_bot_active", "is_bot_active", postgresql_where=is_bot_active == True),
    )

    def __repr__(self):
        return f"<DealState(client_id={self.client_id}, active={self.is_bot_active})>"


# ============================================
# ЛОГИ СООБЩЕНИЙ
# ============================================
class MessageLog(Base):
    __tablename__ = "message_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    telegram_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    send_status: Mapped[str] = mapped_column(String(20), default="SENT")
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    client = relationship("Client", back_populates="message_logs")

    __table_args__ = (
        Index("idx_message_logs_client_id", "client_id"),
        Index("idx_message_logs_sent_at", "sent_at"),
    )

    def __repr__(self):
        return f"<MessageLog(client_id={self.client_id}, type='{self.message_type}', status='{self.send_status}')>"


# ============================================
# НАСТРОЙКИ БОТА
# ============================================
class BotSetting(Base):
    __tablename__ = "bot_settings"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<BotSetting(key='{self.key}', value='{self.value}')>"


# ============================================
# ПРИВЯЗКИ ЧАТОВ К КАРТОЧКАМ BITRIX
# ============================================
class ChatBinding(Base):
    """
    Привязка Telegram чатов к карточкам Bitrix24.
    
    Используется для отправки отчётов в групповые чаты.
    """
    __tablename__ = "chat_bindings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    chat_title: Mapped[str] = mapped_column(String(255), nullable=True)
    bitrix_deal_id: Mapped[str] = mapped_column(String(50), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    __table_args__ = (
        Index("idx_chat_bindings_chat_id", "chat_id"),
        Index("idx_chat_bindings_bitrix_deal_id", "bitrix_deal_id"),
    )
    
    def __repr__(self):
        return f"<ChatBinding(chat_id={self.chat_id}, bitrix={self.bitrix_deal_id})>"

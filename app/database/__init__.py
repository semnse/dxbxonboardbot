"""
Модуль работы с базой данных
"""
from app.database.connection import (
    init_db,
    close_db,
    get_db,
    get_db_session,
    get_engine,
    AsyncSessionLocal,
    Base,
)
from app.database.models import (
    Client,
    Product,
    ProductFeature,
    ClientProduct,
    WaitReason,
    RiskMessage,
    DealStage,
    DealState,
    MessageLog,
    BotSetting,
    ChatBinding,
)
from app.database.repository import (
    BaseRepository,
    ClientRepository,
    ProductRepository,
    DealStateRepository,
    MessageLogRepository,
    WaitReasonRepository,
    ChatBindingRepository,
)

__all__ = [
    # Connection
    "init_db",
    "close_db",
    "get_db",
    "get_db_session",
    "get_engine",
    "AsyncSessionLocal",
    "Base",
    # Models
    "Client",
    "Product",
    "ProductFeature",
    "ClientProduct",
    "WaitReason",
    "RiskMessage",
    "DealStage",
    "DealState",
    "MessageLog",
    "BotSetting",
    "ChatBinding",
    # Repositories
    "BaseRepository",
    "ClientRepository",
    "ProductRepository",
    "DealStateRepository",
    "MessageLogRepository",
    "WaitReasonRepository",
    "ChatBindingRepository",
]

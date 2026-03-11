"""
Репозитории для работы с базой данных
CRUD операции для основных сущностей
"""
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any, TypeVar, Generic

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import (
    Client,
    Product,
    ClientProduct,
    DealState,
    DealStage,
    MessageLog,
    WaitReason,
    RiskMessage,
    ProductFeature,
    ChatBinding,
)


T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Базовый репозиторий с общими методами"""
    
    def __init__(self, model: type[T], session: AsyncSession):
        self.model = model
        self.session = session
    
    async def get(self, id: int) -> Optional[T]:
        """Получить запись по ID"""
        result = await self.session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Получить все записи с пагинацией"""
        result = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result.scalars().all())
    
    async def create(self, **kwargs) -> T:
        """Создать запись"""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance
    
    async def update(self, id: int, **kwargs) -> Optional[T]:
        """Обновить запись"""
        await self.session.execute(
            update(self.model).where(self.model.id == id).values(**kwargs)
        )
        return await self.get(id)
    
    async def delete(self, id: int) -> bool:
        """Удалить запись"""
        await self.session.execute(delete(self.model).where(self.model.id == id))
        return True


class ClientRepository(BaseRepository[Client]):
    """Репозиторий для работы с клиентами"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Client, session)
    
    async def get_by_bitrix_id(self, bitrix_deal_id: str) -> Optional[Client]:
        """Получить клиента по ID сделки в Bitrix"""
        result = await self.session.execute(
            select(Client)
            .options(selectinload(Client.products), selectinload(Client.deal_state))
            .where(Client.bitrix_deal_id == bitrix_deal_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_telegram_chat_id(self, telegram_chat_id: int) -> Optional[Client]:
        """Получить клиента по ID чата Telegram"""
        result = await self.session.execute(
            select(Client).where(Client.telegram_chat_id == telegram_chat_id)
        )
        return result.scalar_one_or_none()
    
    async def get_active_clients_with_bot(self) -> List[Client]:
        """Получить всех активных клиентов с включённым ботом"""
        result = await self.session.execute(
            select(Client)
            .join(Client.deal_state)
            .where(
                Client.is_active == True,
                DealState.is_bot_active == True
            )
            .options(selectinload(Client.deal_state), selectinload(Client.products))
        )
        return list(result.scalars().all())
    
    async def create_with_products(
        self,
        bitrix_deal_id: str,
        company_name: str,
        telegram_chat_id: Optional[int] = None,
        product_codes: Optional[List[str]] = None,
    ) -> Client:
        """Создать клиента с продуктами"""
        client = Client(
            bitrix_deal_id=bitrix_deal_id,
            company_name=company_name,
            telegram_chat_id=telegram_chat_id,
        )
        self.session.add(client)
        await self.session.flush()
        
        if product_codes:
            for code in product_codes:
                client_product = ClientProduct(client_id=client.id, product_code=code)
                self.session.add(client_product)
        
        return client


class ProductRepository(BaseRepository[Product]):
    """Репозиторий для работы с продуктами"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Product, session)
    
    async def get_by_code(self, code: str) -> Optional[Product]:
        """Получить продукт по коду"""
        result = await self.session.execute(
            select(Product).where(Product.code == code)
        )
        return result.scalar_one_or_none()
    
    async def get_active_with_features(self) -> List[Product]:
        """Получить все активные продукты с функциями"""
        result = await self.session.execute(
            select(Product)
            .options(selectinload(Product.features))
            .where(Product.is_active == True)
        )
        return list(result.scalars().all())
    
    async def get_client_features(self, client_id: int) -> List[str]:
        """Получить список функций для клиента"""
        result = await self.session.execute(
            select(ProductFeature.feature_text)
            .join(ClientProduct, ClientProduct.product_code == ProductFeature.product_code)
            .where(
                ClientProduct.client_id == client_id,
                ClientProduct.is_active == True,
                ProductFeature.is_active == True
            )
            .order_by(ProductFeature.display_order)
        )
        return list(result.scalars().all())


class DealStateRepository(BaseRepository[DealState]):
    """Репозиторий для работы с состояниями сделок"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(DealState, session)
    
    async def get_by_client_id(self, client_id: int) -> Optional[DealState]:
        """Получить состояние сделки клиента"""
        result = await self.session.execute(
            select(DealState)
            .options(selectinload(DealState.current_stage))
            .where(DealState.client_id == client_id)
        )
        return result.scalar_one_or_none()
    
    async def get_active_bot_states(self) -> List[DealState]:
        """Получить все активные состояния с включённым ботом"""
        result = await self.session.execute(
            select(DealState)
            .where(
                DealState.is_bot_active == True,
                DealState.current_stage_id.isnot(None)
            )
            .options(selectinload(DealState.client), selectinload(DealState.current_stage))
        )
        return list(result.scalars().all())
    
    async def activate_bot(
        self,
        client_id: int,
        stage_id: int,
        wait_reasons: List[str],
    ) -> DealState:
        """Активировать бота для клиента"""
        deal_state = await self.get_by_client_id(client_id)
        
        if deal_state:
            # Обновление существующего
            deal_state.is_bot_active = True
            deal_state.current_stage_id = stage_id
            deal_state.wait_reasons = wait_reasons
            deal_state.entered_wait_stage_at = datetime.utcnow()
            deal_state.messages_sent_count = 0
        else:
            # Создание нового
            deal_state = DealState(
                client_id=client_id,
                current_stage_id=stage_id,
                wait_reasons=wait_reasons,
                entered_wait_stage_at=datetime.utcnow(),
                is_bot_active=True,
                messages_sent_count=0,
            )
            self.session.add(deal_state)
        
        await self.session.flush()
        return deal_state
    
    async def deactivate_bot(self, client_id: int) -> bool:
        """Деактивировать бота для клиента"""
        deal_state = await self.get_by_client_id(client_id)
        if deal_state:
            deal_state.is_bot_active = False
            await self.session.flush()
        return True
    
    async def increment_message_count(self, client_id: int) -> None:
        """Увеличить счётчик отправленных сообщений"""
        await self.session.execute(
            update(DealState)
            .where(DealState.client_id == client_id)
            .values(
                messages_sent_count=DealState.messages_sent_count + 1,
                last_message_sent_at=datetime.utcnow(),
            )
        )
    
    async def update_last_message_time(self, client_id: int) -> None:
        """Обновить время последнего сообщения"""
        await self.session.execute(
            update(DealState)
            .where(DealState.client_id == client_id)
            .values(last_message_sent_at=datetime.utcnow())
        )


class MessageLogRepository(BaseRepository[MessageLog]):
    """Репозиторий для логирования сообщений"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(MessageLog, session)
    
    async def log_sent(
        self,
        client_id: int,
        message_type: str,
        message_text: str,
        telegram_message_id: Optional[int] = None,
    ) -> MessageLog:
        """Записать факт отправки сообщения"""
        log = MessageLog(
            client_id=client_id,
            message_type=message_type,
            message_text=message_text,
            telegram_message_id=telegram_message_id,
            send_status="SENT",
        )
        self.session.add(log)
        await self.session.flush()
        return log
    
    async def log_failed(
        self,
        client_id: int,
        message_type: str,
        message_text: str,
        error_message: str,
    ) -> MessageLog:
        """Записать факт неудачной отправки"""
        log = MessageLog(
            client_id=client_id,
            message_type=message_type,
            message_text=message_text,
            send_status="FAILED",
            error_message=error_message,
        )
        self.session.add(log)
        await self.session.flush()
        return log
    
    async def get_client_logs(
        self,
        client_id: int,
        limit: int = 50,
    ) -> List[MessageLog]:
        """Получить логи сообщений клиента"""
        result = await self.session.execute(
            select(MessageLog)
            .where(MessageLog.client_id == client_id)
            .order_by(MessageLog.sent_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class WaitReasonRepository(BaseRepository[WaitReason]):
    """Репозиторий для причин ожидания"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(WaitReason, session)
    
    async def get_by_code(self, code: str) -> Optional[WaitReason]:
        """Получить причину по коду"""
        result = await self.session.execute(
            select(WaitReason).where(WaitReason.code == code)
        )
        return result.scalar_one_or_none()
    
    async def get_active_with_risks(self) -> List[WaitReason]:
        """Получить все активные причины с рисками"""
        result = await self.session.execute(
            select(WaitReason)
            .options(selectinload(WaitReason.risk_messages))
            .where(WaitReason.is_active == True)
        )
        return list(result.scalars().all())
    
    async def get_risk_text(self, reason_code: str) -> Optional[str]:
        """Получить текст риска для причины"""
        result = await self.session.execute(
            select(RiskMessage.risk_text)
            .where(
                RiskMessage.reason_code == reason_code,
                RiskMessage.is_active == True
            )
            .order_by(RiskMessage.display_order)
            .limit(1)
        )
        return result.scalar_one_or_none()


# ============================================
# ПРИВЯЗКИ ЧАТОВ
# ============================================
class ChatBindingRepository(BaseRepository[ChatBinding]):
    """
    Репозиторий для привязок чатов к карточкам Bitrix.
    
    Полностью асинхронная версия на SQLAlchemy 2.0.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(ChatBinding, session)

    async def get_by_chat_and_thread(
        self,
        chat_id: int,
        message_thread_id: Optional[int] = None
    ) -> List[ChatBinding]:
        """
        Получить привязки по чату и топику.

        Args:
            chat_id: ID чата Telegram
            message_thread_id: ID топика (None для обычных чатов или всех топиков)

        Returns:
            Список привязок (обычно 0 или 1 элемент)
        """
        if message_thread_id is not None:
            # Для Topics чатов — ищем конкретный топик
            result = await self.session.execute(
                select(ChatBinding).where(
                    ChatBinding.chat_id == chat_id,
                    ChatBinding.message_thread_id == message_thread_id,
                    ChatBinding.is_active == True
                )
            )
        else:
            # Для обычных чатов или поиска по всем топикам — ищем все активные binding
            result = await self.session.execute(
                select(ChatBinding).where(
                    ChatBinding.chat_id == chat_id,
                    ChatBinding.is_active == True
                )
            )
        return list(result.scalars().all())

    async def get_by_chat_id_legacy(self, chat_id: int) -> Optional[ChatBinding]:
        """
        Получить первую привязку по ID чата (устаревший метод).
        
        Deprecated: Используйте get_by_chat_and_thread для поддержки Topics.
        """
        result = await self.session.execute(
            select(ChatBinding)
            .where(ChatBinding.chat_id == chat_id, ChatBinding.is_active == True)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_bitrix_deal_id(self, bitrix_deal_id: str) -> Optional[ChatBinding]:
        """
        Получить привязку по ID сделки Bitrix.
        
        Args:
            bitrix_deal_id: ID сделки в Bitrix24
            
        Returns:
            Привязка или None
        """
        result = await self.session.execute(
            select(ChatBinding)
            .where(
                ChatBinding.bitrix_deal_id == bitrix_deal_id,
                ChatBinding.is_active == True
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_active_bindings(self) -> List[ChatBinding]:
        """
        Получить все активные привязки.
        
        Returns:
            Список активных привязок
        """
        result = await self.session.execute(
            select(ChatBinding).where(ChatBinding.is_active == True)
        )
        return list(result.scalars().all())

    async def create(
        self,
        chat_id: int,
        bitrix_deal_id: str,
        company_name: str,
        chat_title: Optional[str] = None,
        message_thread_id: Optional[int] = None
    ) -> ChatBinding:
        """
        Создать привязку с upsert логикой.
        
        Args:
            chat_id: ID чата Telegram
            bitrix_deal_id: ID сделки Bitrix
            company_name: Название компании
            chat_title: Заголовок чата
            message_thread_id: ID топика (для Topics)
            
        Returns:
            Созданная или обновлённая привязка
        """
        from sqlalchemy.dialects.postgresql import insert
        
        stmt = insert(ChatBinding).values(
            chat_id=chat_id,
            message_thread_id=message_thread_id,
            chat_title=chat_title,
            bitrix_deal_id=bitrix_deal_id,
            company_name=company_name,
            is_active=True
        )
        
        # UPSERT: ON CONFLICT DO UPDATE
        if message_thread_id is not None:
            # Для Topics: уникальный ключ (chat_id, message_thread_id, bitrix_deal_id)
            stmt = stmt.on_conflict_do_update(
                index_elements=["chat_id", "message_thread_id", "bitrix_deal_id"],
                set_=dict(
                    company_name=company_name,
                    chat_title=chat_title,
                    updated_at=datetime.utcnow()
                )
            )
        else:
            # Для обычных чатов: уникальный ключ (chat_id, bitrix_deal_id)
            stmt = stmt.on_conflict_do_update(
                index_elements=["chat_id", "bitrix_deal_id"],
                set_=dict(
                    company_name=company_name,
                    chat_title=chat_title,
                    updated_at=datetime.utcnow()
                )
            )

        result = await self.session.execute(stmt.returning(ChatBinding))
        await self.session.commit()
        return result.scalar_one()

    async def update(
        self,
        id: int,
        bitrix_deal_id: Optional[str] = None,
        company_name: Optional[str] = None,
        chat_title: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[ChatBinding]:
        """
        Обновить привязку.
        
        Args:
            id: ID привязки
            bitrix_deal_id: Новый ID сделки Bitrix
            company_name: Новое название компании
            chat_title: Новый заголовок чата
            is_active: Статус активности
            
        Returns:
            Обновлённая привязка или None
        """
        update_data = {
            "updated_at": datetime.utcnow()
        }
        if bitrix_deal_id is not None:
            update_data["bitrix_deal_id"] = bitrix_deal_id
        if company_name is not None:
            update_data["company_name"] = company_name
        if chat_title is not None:
            update_data["chat_title"] = chat_title
        if is_active is not None:
            update_data["is_active"] = is_active
        
        stmt = (
            update(ChatBinding)
            .where(ChatBinding.id == id)
            .values(**update_data)
            .returning(ChatBinding)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def deactivate(self, id: int) -> bool:
        """
        Деактивировать привязку (soft delete).
        
        Args:
            id: ID привязки
            
        Returns:
            True если успешно
        """
        await self.session.execute(
            update(ChatBinding)
            .where(ChatBinding.id == id)
            .values(is_active=False, updated_at=datetime.utcnow())
        )
        return True

    async def delete_hard(self, id: int) -> bool:
        """
        Полностью удалить привязку (hard delete).
        
        Args:
            id: ID привязки
            
        Returns:
            True если успешно
        """
        await self.session.execute(
            delete(ChatBinding).where(ChatBinding.id == id)
        )
        return True

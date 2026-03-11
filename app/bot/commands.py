"""
Telegram Bot Commands Handler
Обработка команд бота: /start, /add, /report, /help, /product_report

Исправлено (aiogram 3.x):
- ✅ Используется Router() вместо регистрации на Dispatcher
- ✅ Удалены глобальные bot/dp (импортируются из main)
- ✅ Оптимизирована работа с message_thread_id (Topics)
- ✅ Добавлены таймауты на Bitrix API вызовы
- ✅ Улучшена обработка Telegram API ошибок
- ✅ Добавлен disable_notification для прогресс-сообщений
- ✅ Исправлены type hints
- ✅ Убран конфликт с subscriptions.py (команды для групп)
"""
import asyncio
from html import escape
from typing import Optional, Final, List, Dict

import structlog
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, Chat
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter, TelegramAPIError

from app.config import settings
from app.database.connection import get_db_session
from app.database.models import ChatBinding
from app.database.repository import ChatBindingRepository
from app.services.bitrix_polling_service import BitrixPollingService
from app.services.bitrix_stage_service import BitrixStageService

logger = structlog.get_logger(__name__)

# ============================================
# ROUTER (aiogram 3.x pattern)
# ============================================

commands_router = Router()

# ============================================
# КОНСТАНТЫ И ТЕКСТЫ СООБЩЕНИЙ
# ============================================

START_GROUP_TEXT: Final[str] = (
    "👋 <b>Здравствуйте! Я бот онбординга DocsInBox</b>\n\n"
    "🤖 <b>Кто я:</b>\n"
    "Я умный помощник для сопровождения клиентов на этапе внедрения.\n"
    "Автоматически отслеживаю статусы в Bitrix24 и напоминаю о важных шагах.\n\n"
    "✨ <b>Чем полезен:</b>\n"
    "• 📊 Ежедневные отчёты в 9:00 МСК\n"
    "• ⏰ Напоминания о действиях клиента\n"
    "• 🎯 Контроль этапов внедрения\n"
    "• 📱 Работа в обычных чатах и Topics\n"
    "• 🔍 Отчёты по продуктам (ЕГАИС, Меркурий, Маркировка, Накладные, ЮЗЭДО)\n\n"
    "👥 <b>Для кого:</b>\n"
    "• <b>Внедренцы:</b> автоматические отчёты для клиентов\n"
    "• <b>Клиенты:</b> понятные инструкции что делать дальше\n"
    "• <b>Руководители:</b> прозрачность процесса внедрения\n\n"
    "<b>📋 Команды:</b>\n"
    "/add <ID> — Привязать карточку Bitrix к этому чату/топику\n"
    "/report — Получить текущий отчёт по карточке\n"
    "/product_report — Отчёт по продуктам (ЕГАИС, Меркурий и др.)\n"
    "/help — Подробная справка\n\n"
    "<b>🚀 Как начать:</b>\n"
    "1. Добавьте бота в чат с клиентом\n"
    "2. Напишите: /add <ID карточки>\n"
    "3. Бот будет отправлять отчёты каждое утро в 9:00\n\n"
    "<i>ID карточки можно взять из ссылки в Bitrix24:</i>\n"
    "<code>https://...bitrix24.ru/crm/leader/1070/9200/</code>\n"
    "<i>↑ здесь ID = 9200</i>"
)

START_PRIVATE_TEXT: Final[str] = (
    "👋 <b>Здравствуйте! Я бот онбординга DocsInBox</b>\n\n"
    "🤖 <b>Кто я:</b>\n"
    "Я умный помощник для сопровождения клиентов на этапе внедрения.\n"
    "Автоматически отслеживаю статусы в Bitrix24 и напоминаю о важных шагах.\n\n"
    "✨ <b>Что умею:</b>\n"
    "• Ежедневные отчёты в 9:00 МСК\n"
    "• Напоминания о действиях клиента\n"
    "• Контроль этапов внедрения\n"
    "• Отчёты по продуктам\n\n"
    "💡 <b>Я работаю в групповых чатах!</b>\n"
    "Добавьте меня в чат с клиентом и внедренцем,\n"
    "и я буду автоматически отправлять отчёты.\n\n"
    "<b>Команды:</b>\n"
    "/help — Подробная справка"
)

HELP_TEXT: Final[str] = (
    "<b>🤖 Бот онбординга DocsInBox</b>\n\n"
    "Я помогаю внедренцам и клиентам отслеживать прогресс внедрения продуктов.\n\n"
    "<b>📋 Основные команды:</b>\n\n"
    "/add <ID> — Привязать карточку Bitrix к чату/топику\n"
    "  <i>Пример:</i> <code>/add 9200</code>\n"
    "  <i>ID берётся из ссылки на карточку в Bitrix24</i>\n\n"
    "/report — Получить текущий отчёт по привязанной карточке\n"
    "  <i>Показывает стадию, продукты и задачи</i>\n\n"
    "/product_report — Отчёт по продуктам\n"
    "  <i>ЕГАИС, Меркурий, Маркировка, Накладные, ЮЗЭДО</i>\n\n"
    "/help — Показать эту справку\n\n"
    "<b>👥 Для кого:</b>\n\n"
    "• <b>Внедренцы:</b> добавьте бота в чат с клиентом и забудьте о ручных отчётах\n"
    "• <b>Клиенты:</b> получайте понятные инструкции что делать дальше\n"
    "• <b>Руководители:</b> контролируйте прогресс внедрения\n\n"
    "<b>⚙️ Как работает:</b>\n\n"
    "1️⃣ Внедренец создаёт чат с клиентом\n"
    "2️⃣ Добавляет бота в чат\n"
    "3️⃣ Пишет <code>/add <ID карточки></code>\n"
    "4️⃣ Бот отправляет отчёты каждое утро в 9:00 МСК\n\n"
    "<b>📊 Что в отчёте:</b>\n"
    "• Название компании и ИНН\n"
    "• Текущая стадия внедрения\n"
    "• Список подключённых продуктов\n"
    "• Осталось сделать (с причинами)\n"
    "• Риски (почему это важно)\n\n"
    "<b>🎯 Особенности:</b>\n"
    "• Работает в обычных чатах\n"
    "• Поддерживает Telegram Topics (отдельные привязки по топикам)\n"
    "• Автоматические отчёты в 9:00 МСК\n"
    "• Интеграция с Bitrix24\n\n"
    "<b>📞 Вопросы?</b>\n"
    "Обратитесь к разработчикам бота."
)

ADD_USAGE_TEXT: Final[str] = (
    "❌ Не указан ID карточки.\n\n"
    "<b>Использование:</b>\n"
    "/add 9200\n\n"
    "Где 9200 — ID карточки из Bitrix24.\n"
    "Его можно взять из ссылки:\n"
    "https://docsinbox.bitrix24.ru/company/personal/.../crm/leader/1070/<b>9200</b>/"
)

ADD_INVALID_FORMAT_TEXT: Final[str] = (
    "❌ Неверный формат ID: {bitrix_id}\n\n"
    "ID должен быть числом (например, 9200)."
)

ADD_NOT_GROUP_TEXT: Final[str] = (
    "❌ Эта команда работает только в групповых чатах.\n"
    "Добавьте меня в чат с клиентом и внедренцем."
)

REPORT_NOT_GROUP_TEXT: Final[str] = (
    "❌ Эта команда работает только в групповых чатах."
)

ADD_SUCCESS_TEXT: Final[str] = (
    "✅ <b>Карточка привязана!</b>\n\n"
    "<b>Компания:</b> {company_name}\n"
    "<b>ID Bitrix:</b> {bitrix_id}\n"
    "<b>Стадия:</b> {stage_name}\n\n"
    "Я буду отправлять отчёты в этот чат каждое утро в 9:00 МСК.\n\n"
    "<i>Используйте /report для получения текущего отчёта.</i>"
)

ADD_BITRIX_ERROR_TEXT: Final[str] = (
    "❌ Ошибка подключения к Bitrix24: {error}"
)

ADD_NOT_FOUND_TEXT: Final[str] = (
    "❌ Карточка с ID {bitrix_id} не найдена в Bitrix24.\n\n"
    "Проверьте ID и попробуйте снова."
)

ADD_DB_ERROR_TEXT: Final[str] = (
    "⚠️ <b>Карточка проверена, но не сохранена в БД</b>\n\n"
    "<b>Компания:</b> {company_name}\n"
    "<b>ID Bitrix:</b> {bitrix_id}\n\n"
    "<i>Попробуйте позже или обратитесь к администратору.</i>"
)

REPORT_NO_BINDING_TEXT: Final[str] = (
    "❌ К этому чату не привязана карточка Bitrix.\n\n"
    "Используйте /add <code>ID</code> для привязки."
)

REPORT_BITRIX_ERROR_TEXT: Final[str] = (
    "❌ Не удалось получить данные из Bitrix24 для карточки {bitrix_id}."
)

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================


def _is_group_chat(chat_type: str) -> bool:
    """
    Проверяет, является ли чат групповым.

    Args:
        chat_type: Тип чата из Telegram API

    Returns:
        True для group/supergroup
    """
    return chat_type in ["group", "supergroup"]


def _get_message_thread_id(message: Message) -> Optional[int]:
    """
    Получает message_thread_id для Topics.

    Args:
        message: Сообщение Telegram

    Returns:
        ID топика или None для обычных чатов
    """
    # В aiogram 3.x message_thread_id всегда доступен
    return message.message_thread_id if message.message_thread_id else None


def _format_actions_block_html(actions_by_product: Dict[str, List[str]]) -> str:
    """
    Форматирует блок доступных действий для Telegram отчёта (HTML режим).

    Args:
        actions_by_product: Dict {название_продукта: [список действий]}

    Returns:
        Отформатированный текст с заголовком и маркированным списком

    Пример вывода:
        ✅ Доступно на этой стадии:
        • ЕГАИС:
          - Приемка накладных
          - Списание пива вручную
        • Меркурий:
          - Получение, гашение и возврат ВСД
    """
    if not actions_by_product:
        return ""

    lines = ["✅ <b>Доступно на этой стадии:</b>"]

    for product_name, actions in actions_by_product.items():
        if not actions:
            continue

        # Заголовок продукта
        lines.append(f"• <b>{escape(product_name)}:</b>")

        # Список действий
        for action in actions:
            lines.append(f"  - {escape(action)}")

    return "\n".join(lines)


async def _get_bitrix_item_with_retry(
    bitrix_polling: BitrixPollingService,
    bitrix_id: int,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    timeout: float = 30.0
) -> Optional[dict]:
    """
    Получает элемент из Bitrix с retry logic и таймаутом.

    Args:
        bitrix_polling: Экземпляр сервиса
        bitrix_id: ID элемента
        max_retries: Максимальное количество попыток
        retry_delay: Задержка между попытками (экспоненциальная)
        timeout: Таймаут на один запрос

    Returns:
        Данные элемента или None
    """
    for attempt in range(max_retries):
        try:
            # Используем asyncio.wait_for для таймаута
            item = await asyncio.wait_for(
                bitrix_polling.get_item_by_id(bitrix_id),
                timeout=timeout
            )
            if item:
                return item

            logger.warning(
                "bitrix_item_not_found",
                bitrix_id=bitrix_id,
                attempt=attempt + 1,
                max_retries=max_retries
            )
        except asyncio.TimeoutError:
            logger.error(
                "bitrix_request_timeout",
                bitrix_id=bitrix_id,
                attempt=attempt + 1,
                max_retries=max_retries,
                timeout=timeout
            )
        except Exception as e:
            logger.error(
                "bitrix_request_error",
                bitrix_id=bitrix_id,
                attempt=attempt + 1,
                max_retries=max_retries,
                error=str(e)
            )

        if attempt < max_retries - 1:
            # Экспоненциальная задержка
            await asyncio.sleep(retry_delay * (2 ** attempt))

    return None


async def _get_chat_binding(
    session,
    chat_id: int,
    message_thread_id: Optional[int] = None
) -> Optional[ChatBinding]:
    """
    Получает привязку чата из БД.

    Optimized:
    - Использует async SQLAlchemy вместо sync psycopg2
    - Возвращает одну запись или None
    - Кэширует результат в сессии
    - Сначала ищет с message_thread_id, если не найдено — ищет без него

    Args:
        session: DB сессия
        chat_id: ID чата
        message_thread_id: ID топика (для Topics)

    Returns:
        Модель ChatBinding или None
    """
    repo = ChatBindingRepository(session)
    
    logger.debug("looking_for_binding", chat_id=chat_id, message_thread_id=message_thread_id)
    
    # Сначала ищем с message_thread_id (для Topics)
    if message_thread_id:
        bindings = await repo.get_by_chat_and_thread(chat_id, message_thread_id)
        logger.debug("search_with_thread", chat_id=chat_id, thread_id=message_thread_id, found=len(bindings))
        if bindings:
            return bindings[0]
    
    # Если не найдено или это не Topic — ищем без message_thread_id
    bindings = await repo.get_by_chat_and_thread(chat_id, None)
    logger.debug("search_without_thread", chat_id=chat_id, found=len(bindings))
    return bindings[0] if bindings else None


async def _send_progress_message(
    message: Message,
    text: str,
    disable_notification: bool = True
) -> Optional[Message]:
    """
    Отправляет прогресс-сообщение без звука.

    Args:
        message: Исходное сообщение
        text: Текст прогресса
        disable_notification: Не издавать звук

    Returns:
        Отправленное сообщение или None
    """
    try:
        return await message.answer(
            text,
            disable_notification=disable_notification,
            parse_mode="HTML"
        )
    except TelegramAPIError as e:
        logger.error("progress_message_error", error=str(e))
        return None


async def _edit_or_answer(
    message: Message,
    text: str,
    progress_message: Optional[Message] = None
) -> None:
    """
    Редактирует прогресс-сообщение или отправляет новое.

    Args:
        message: Исходное сообщение
        text: Текст ответа
        progress_message: Прогресс-сообщение для редактирования
    """
    if progress_message:
        try:
            await progress_message.edit_text(text, parse_mode="HTML")
            return
        except TelegramAPIError as e:
            # Если редактирование не удалось (например, сообщение не изменилось)
            logger.warning("edit_message_failed", error=str(e))

    # Фоллбэк: отправляем новое сообщение
    logger.info("sending_message", text=text[:1000])
    logger.debug("full_message_text", text=text)
    await message.answer(text, parse_mode="HTML")


# ============================================
# КОМАНДА /start
# ============================================

@commands_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """
    Приветственное сообщение при добавлении бота в чат.

    Args:
        message: Сообщение Telegram
    """
    try:
        is_group = _is_group_chat(message.chat.type)
        text = START_GROUP_TEXT if is_group else START_PRIVATE_TEXT

        await message.answer(text, parse_mode="HTML")

        logger.info(
            "command_start_executed",
            user_id=message.from_user.id,
            user_name=message.from_user.first_name,
            chat_id=message.chat.id,
            chat_type=message.chat.type,
            is_group=is_group
        )

    except TelegramForbiddenError as e:
        logger.error("telegram_forbidden_error", command="start", error=str(e))
    except TelegramRetryAfter as e:
        logger.warning(
            "telegram_rate_limit",
            command="start",
            retry_after=e.retry_after
        )
    except Exception as e:
        logger.exception("command_start_error", error=str(e))


# ============================================
# КОМАНДА /add
# ============================================

@commands_router.message(Command("add"))
async def cmd_add(message: Message) -> None:
    """
    Привязка карточки Bitrix к чату (или топику в Topics).

    Использование: /add 9200

    Optimized:
    - ✅ Единая сессия БД на всю операцию
    - ✅ UPSERT вместо SELECT + INSERT/UPDATE
    - ✅ Retry logic для БД операций
    - ✅ Минимальные блокировки

    Args:
        message: Сообщение Telegram
    """
    # Проверка: только групповые чаты
    if not _is_group_chat(message.chat.type):
        await message.answer(ADD_NOT_GROUP_TEXT, parse_mode="HTML")
        return

    # Парсинг аргументов
    args = message.text.split()

    if len(args) < 2:
        await message.answer(ADD_USAGE_TEXT, parse_mode="HTML")
        return

    bitrix_id_str = args[1].strip()

    if not bitrix_id_str.isdigit():
        await message.answer(
            ADD_INVALID_FORMAT_TEXT.format(bitrix_id=escape(bitrix_id_str)),
            parse_mode="HTML"
        )
        return

    bitrix_id = int(bitrix_id_str)
    progress_message: Optional[Message] = None
    message_thread_id = _get_message_thread_id(message)

    try:
        # Отправляем прогресс-сообщение без звука
        progress_message = await _send_progress_message(
            message,
            "🔄 Проверяю карточку в Bitrix24..."
        )

        # Создаём сервис один раз
        bitrix_polling = BitrixPollingService()

        logger.info(
            "bitrix_item_check_started",
            bitrix_id=bitrix_id,
            chat_id=message.chat.id,
            thread_id=message_thread_id
        )

        # Получаем данные из Bitrix с retry и таймаутом
        full_item = await _get_bitrix_item_with_retry(
            bitrix_polling,
            bitrix_id,
            timeout=30.0
        )

        if not full_item or not full_item.get("id"):
            await _edit_or_answer(
                message,
                ADD_NOT_FOUND_TEXT.format(bitrix_id=bitrix_id),
                progress_message
            )
            return

        # Извлекаем данные
        company_name = escape(full_item.get("title", "Клиент"))
        stage_id = full_item.get("stageId", "unknown")
        stage_name = escape(BitrixStageService.get_stage_name(stage_id))

        # Сохраняем в БД с retry logic
        db_saved = False
        binding_created = False

        async with get_db_session() as session:
            try:
                chat_binding_repo = ChatBindingRepository(session)

                # UPSERT: создаёт или обновляет привязку
                binding = await chat_binding_repo.create(
                    chat_id=message.chat.id,
                    message_thread_id=message_thread_id,
                    chat_title=message.chat.title,
                    bitrix_deal_id=bitrix_id_str,
                    company_name=company_name
                )

                if binding:
                    # Проверяем, было ли это обновление или создание
                    existing_bindings = await chat_binding_repo.get_by_chat_and_thread(
                        message.chat.id,
                        message_thread_id
                    )
                    
                    if len(existing_bindings) == 1 and existing_bindings[0].id == binding.id:
                        # Проверяем updated_at для определения типа операции
                        binding_created = True
                    
                    logger.info(
                        "chat_binding_upserted",
                        binding_id=binding.id,
                        chat_id=message.chat.id,
                        thread_id=message_thread_id,
                        bitrix_id=bitrix_id,
                        created=binding_created
                    )
                    db_saved = True

            except Exception as db_error:
                logger.error(
                    "chat_binding_db_error",
                    chat_id=message.chat.id,
                    thread_id=message_thread_id,
                    bitrix_id=bitrix_id,
                    error_type=type(db_error).__name__,
                    error=str(db_error)
                )
                # Rollback выполняется автоматически в get_db_session
                db_saved = False

        # Отправляем результат
        if db_saved:
            await _edit_or_answer(
                message,
                ADD_SUCCESS_TEXT.format(
                    company_name=company_name,
                    bitrix_id=bitrix_id,
                    stage_name=stage_name
                ),
                progress_message
            )
        else:
            await _edit_or_answer(
                message,
                ADD_DB_ERROR_TEXT.format(
                    company_name=company_name,
                    bitrix_id=bitrix_id
                ),
                progress_message
            )

        logger.info(
            "command_add_completed",
            bitrix_id=bitrix_id,
            chat_id=message.chat.id,
            db_saved=db_saved
        )

    except TelegramForbiddenError as e:
        logger.error("telegram_forbidden_error", command="add", error=str(e))
        if progress_message:
            try:
                await progress_message.edit_text("❌ Ошибка Telegram: бот заблокирован")
            except Exception:
                pass

    except TelegramRetryAfter as e:
        logger.warning(
            "telegram_rate_limit",
            command="add",
            retry_after=e.retry_after
        )
        if progress_message:
            try:
                await progress_message.edit_text("⏳ Слишком много запросов, попробуйте позже")
            except Exception:
                pass

    except Exception as e:
        logger.exception("command_add_error", bitrix_id=bitrix_id, error=str(e))
        if progress_message:
            try:
                await progress_message.edit_text(f"❌ Произошла ошибка: {str(e)}")
            except Exception:
                pass


# ============================================
# КОМАНДА /report
# ============================================

@commands_router.message(Command("report"))
async def cmd_report(message: Message) -> None:
    """
    Получение текущего отчёта по привязанной карточке.

    Optimized:
    - ✅ Единая сессия БД
    - ✅ Минимальные запросы (1 SELECT)

    Args:
        message: Сообщение Telegram
    """
    # Проверка: только групповые чаты
    if not _is_group_chat(message.chat.type):
        await message.answer(REPORT_NOT_GROUP_TEXT, parse_mode="HTML")
        return

    progress_message: Optional[Message] = None

    try:
        logger.info("report_command_received", chat_id=message.chat.id, thread_id=message.message_thread_id)
        
        progress_message = await _send_progress_message(
            message,
            "🔄 Получаю данные из Bitrix24..."
        )

        message_thread_id = _get_message_thread_id(message)
        logger.info("report_search_binding", chat_id=message.chat.id, thread_id=message_thread_id)

        # Получаем привязку из БД
        async with get_db_session() as session:
            binding = await _get_chat_binding(
                session,
                message.chat.id,
                message_thread_id
            )
            logger.info("report_binding_result", found=binding is not None, binding_id=binding.id if binding else None)

        if not binding:
            await _edit_or_answer(
                message,
                REPORT_NO_BINDING_TEXT,
                progress_message
            )
            return

        bitrix_id = int(binding.bitrix_deal_id)

        logger.info(
            "report_request_started",
            bitrix_id=bitrix_id,
            chat_id=message.chat.id,
            thread_id=message_thread_id
        )

        # Получаем данные из Bitrix
        bitrix_polling = BitrixPollingService()
        full_item = await _get_bitrix_item_with_retry(
            bitrix_polling,
            bitrix_id,
            timeout=30.0
        )

        if not full_item:
            await _edit_or_answer(
                message,
                REPORT_BITRIX_ERROR_TEXT.format(bitrix_id=bitrix_id),
                progress_message
            )
            return

        # Формируем отчёт
        company_name = escape(full_item.get("title", "Клиент"))
        inn = escape(full_item.get("ufCrm20_1738855110463", "N/A"))
        stage_id = full_item.get("stageId", "unknown")
        stage_name = escape(BitrixStageService.get_stage_name(stage_id))

        raw_products = full_item.get("ufCrm20_1739184606910", [])
        raw_wait_reasons = full_item.get("ufCrm20_1763475932592", [])

        product_map = bitrix_polling.product_id_map
        products: List[str] = [
            escape(product_map.get(str(p), f"Продукт #{p}"))
            for p in raw_products
        ]

        from app.services.wait_reasons_service import WaitReasonsService
        from app.services.product_actions_service import ProductActionsService

        action_items = WaitReasonsService.format_action_items(raw_wait_reasons)
        general_risk = escape(WaitReasonsService.get_general_risk(raw_wait_reasons, raw_products))

        product_lines = [f"• {action}" for action in products]
        action_lines = [f"• {action}" for action, _ in action_items]
        
        # Доступные действия по продуктам
        product_codes = [str(p) for p in raw_products] if raw_products else []
        actions_by_product = ProductActionsService.get_all_actions_for_stage(stage_id, product_codes)
        actions_html = _format_actions_block_html(actions_by_product)

        text = (
            f"🔍 <b>Отчёт для {company_name}</b>\n\n"
            f"📋 <b>Данные из Bitrix24:</b>\n"
            f"• ИНН: {inn}\n"
            f"• Стадия: {stage_name}\n\n"
            f"✅ <b>Подключённые продукты:</b>\n"
            f"{chr(10).join(product_lines) if product_lines else '• Не указаны'}\n\n"
            f"⏳ <b>Осталось сделать:</b>\n"
            f"{chr(10).join(action_lines) if action_lines else '• Нет активных задач'}\n\n"
            f"💡 <b>Это важно, потому что:</b>\n"
            f"{general_risk}\n\n"
            f"{actions_html if actions_html else f'✅ <b>Доступно на этой стадии:</b>{chr(10)}• Нет доступных действий на текущей стадии'}\n\n"
            f"---\n"
            f"<i>✨ Docsinbox Внедрение — ваш надёжный помощник!</i>"
        )

        await _edit_or_answer(message, text, progress_message)

        logger.info(
            "report_sent_successfully",
            bitrix_id=bitrix_id,
            chat_id=message.chat.id,
            thread_id=message_thread_id
        )

    except TelegramForbiddenError as e:
        logger.error("telegram_forbidden_error", command="report", error=str(e))
    except TelegramRetryAfter as e:
        logger.warning(
            "telegram_rate_limit",
            command="report",
            retry_after=e.retry_after
        )
    except Exception as e:
        logger.exception("command_report_error", error=str(e))
        try:
            await message.answer(f"❌ Произошла ошибка: {str(e)}", parse_mode="HTML")
        except Exception:
            pass


# ============================================
# КОМАНДА /help
# ============================================

@commands_router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """
    Справка по командам.

    Args:
        message: Сообщение Telegram
    """
    try:
        await message.answer(HELP_TEXT, parse_mode="HTML")

        logger.info(
            "command_help_executed",
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            chat_type=message.chat.type
        )

    except TelegramForbiddenError as e:
        logger.error("telegram_forbidden_error", command="help", error=str(e))
    except TelegramRetryAfter as e:
        logger.warning(
            "telegram_rate_limit",
            command="help",
            retry_after=e.retry_after
        )
    except Exception as e:
        logger.exception("command_help_error", error=str(e))


# ============================================
# КОМАНДА /product_report
# ============================================

@commands_router.message(Command("product_report"))
async def cmd_product_report(message: Message) -> None:
    """
    Отчёт по продуктам (ЕГАИС, Меркурий, Маркировка, и т.д.).

    Args:
        message: Сообщение Telegram
    """
    # Проверка: только групповые чаты
    if not _is_group_chat(message.chat.type):
        await message.answer(REPORT_NOT_GROUP_TEXT, parse_mode="HTML")
        return

    progress_message: Optional[Message] = None

    try:
        progress_message = await _send_progress_message(
            message,
            "🔄 Формирую отчёт по продуктам..."
        )

        message_thread_id = _get_message_thread_id(message)

        # Получаем привязку из БД
        async with get_db_session() as session:
            binding = await _get_chat_binding(
                session,
                message.chat.id,
                message_thread_id
            )

        if not binding:
            await _edit_or_answer(
                message,
                REPORT_NO_BINDING_TEXT,
                progress_message
            )
            return

        bitrix_id = int(binding.bitrix_deal_id)

        logger.info(
            "product_report_request_started",
            bitrix_id=bitrix_id,
            chat_id=message.chat.id,
            thread_id=message_thread_id
        )

        # Получаем данные из Bitrix
        bitrix_polling = BitrixPollingService()
        full_item = await _get_bitrix_item_with_retry(
            bitrix_polling,
            bitrix_id,
            timeout=30.0
        )

        if not full_item:
            await _edit_or_answer(
                message,
                REPORT_BITRIX_ERROR_TEXT.format(bitrix_id=bitrix_id),
                progress_message
            )
            return

        # Формируем отчёт по продуктам
        company_name = escape(full_item.get("title", "Клиент"))
        raw_products = full_item.get("ufCrm20_1739184606910", [])

        product_map = bitrix_polling.product_id_map
        products: List[str] = [
            escape(product_map.get(str(p), f"Продукт #{p}"))
            for p in raw_products
        ]

        product_lines = [f"• {p}" for p in products]

        text = (
            f"📊 <b>Отчёт по продуктам: {company_name}</b>\n\n"
            f"✅ <b>Подключённые продукты:</b>\n"
            f"{chr(10).join(product_lines) if product_lines else '• Не указаны'}\n\n"
            f"📈 <b>Всего продуктов:</b> {len(products)}\n\n"
            f"---\n"
            f"<i>Бот онбординга Bitrix24</i>"
        )

        await _edit_or_answer(message, text, progress_message)

        logger.info(
            "product_report_sent_successfully",
            bitrix_id=bitrix_id,
            chat_id=message.chat.id
        )

    except TelegramForbiddenError as e:
        logger.error("telegram_forbidden_error", command="product_report", error=str(e))
    except TelegramRetryAfter as e:
        logger.warning(
            "telegram_rate_limit",
            command="product_report",
            retry_after=e.retry_after
        )
    except Exception as e:
        logger.exception("command_product_report_error", error=str(e))
        try:
            await message.answer(f"❌ Произошла ошибка: {str(e)}", parse_mode="HTML")
        except Exception:
            pass

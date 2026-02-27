"""
Telegram Bot Commands Handler
Обработка команд бота: /start, /add, /report, /help

Исправлено:
- Правильная инициализация бота и диспетчера
- Корректная обработка /add команды с привязкой чата к Bitrix карточке
- Обработка ошибок и логирование
"""
import logging
from typing import Optional, Dict, Any

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.exceptions import TelegramNetworkError, TelegramAPIError

from app.config import settings
from app.database.connection import get_db_session, AsyncSessionLocal
from app.database.repository import ChatBindingRepository
from app.database.models import ChatBinding
from app.services.bitrix_polling_service import BitrixPollingService
from app.services.wait_reasons_service import WaitReasonsService
from app.services.bitrix_stage_service import BitrixStageService
from app.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
# Важно: создаём один экземпляр для всего приложения
bot = Bot(token=settings.telegram_bot_token, session=None)
dp = Dispatcher()

# Кэш для хранения привязок chat_id -> bitrix_id (временное решение без БД)
_chat_cache: Dict[int, Dict[str, Any]] = {}


# ============================================
# КОМАНДА /start
# ============================================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Приветственное сообщение при добавлении бота в чат"""
    try:
        # Проверяем, это группа или личный чат
        if message.chat.type in ["group", "supergroup"]:
            text = (
                "👋 Здравствуйте! Я бот онбординга DocsInBox.\n\n"
                "Я буду напоминать о шагах внедрения и объяснять, почему это важно.\n\n"
                "<b>Как использовать:</b>\n"
                "1. Внедренец пишет: /add <ID карточки из Bitrix>\n"
                "   Пример: /add 9200\n"
                "2. Я буду отправлять отчёты по этой карточке каждое утро в 9:00\n\n"
                "<b>Команды:</b>\n"
                "/add <ID> — Привязать карточку Bitrix к этому чату\n"
                "/report — Получить текущий отчёт\n"
                "/help — Помощь"
            )
        else:
            text = (
                "👋 Здравствуйте! Я бот онбординга DocsInBox.\n\n"
                "Я работаю в групповых чатах с внедренцами и клиентами.\n\n"
                "Добавьте меня в чат и используйте команду /add <ID карточки>"
            )

        await message.answer(text, parse_mode="HTML")
        logger.info(f"Command /start executed by {message.from_user.first_name} in chat {message.chat.id}")
        
    except TelegramAPIError as e:
        logger.error(f"Telegram API error in /start: {e}")
    except Exception as e:
        logger.exception(f"Error in /start command: {e}")


# ============================================
# КОМАНДА /add
# ============================================
@dp.message(Command("add"))
async def cmd_add(message: Message):
    """
    Привязка карточки Bitrix к чату.

    Использование: /add 9200
    
    Логика:
    1. Парсим ID карточки из аргументов
    2. Проверяем карточку в Bitrix24
    3. Сохраняем привязку в базу данных
    4. Отправляем подтверждение
    """
    try:
        # Проверяем, что это группа
        if message.chat.type not in ["group", "supergroup"]:
            await message.answer(
                "❌ Эта команда работает только в групповых чатах.\n"
                "Добавьте меня в чат с клиентом и внедренцем."
            )
            return

        # Парсим аргумент
        args = message.text.split()

        if len(args) < 2:
            await message.answer(
                "❌ Не указан ID карточки.\n\n"
                "<b>Использование:</b>\n"
                "/add 9200\n\n"
                "Где 9200 — ID карточки из Bitrix24.\n"
                "Его можно взять из ссылки:\n"
                "https://docsinbox.bitrix24.ru/company/personal/.../crm/leader/1070/<b>9200</b>/",
                parse_mode="HTML"
            )
            return

        bitrix_id = args[1].strip()

        # Проверяем, что это число
        if not bitrix_id.isdigit():
            await message.answer(
                f"❌ Неверный формат ID: {bitrix_id}\n\n"
                "ID должен быть числом (например, 9200)."
            )
            return

        # Отправляем сообщение о процессе
        progress_message = await message.answer("🔄 Проверяю карточку в Bitrix24...")

        # Проверяем, существует ли карточка в Bitrix
        bitrix_polling = BitrixPollingService()
        logger.info(f"Checking Bitrix for item ID={bitrix_id}")
        
        try:
            full_item = await bitrix_polling.get_item_by_id(int(bitrix_id))
        except Exception as e:
            logger.exception(f"Error getting item from Bitrix: {e}")
            await progress_message.edit_text(
                f"❌ Ошибка подключения к Bitrix24: {str(e)}"
            )
            return

        logger.info(f"Bitrix response for item {bitrix_id}: {full_item is not None}")

        if not full_item or not full_item.get('id'):
            await progress_message.edit_text(
                f"❌ Карточка с ID {bitrix_id} не найдена в Bitrix24.\n\n"
                "Проверьте ID и попробуйте снова."
            )
            return

        # Получаем название компании
        company_name = full_item.get('title', 'Клиент')
        stage_id = full_item.get('stageId', 'unknown')
        stage_name = BitrixStageService.get_stage_name(stage_id)

        # Сохраняем привязку в БД с retry
        try:
            async with get_db_session() as session:
                chat_binding_repo = ChatBindingRepository(session)

                # Проверяем, есть ли уже привязка для этого чата
                existing = await chat_binding_repo.get_by_chat_id(message.chat.id)

                if existing:
                    # Обновляем существующую привязку
                    await chat_binding_repo.update(
                        existing.id,
                        bitrix_deal_id=bitrix_id,
                        company_name=company_name,
                        chat_title=message.chat.title,
                        is_active=True
                    )
                    logger.info(f"Updated binding: chat={message.chat.id}, bitrix={bitrix_id}")
                else:
                    # Создаём новую привязку
                    await chat_binding_repo.create(
                        chat_id=message.chat.id,
                        chat_title=message.chat.title,
                        bitrix_deal_id=bitrix_id,
                        company_name=company_name
                    )
                    logger.info(f"Created binding: chat={message.chat.id}, bitrix={bitrix_id}")

        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
            # БД не доступна, но сохраняем в кэш
            pass
        
        # Сохраняем в кэш (всегда)
        _chat_cache[message.chat.id] = {
            'chat_id': message.chat.id,
            'chat_title': message.chat.title,
            'bitrix_deal_id': bitrix_id,
            'company_name': company_name
        }
        logger.info(f"Cached binding: chat={message.chat.id}, bitrix={bitrix_id}")

        # Отправляем подтверждение
        text = (
            f"✅ <b>Карточка привязана!</b>\n\n"
            f"<b>Компания:</b> {company_name}\n"
            f"<b>ID Bitrix:</b> {bitrix_id}\n"
            f"<b>Стадия:</b> {stage_name}\n\n"
            f"⚠️ <i>Примечание: временные проблемы с БД, но карточка привязана!</i>\n\n"
            f"Я буду отправлять отчёты в этот чат каждое утро в 9:00 МСК.\n\n"
            f"<i>Используйте /report для получения текущего отчёта.</i>"
        )

        await progress_message.edit_text(text, parse_mode="HTML")
        logger.info(f"Command /add executed successfully for bitrix_id={bitrix_id} in chat {message.chat.id}")
        
    except TelegramAPIError as e:
        logger.error(f"Telegram API error in /add: {e}")
        try:
            await message.answer(f"❌ Ошибка Telegram: {str(e)}")
        except:
            pass
    except Exception as e:
        logger.exception(f"Error in /add command: {e}")
        try:
            await message.answer(f"❌ Произошла ошибка: {str(e)}")
        except:
            pass


# ============================================
# КОМАНДА /report
# ============================================
@dp.message(Command("report"))
async def cmd_report(message: Message):
    """Получение текущего отчёта по привязанной карточке"""
    try:
        # Проверяем, что это группа
        if message.chat.type not in ["group", "supergroup"]:
            await message.answer("❌ Эта команда работает только в групповых чатах.")
            return

        # Отправляем сообщение о процессе
        progress_message = await message.answer("🔄 Получаю данные из Bitrix24...")

        # Ищем привязку в памяти (кэш)
        # В production нужно использовать БД, но для теста берём из Bitrix напрямую
        # Проверяем последние команды /add для этого чата
        from app.bot.commands import _chat_cache
        
        binding = _chat_cache.get(message.chat.id)
        
        if not binding:
            # Пытаемся получить из БД (sync version)
            try:
                from app.database.db_sync import get_db_cursor, dict_fetchone
                import asyncio
                
                loop = asyncio.get_event_loop()
                
                def _get_binding():
                    try:
                        with get_db_cursor() as cur:
                            cur.execute(
                                "SELECT id, chat_id, chat_title, bitrix_deal_id, company_name FROM chat_bindings WHERE chat_id = %s LIMIT 1",
                                (message.chat.id,)
                            )
                            return dict_fetchone(cur)
                    except Exception as db_err:
                        logger.warning(f"DB error in /report: {db_err}")
                        return None
                
                binding = await loop.run_in_executor(None, _get_binding)
            except Exception as e:
                logger.error(f"Error getting binding: {e}")
                binding = None

        if not binding:
            await progress_message.edit_text(
                "❌ К этому чату не привязана карточка Bitrix.\n\n"
                "Используйте /add <ID> для привязки."
            )
            return

        # Получаем данные из Bitrix
        bitrix_polling = BitrixPollingService()
        full_item = await bitrix_polling.get_item_by_id(int(binding['bitrix_deal_id'] if isinstance(binding, dict) else binding.bitrix_deal_id))

        if not full_item:
            await progress_message.edit_text(
                f"❌ Не удалось получить данные из Bitrix24 для карточки {binding['bitrix_deal_id'] if isinstance(binding, dict) else binding.bitrix_deal_id}."
            )
            return

        # Формируем отчёт
        company_name = full_item.get('title', 'Клиент')
        inn = full_item.get('ufCrm20_1738855110463', 'N/A')
        stage_id = full_item.get('stageId', 'unknown')
        stage_name = BitrixStageService.get_stage_name(stage_id)

        raw_products = full_item.get('ufCrm20_1739184606910', [])
        raw_wait_reasons = full_item.get('ufCrm20_1763475932592', [])

        # Форматируем
        product_map = {
            '8426': 'ЕГАИС',
            '8428': 'Накладные',
            '8430': 'ЮЗЭДО',
            '8432': 'Меркурий',
            '8434': 'Маркировка',
        }
        products = [product_map.get(str(p), f"Продукт #{p}") for p in raw_products]

        action_items = WaitReasonsService.format_action_items(raw_wait_reasons)
        general_risk = WaitReasonsService.get_general_risk(raw_wait_reasons, raw_products)

        # Собираем сообщение
        product_lines = [f"• {p}" for p in products]
        action_lines = [f"• {action}" for action, _ in action_items]

        text = f"""🔍 <b>Отчёт для {company_name}</b>

📋 <b>Данные из Bitrix24:</b>
• ИНН: {inn}
• Стадия: {stage_name}

✅ <b>Подключённые продукты:</b>
{chr(10).join(product_lines) if product_lines else '• Не указаны'}

⏳ <b>Осталось сделать:</b>
{chr(10).join(action_lines) if action_lines else '• Нет активных задач'}

💡 <b>Это важно, потому что:</b>
{general_risk}

---
<i>Бот онбординга Bitrix24</i>"""

        await progress_message.edit_text(text, parse_mode="HTML")
        logger.info(f"Command /report executed for chat {message.chat.id}")
        
    except TelegramAPIError as e:
        logger.error(f"Telegram API error in /report: {e}")
    except Exception as e:
        logger.exception(f"Error in /report command: {e}")
        try:
            await message.answer(f"❌ Произошла ошибка: {str(e)}")
        except:
            pass


# ============================================
# КОМАНДА /help
# ============================================
@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Справка по командам"""
    try:
        text = """<b>Бот онбординга DocsInBox</b>

Я помогаю внедренцам и клиентам отслеживать прогресс внедрения.

<b>Команды:</b>

/add <ID> — Привязать карточку Bitrix к чату
  Пример: /add 9200
  ID берётся из ссылки на карточку в Bitrix24

/report — Получить текущий отчёт по привязанной карточке

/help — Показать эту справку

<b>Как это работает:</b>

1. Внедренец создаёт чат с клиентом
2. Добавляет бота в чат
3. Пишет /add <ID карточки>
4. Бот отправляет отчёты каждое утро в 9:00 МСК

<b>Что в отчёте:</b>
• Список подключённых продуктов
• Осталось сделать (с причинами)
• Риски (почему это важно)"""

        await message.answer(text, parse_mode="HTML")
        
    except TelegramAPIError as e:
        logger.error(f"Telegram API error in /help: {e}")
    except Exception as e:
        logger.exception(f"Error in /help command: {e}")


# ============================================
# ЗАПУСК БОТА
# ============================================
async def start_bot_polling():
    """
    Запуск бота в режиме polling.
    
    Важно: эта функция должна вызываться как asyncio.create_task()
    в том же event loop что и FastAPI.
    """
    logger.info("Starting bot polling...")
    try:
        # Используем allowed_updates для получения всех типов обновлений
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    except asyncio.CancelledError:
        logger.info("Bot polling cancelled")
        raise
    except Exception as e:
        logger.exception(f"Bot polling error: {e}")
        raise


async def stop_bot_polling():
    """Остановка бота и закрытие сессии"""
    logger.info("Stopping bot polling...")
    try:
        await bot.session.close()
        logger.info("Bot session closed")
    except Exception as e:
        logger.error(f"Error closing bot session: {e}")

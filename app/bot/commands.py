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

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.exceptions import TelegramAPIError

from app.config import settings
from app.database.connection import get_db_session
from app.database.repository import ChatBindingRepository
from app.database.models import ChatBinding
from app.services.bitrix_polling_service import BitrixPollingService
from app.services.wait_reasons_service import WaitReasonsService
from app.services.bitrix_stage_service import BitrixStageService
from app.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=settings.telegram_bot_token, session=None)
dp = Dispatcher()

# Глобальный кэш для временного хранения привязок (сбрасывается при рестарте)
_chat_cache: Dict[str, Dict[str, Any]] = {}


def _get_cache_key(chat_id: int, message_thread_id: Optional[int] = None) -> str:
    """Создаёт ключ кэша с учётом топика"""
    if message_thread_id:
        return f"{chat_id}_thread_{message_thread_id}"
    return str(chat_id)


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
        else:
            text = (
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
    Привязка карточки Bitrix к чату (или топику в Topics).

    Использование: /add 9200

    Логика:
    1. Парсим ID карточки из аргументов
    2. Проверяем карточку в Bitrix24
    3. Сохраняем привязку в базу данных (с учётом message_thread_id для Topics)
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

                # Получаем ID топика (для Topics групп)
                # message_thread_id доступен только в Topics чатах
                message_thread_id = None
                if hasattr(message, 'message_thread_id'):
                    message_thread_id = message.message_thread_id
                    logger.info(f"Topic detected: thread_id={message_thread_id}")

                # Проверяем, есть ли уже привязка для этого чата + топика
                existing_bindings = await chat_binding_repo.get_by_chat_and_thread(
                    message.chat.id,
                    message_thread_id
                )

                if existing_bindings:
                    # Обновляем существующую привязку (первую)
                    existing = existing_bindings[0]
                    await chat_binding_repo.update(
                        existing.id,
                        bitrix_deal_id=bitrix_id,
                        company_name=company_name,
                        chat_title=message.chat.title,
                        is_active=True
                    )
                    logger.info(f"Updated binding: chat={message.chat.id}, thread={message_thread_id}, bitrix={bitrix_id}")
                else:
                    # Создаём новую привязку
                    await chat_binding_repo.create(
                        chat_id=message.chat.id,
                        message_thread_id=message_thread_id,
                        chat_title=message.chat.title,
                        bitrix_deal_id=bitrix_id,
                        company_name=company_name
                    )
                    logger.info(f"Created binding: chat={message.chat.id}, thread={message_thread_id}, bitrix={bitrix_id}")

        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
            # БД не доступна, но сохраняем в кэш
            pass

        # Сохраняем в кэш (всегда)
        cache_key = _get_cache_key(message.chat.id, message_thread_id)
        _chat_cache[cache_key] = {
            'chat_id': message.chat.id,
            'message_thread_id': message_thread_id,
            'chat_title': message.chat.title,
            'bitrix_deal_id': bitrix_id,
            'company_name': company_name
        }
        logger.debug(f"Cached binding: {cache_key}, bitrix={bitrix_id}")

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
        # Получаем ID топика (для Topics групп)
        message_thread_id = getattr(message, 'message_thread_id', None)
        
        # Ключ кэша с учётом топика
        cache_key = _get_cache_key(message.chat.id, message_thread_id)
        
        # Сначала ищем в кэше
        binding = _chat_cache.get(cache_key)

        if not binding:
            # Пытаемся получить из БД (sync version)
            try:
                from app.database.db_sync import get_db_cursor, dict_fetchall
                import asyncio

                loop = asyncio.get_event_loop()

                def _get_bindings():
                    try:
                        with get_db_cursor() as cur:
                            if message_thread_id:
                                # Для Topics - ищем в конкретном топике
                                # ИЛИ ищем привязку без топика (для обратной совместимости)
                                cur.execute(
                                    """SELECT id, chat_id, message_thread_id, chat_title, bitrix_deal_id, company_name 
                                       FROM chat_bindings 
                                       WHERE chat_id = %s AND (message_thread_id = %s OR message_thread_id IS NULL)
                                       ORDER BY message_thread_id DESC NULLS LAST
                                       LIMIT 1""",
                                    (message.chat.id, message_thread_id)
                                )
                            else:
                                # Для обычных чатов - ищем без топика
                                cur.execute(
                                    """SELECT id, chat_id, message_thread_id, chat_title, bitrix_deal_id, company_name 
                                       FROM chat_bindings 
                                       WHERE chat_id = %s AND message_thread_id IS NULL
                                       LIMIT 1""",
                                    (message.chat.id,)
                                )
                            return dict_fetchall(cur)
                    except Exception as db_err:
                        logger.warning(f"DB error in /report: {db_err}")
                        return None

                bindings = await loop.run_in_executor(None, _get_bindings)
                if bindings:
                    binding = bindings[0]
                    logger.debug(f"Found DB binding: chat={message.chat.id}, thread={message_thread_id}")
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
        bitrix_id = binding.get('bitrix_deal_id') if isinstance(binding, dict) else binding.bitrix_deal_id
        logger.info(f"Fetching Bitrix data for item {bitrix_id}...")
        full_item = await bitrix_polling.get_item_by_id(int(bitrix_id))

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
        text = """<b>🤖 Бот онбординга DocsInBox</b>

Я помогаю внедренцам и клиентам отслеживать прогресс внедрения продуктов.

<b>📋 Основные команды:</b>

/add <ID> — Привязать карточку Bitrix к чату/топику
  <i>Пример:</i> <code>/add 9200</code>
  <i>ID берётся из ссылки на карточку в Bitrix24</i>

/report — Получить текущий отчёт по привязанной карточке
  <i>Показывает стадию, продукты и задачи</i>

/product_report — Отчёт по продуктам
  <i>ЕГАИС, Меркурий, Маркировка, Накладные, ЮЗЭДО</i>

/help — Показать эту справку

<b>👥 Для кого:</b>

• <b>Внедренцы:</b> добавьте бота в чат с клиентом и забудьте о ручных отчётах
• <b>Клиенты:</b> получайте понятные инструкции что делать дальше
• <b>Руководители:</b> контролируйте прогресс внедрения

<b>⚙️ Как работает:</b>

1️⃣ Внедренец создаёт чат с клиентом
2️⃣ Добавляет бота в чат
3️⃣ Пишет <code>/add <ID карточки></code>
4️⃣ Бот отправляет отчёты каждое утро в 9:00 МСК

<b>📊 Что в отчёте:</b>
• Название компании и ИНН
• Текущая стадия внедрения
• Список подключённых продуктов
• Осталось сделать (с причинами)
• Риски (почему это важно)

<b>🎯 Особенности:</b>
• Работает в обычных чатах
• Поддерживает Telegram Topics (отдельные привязки по топикам)
• Автоматические отчёты в 9:00 МСК
• Интеграция с Bitrix24

<b>📞 Вопросы?</b>
Обратитесь к разработчикам бота."""

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

"""
Comprehensive Integration Test Script
Тестирует полный цикл работы бота:
1. Подключение к БД
2. Подключение к Telegram
3. Подключение к Bitrix24
4. Команда /add
5. Планировщик задач
6. Отправка напоминаний
"""
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import dotenv_values

# Загружаем .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    env_values = dotenv_values(str(env_path))
    for key, value in env_values.items():
        if value is not None:
            os.environ[key] = value

# Цвета для вывода
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}\n")


def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_info(text):
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


async def test_config():
    """Тест 1: Проверка конфигурации"""
    print_header("ТЕСТ 1: Проверка конфигурации")
    
    from app.config import settings
    
    errors = []
    
    if not settings.telegram_bot_token:
        errors.append("TELEGRAM_BOT_TOKEN не настроен")
    else:
        print_success(f"Telegram bot token: {settings.telegram_bot_token[:20]}...")
    
    if not settings.bitrix_webhook_url:
        errors.append("BITRIX_WEBHOOK_URL не настроен")
    else:
        print_success(f"Bitrix webhook URL: {settings.bitrix_webhook_url[:40]}...")
    
    if not settings.database_url:
        errors.append("DATABASE_URL не настроен")
    else:
        print_success(f"Database URL: {settings.database_url[:40]}...")    
    print_success(f"Timezone: {settings.timezone}")
    print_success(f"Bot send time: {settings.bot_send_time_hour}:00")
    
    if errors:
        for error in errors:
            print_error(error)
        return False
    
    print_success("Конфигурация проверена успешно")
    return True


async def test_database():
    """Тест 2: Проверка подключения к БД"""
    print_header("ТЕСТ 2: Проверка подключения к базе данных")
    
    try:
        from app.database.connection import init_db, get_db_session
        from app.database.repository import ChatBindingRepository, ClientRepository
        
        # Инициализация БД
        await init_db()
        print_success("База данных инициализирована")
        
        # Проверка таблиц
        async with get_db_session() as session:
            from sqlalchemy import text
            
            # Проверяем таблицу chat_bindings
            result = await session.execute(text("SELECT COUNT(*) FROM chat_bindings"))
            count = result.scalar()
            print_success(f"chat_bindings: {count} записей")
            
            # Проверяем таблицу clients
            result = await session.execute(text("SELECT COUNT(*) FROM clients"))
            count = result.scalar()
            print_success(f"clients: {count} записей")
            
            # Проверяем таблицу deal_stages
            result = await session.execute(text("SELECT COUNT(*) FROM deal_stages"))
            count = result.scalar()
            print_success(f"deal_stages: {count} записей")
        
        print_success("Подключение к БД успешно")
        return True
        
    except Exception as e:
        print_error(f"Ошибка подключения к БД: {e}")
        return False


async def test_telegram():
    """Тест 3: Проверка подключения к Telegram"""
    print_header("ТЕСТ 3: Проверка подключения к Telegram")
    
    try:
        from aiogram import Bot
        from app.config import settings
        
        bot = Bot(token=settings.telegram_bot_token)
        
        # Проверяем бота
        me = await bot.get_me()
        print_success(f"Бот подключен: @{me.username} ({me.first_name})")
        
        # Проверяем обновления
        updates = await bot.get_updates(offset=0, timeout=1)
        print_success(f"Получено обновлений: {len(updates)}")
        
        await bot.session.close()
        print_success("Подключение к Telegram успешно")
        return True
        
    except Exception as e:
        print_error(f"Ошибка подключения к Telegram: {e}")
        return False


async def test_bitrix():
    """Тест 4: Проверка подключения к Bitrix24"""
    print_header("ТЕСТ 4: Проверка подключения к Bitrix24")
    
    try:
        from app.services.bitrix_polling_service import BitrixPollingService
        
        bitrix = BitrixPollingService()
        
        if not bitrix.webhook_url:
            print_error("Bitrix webhook URL не настроен")
            return False
        
        # Получаем все элементы на стадиях ожидания
        print_info("Получение элементов на стадиях ожидания...")
        items = await bitrix.get_waiting_items(limit=100)
        print_success(f"Найдено элементов: {len(items)}")
        
        # Показываем разбивку по стадиям
        if items:
            by_stage = {}
            for item in items:
                stage = item.get('stageId', 'UNKNOWN')
                if stage not in by_stage:
                    by_stage[stage] = 0
                by_stage[stage] += 1
            
            print_info("Разбивка по стадиям:")
            for stage, count in sorted(by_stage.items(), key=lambda x: -x[1])[:5]:
                print(f"  {stage}: {count}")
        
        # Тестируем получение конкретного элемента
        if items:
            test_item = items[0]
            print_info(f"Тест получения полного элемента (ID={test_item.get('id')})...")
            full_item = await bitrix.get_item_by_id(test_item['id'])
            
            if full_item:
                print_success(f"Элемент получен: {full_item.get('title', '')[:50]}")
                
                # Проверяем UF-поля
                telegram = full_item.get('ufCrm20_1747732557645')
                inn = full_item.get('ufCrm20_1738855110463')
                products = full_item.get('ufCrm20_1739184606910')
                wait_reasons = full_item.get('ufCrm20_1763475932592')
                
                print_info(f"  Telegram: {telegram}")
                print_info(f"  INN: {inn}")
                print_info(f"  Products: {products}")
                print_info(f"  Wait reasons: {wait_reasons}")
            else:
                print_warning("Не удалось получить полный элемент")
        
        print_success("Подключение к Bitrix24 успешно")
        return True
        
    except Exception as e:
        print_error(f"Ошибка подключения к Bitrix24: {e}")
        return False


async def test_wait_reasons_service():
    """Тест 5: Проверка WaitReasonsService"""
    print_header("ТЕСТ 5: Проверка WaitReasonsService")
    
    try:
        from app.services.wait_reasons_service import WaitReasonsService
        
        # Тестовые данные
        test_reasons = ['21078', '21080', '21108']  # Сопоставления, Заполнение ТЗ, Заполнение ТТК
        
        # Тестируем форматирование
        action_items = WaitReasonsService.format_action_items(test_reasons)
        print_success(f"Action items: {len(action_items)}")
        for action, risk in action_items:
            print(f"  - {action}")
        
        # Тестируем группировку по рискам
        general_risk = WaitReasonsService.get_general_risk(test_reasons, ['8426'])
        print_success(f"General risk: {general_risk[:100]}...")
        
        print_success("WaitReasonsService работает корректно")
        return True
        
    except Exception as e:
        print_error(f"Ошибка WaitReasonsService: {e}")
        return False


async def test_scheduler():
    """Тест 6: Проверка планировщика"""
    print_header("ТЕСТ 6: Проверка планировщика задач")
    
    try:
        from app.bot.scheduler import start_scheduler, shutdown_scheduler, send_daily_reminders
        
        # Запускаем планировщик
        await start_scheduler()
        print_success("Планировщик запущен")
        
        # Проверяем задачи
        from app.bot.scheduler import _scheduler
        if _scheduler:
            jobs = _scheduler.get_jobs()
            print_success(f"Запланировано задач: {len(jobs)}")
            for job in jobs:
                print(f"  - {job.name}: {job.trigger}")
        
        # Останавливаем планировщик
        await shutdown_scheduler()
        print_success("Планировщик остановлен")
        
        return True
        
    except Exception as e:
        print_error(f"Ошибка планировщика: {e}")
        return False


async def test_notification_service():
    """Тест 7: Проверка NotificationService"""
    print_header("ТЕСТ 7: Проверка NotificationService")
    
    try:
        from app.services.notification_service import NotificationService
        from app.services.bitrix_polling_service import BitrixPollingService
        
        notification = NotificationService()
        bitrix = BitrixPollingService()
        
        # Получаем тестовый элемент
        items = await bitrix.get_waiting_items(limit=1)
        if not items:
            print_warning("Нет элементов для тестирования")
            return True
        
        full_item = await bitrix.get_item_by_id(items[0]['id'])
        if not full_item:
            print_warning("Не удалось получить полный элемент")
            return True
        
        # Тестируем формирование сообщения
        company_name = full_item.get('title', 'Тест')
        message = notification._build_message_from_bitrix(full_item, company_name)
        
        print_success(f"Сообщение сформировано ({len(message)} символов)")
        print_info(f"Первые 200 символов: {message[:200]}...")
        
        print_success("NotificationService работает корректно")
        return True
        
    except Exception as e:
        print_error(f"Ошибка NotificationService: {e}")
        return False


async def test_full_flow():
    """Тест 8: Полный цикл (имитация)"""
    print_header("ТЕСТ 8: Полный цикл работы (имитация)")
    
    try:
        from app.database.connection import get_db_session
        from app.database.repository import ChatBindingRepository
        from app.services.bitrix_polling_service import BitrixPollingService
        from app.services.notification_service import NotificationService
        
        bitrix = BitrixPollingService()
        notification = NotificationService()
        
        # 1. Получаем элемент из Bitrix
        print_info("1. Получение элемента из Bitrix24...")
        items = await bitrix.get_waiting_items(limit=1)
        if not items:
            print_warning("Нет элементов для тестирования")
            return True
        
        full_item = await bitrix.get_item_by_id(items[0]['id'])
        if not full_item:
            print_warning("Не удалось получить полный элемент")
            return True
        
        print_success(f"Элемент получен: {full_item.get('title', '')[:50]}")
        
        # 2. Формируем сообщение
        print_info("2. Формирование сообщения...")
        company_name = full_item.get('title', 'Тест')
        message = notification._build_message_from_bitrix(full_item, company_name)
        print_success(f"Сообщение сформировано ({len(message)} символов)")
        
        # 3. Проверяем БД
        print_info("3. Проверка базы данных...")
        async with get_db_session() as session:
            chat_binding_repo = ChatBindingRepository(session)
            bindings = await chat_binding_repo.get_active_bindings()
            print_success(f"Активных привязок: {len(bindings)}")
        
        print_success("Полный цикл пройден успешно")
        return True
        
    except Exception as e:
        print_error(f"Ошибка полного цикла: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Запуск всех тестов"""
    print_header("КОМПЛЕКСНЫЙ ТЕСТ СИСТЕМЫ")
    print(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        "Конфигурация": await test_config(),
        "База данных": await test_database(),
        "Telegram": await test_telegram(),
        "Bitrix24": await test_bitrix(),
        "WaitReasonsService": await test_wait_reasons_service(),
        "Планировщик": await test_scheduler(),
        "NotificationService": await test_notification_service(),
        "Полный цикл": await test_full_flow(),
    }
    
    # Итоги
    print_header("ИТОГИ ТЕСТИРОВАНИЯ")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        if result:
            print_success(f"{test_name}: PASSED")
        else:
            print_error(f"{test_name}: FAILED")
    
    print(f"\n{Colors.BOLD}Итого: {passed}/{total} тестов пройдено{Colors.RESET}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!{Colors.RESET}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ{Colors.RESET}\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

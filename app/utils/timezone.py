"""
Утилиты для работы с часовыми поясами
"""
from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.config import settings


def get_msk_time() -> datetime:
    """
    Возвращает текущее время в Москве (MSK, UTC+3).
    """
    return datetime.now(ZoneInfo(settings.timezone))


def is_work_hours(current_time: datetime | None = None) -> bool:
    """
    Проверяет, является ли время рабочим (9:00-18:00 МСК).
    
    Args:
        current_time: Время для проверки (по умолчанию — сейчас)
    
    Returns:
        True, если время рабочее
    """
    if current_time is None:
        current_time = get_msk_time()
    
    msk_hour = current_time.hour
    
    return settings.bot_work_hours_start <= msk_hour < settings.bot_work_hours_end


def is_nine_am_msk() -> bool:
    """
    Проверяет, сейчас ли 9:00 МСК (±1 минута).
    
    Используется для планировщика задач.
    """
    current_time = get_msk_time()
    
    return (
        current_time.hour == settings.bot_send_time_hour
        and current_time.minute <= 1
    )


def get_next_send_time() -> datetime:
    """
    Возвращает время следующей отправки сообщений.
    
    Если сейчас 9:00-18:00 — сегодня в 9:00.
    Иначе — завтра в 9:00.
    """
    now = get_msk_time()
    
    # Целевое время сегодня в 9:00
    target_time = now.replace(
        hour=settings.bot_send_time_hour,
        minute=0,
        second=0,
        microsecond=0,
    )
    
    # Если уже прошло 9:00 или ещё не наступило — завтра
    if now.hour >= settings.bot_work_hours_end or now.hour < settings.bot_send_time_hour:
        # Завтра в 9:00
        from datetime import timedelta
        target_time = target_time + timedelta(days=1)
    
    return target_time


def format_datetime_msk(dt: datetime) -> str:
    """
    Форматирует datetime в строку MSK.
    
    Пример: "26.02.2026 14:30"
    """
    msk_time = dt.astimezone(ZoneInfo(settings.timezone))
    return msk_time.strftime("%d.%m.%Y %H:%M")

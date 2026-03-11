"""
Celery приложение для фоновых задач

Задачи:
- fetch_daily_statuses: Сбор статусов из Bitrix24 (08:00 MSK)
- send_daily_reports: Отправка отчётов пользователям (09:00 MSK)
"""
import sys
import os
from celery import Celery
from celery.schedules import crontab

# Добавляем корень проекта в PATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings

# Инициализация Celery приложения
celery_app = Celery(
    "bitrix_bot_worker",
    broker=settings.celery_broker_url or settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.fetch_task",
        "app.tasks.send_task",
    ],
)

# Настройки timezone
celery_app.conf.timezone = settings.timezone
celery_app.conf.enable_utc = False

# Отключаем fast_trace_task для совместимости с Python 3.13
celery_app.conf.task_always_eager = False
celery_app.conf.task_track_success = True

# Расписание задач (по Москве)
celery_app.conf.beat_schedule = {
    "fetch-daily-statuses": {
        "task": "app.tasks.fetch_task.fetch_daily_statuses",
        "schedule": crontab(hour=8, minute=0),  # 08:00 MSK
    },
    "send-daily-reports": {
        "task": "app.tasks.send_task.send_daily_reports",
        "schedule": crontab(hour=settings.bot_send_time_hour, minute=0),  # 09:00 MSK (из .env)
    },
}

# Настройки rate limiting для Bitrix API (2 запроса/сек)
celery_app.conf.worker_prefetch_multiplier = 1
celery_app.conf.task_acks_late = True
celery_app.conf.task_track_started = True

# Настройки сериализации
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)

"""
Обработчики команд для управления подписками на Bitrix24 карточки

Команды:
- /add <ID> — добавить карточку в подписки
- /list — список подписок
- /remove <ID> — удалить подписку
- /status — запросить актуальные статусы
- /stop — отключить рассылку
"""
import logging
from typing import Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from app.config import settings
from app.database.connection import get_session_maker
from app.database.models_bot import User, Subscription
from app.services.bitrix_service import BitrixService

logger = logging.getLogger(__name__)

# Роутер для новых обработчиков
subscriptions_router = Router()


async def get_or_create_user(session, tg_id: int, username: Optional[str], 
                             first_name: Optional[str] = None, 
                             last_name: Optional[str] = None) -> User:
    """Получить или создать пользователя в БД."""
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            tg_id=tg_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    return user


@subscriptions_router.message(Command("add"))
async def cmd_add(message: Message):
    """
    Обработчик команды /add <ID>.

    Добавляет карточку Bitrix24 в подписки пользователя.
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Укажи ID карточки: /add 12345")
        return

    item_id = args[1].strip()

    # Проверяем существование в Bitrix
    bitrix_service = BitrixService()
    item = await bitrix_service.get_deal(item_id)
    
    if not item:
        await message.answer(f"❌ Карточка с ID {item_id} не найдена в Bitrix24.")
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await get_or_create_user(
            session,
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name,
        )

        # Проверяем лимит подписок
        result = await session.execute(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        subs = result.scalars().all()

        if len(subs) >= settings.max_subscriptions_per_user:
            await message.answer(
                f"❌ Максимум {settings.max_subscriptions_per_user} подписок."
            )
            return

        # Проверяем дубликат
        dup = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.bitrix_item_id == item_id,
            )
        )
        if dup.scalar_one_or_none():
            await message.answer(f"⚠️ Карточка {item_id} уже добавлена.")
            return

        # Сохраняем подписку
        sub = Subscription(
            user_id=user.id,
            bitrix_item_id=item_id,
            bitrix_fields=item,
        )
        session.add(sub)
        await session.commit()

    await message.answer(
        f"✅ Карточка {item_id} добавлена! "
        f"Статус будет приходить в 09:00 MSK."
    )


@subscriptions_router.message(Command("list"))
async def cmd_list(message: Message):
    """Обработчик команды /list — показывает подписки пользователя."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        result = await session.execute(
            select(User).where(User.tg_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("У тебя нет подписок.")
            return

        result = await session.execute(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        subs = result.scalars().all()

    if not subs:
        await message.answer("📭 У тебя нет активных подписок.")
        return

    lines = [f"📋 Твои подписки ({len(subs)}/{settings.max_subscriptions_per_user}):"]
    for sub in subs:
        lines.append(f"• ID: {sub.bitrix_item_id}")

    await message.answer("\n".join(lines))


@subscriptions_router.message(Command("remove"))
async def cmd_remove(message: Message):
    """
    Обработчик команды /remove <ID>.

    Удаляет карточку из подписок пользователя.
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Укажи ID карточки: /remove 12345")
        return

    item_id = args[1].strip()

    session_maker = get_session_maker()
    async with session_maker() as session:
        result = await session.execute(
            select(User).where(User.tg_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("❌ Пользователь не найден.")
            return

        result = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.bitrix_item_id == item_id,
            )
        )
        sub = result.scalar_one_or_none()

        if not sub:
            await message.answer(f"❌ Подписка на карточку {item_id} не найдена.")
            return

        await session.delete(sub)
        await session.commit()

    await message.answer(f"🗑️ Карточка {item_id} удалена из подписок.")


@subscriptions_router.message(Command("stop"))
async def cmd_stop(message: Message):
    """
    Обработчик команды /stop.

    Отключает пользователю ежедневную рассылку.
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        result = await session.execute(
            select(User).where(User.tg_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        if user:
            user.is_active = False
            await session.commit()

    await message.answer(
        "🔕 Рассылка отключена. "
        "Для включения напиши /start."
    )


@subscriptions_router.message(Command("status"))
async def cmd_status(message: Message):
    """
    Обработчик команды /status.

    Запрашивает актуальные статусы карточек из Bitrix24.
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        result = await session.execute(
            select(User).where(User.tg_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await message.answer(
                "У тебя нет подписок. Добавь карточку через /add <ID>"
            )
            return

        result = await session.execute(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        subs = result.scalars().all()

    if not subs:
        await message.answer("📭 Нет подписок. Добавь через /add <ID>")
        return

    await message.answer("🔄 Запрашиваю статусы...")

    bitrix_service = BitrixService()
    lines = []
    
    for sub in subs:
        item = await bitrix_service.get_deal(sub.bitrix_item_id)
        if item:
            title = item.get("TITLE") or item.get("NAME") or f"ID {sub.bitrix_item_id}"
            stage = item.get("STAGE_ID", "—")
            lines.append(f"📌 *{title}*\nСтатус: `{stage}`")
        else:
            lines.append(
                f"❌ Карточка {sub.bitrix_item_id}: не удалось получить данные"
            )

    await message.answer("\n\n".join(lines), parse_mode="Markdown")

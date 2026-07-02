import asyncio
import logging
from typing import List, Dict, Any, Optional

from aiogram import Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramRetryAfter

import config
import texts
from database import Database
from utils import safe_send_message, safe_edit_message


logger = logging.getLogger(__name__)


async def send_broadcast(
    bot: Bot,
    db: Database,
    admin_message: Message
) -> Dict[str, Any]:
    """
    Обычная рассылка с сохранением оригинального форматирования
    
    Args:
        bot: экземпляр бота
        db: экземпляр БД
        admin_message: сообщение администратора (шаблон)
    
    Returns:
        Dict: {total, sent, failed}
    """
    users = await db.get_active_users()
    if not users:
        return {"total": 0, "sent": 0, "failed": 0}
    
    total = len(users)
    sent = 0
    failed = 0
    
    for user_data in users:
        user_id = user_data['telegram_id']
        try:
            await admin_message.copy_to(
                chat_id=user_id,
                reply_markup=None
            )
            sent += 1
            await asyncio.sleep(0.05)
        except TelegramRetryAfter as e:
            logger.warning(f"Retry after {e.retry_after}s for user {user_id}")
            await asyncio.sleep(e.retry_after)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            error = str(e).lower()
            if "blocked" in error or "bot was blocked" in error:
                await db.set_blocked(user_id, True)
            failed += 1
            logger.error(f"Send broadcast failed for {user_id}: {e}")
    
    await db.add_broadcast("send", sent, failed)
    logger.info(f"Broadcast completed: sent={sent}, failed={failed}, total={total}")
    
    return {"total": total, "sent": sent, "failed": failed}


async def forward_broadcast(
    bot: Bot,
    db: Database,
    admin_message: Message
) -> Dict[str, Any]:
    """
    Пересылка сообщения всем пользователям
    
    Args:
        bot: экземпляр бота
        db: экземпляр БД
        admin_message: сообщение администратора (для пересылки)
    
    Returns:
        Dict: {total, sent, failed}
    """
    users = await db.get_active_users()
    if not users:
        return {"total": 0, "sent": 0, "failed": 0}
    
    total = len(users)
    sent = 0
    failed = 0
    
    for user_data in users:
        user_id = user_data['telegram_id']
        try:
            await admin_message.forward(
                chat_id=user_id
            )
            sent += 1
            await asyncio.sleep(0.05)
        except TelegramRetryAfter as e:
            logger.warning(f"Retry after {e.retry_after}s for user {user_id}")
            await asyncio.sleep(e.retry_after)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            error = str(e).lower()
            if "blocked" in error or "bot was blocked" in error:
                await db.set_blocked(user_id, True)
            failed += 1
            logger.error(f"Forward broadcast failed for {user_id}: {e}")
    
    await db.add_broadcast("forward", sent, failed)
    logger.info(f"Forward broadcast completed: sent={sent}, failed={failed}, total={total}")
    
    return {"total": total, "sent": sent, "failed": failed}


async def video_broadcast(
    bot: Bot,
    db: Database,
    video_url: str
) -> Dict[str, Any]:
    """
    Рассылка уведомления о новом видео
    
    Args:
        bot: экземпляр бота
        db: экземпляр БД
        video_url: ссылка на видео
    
    Returns:
        Dict: {total, sent, failed}
    """
    users = await db.get_active_users()
    if not users:
        return {"total": 0, "sent": 0, "failed": 0}
    
    text = (
        "🎬 Новое видео уже на канале!\n\n"
        "👇👇👇\n\n"
        f'🔥 <a href="{video_url}"><b>СМОТРЕТЬ</b></a>'
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Смотреть", url=video_url)]
    ])
    
    total = len(users)
    sent = 0
    failed = 0
    
    for user_data in users:
        user_id = user_data['telegram_id']
        try:
            await bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard,
                disable_web_page_preview=False
            )
            sent += 1
            await asyncio.sleep(0.05)
        except TelegramRetryAfter as e:
            logger.warning(f"Retry after {e.retry_after}s for user {user_id}")
            await asyncio.sleep(e.retry_after)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            error = str(e).lower()
            if "blocked" in error or "bot was blocked" in error:
                await db.set_blocked(user_id, True)
            failed += 1
            logger.error(f"Video broadcast failed for {user_id}: {e}")
    
    await db.add_broadcast("video", sent, failed)
    logger.info(f"Video broadcast completed: sent={sent}, failed={failed}, total={total}")
    
    return {"total": total, "sent": sent, "failed": failed}
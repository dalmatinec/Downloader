import asyncio
import logging
import random
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
            try:
                await admin_message.copy_to(
                    chat_id=user_id,
                    reply_markup=None
                )
                sent += 1
                await asyncio.sleep(0.05)
            except Exception as e2:
                error = str(e2).lower()
                if "blocked" in error or "bot was blocked" in error:
                    await db.set_blocked(user_id, True)
                failed += 1
                logger.error(f"Send broadcast retry failed for {user_id}: {e2}")
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
            try:
                await admin_message.forward(
                    chat_id=user_id
                )
                sent += 1
                await asyncio.sleep(0.05)
            except Exception as e2:
                error = str(e2).lower()
                if "blocked" in error or "bot was blocked" in error:
                    await db.set_blocked(user_id, True)
                failed += 1
                logger.error(f"Forward broadcast retry failed for {user_id}: {e2}")
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
    Рассылка уведомления о новом видео + публикация в канал + реакция Кеши
    
    Args:
        bot: экземпляр бота
        db: экземпляр БД
        video_url: ссылка на видео
    
    Returns:
        Dict: {total, sent, failed}
    """
    text = (
        "🎬 <b>Новое видео уже на канале!</b>\n\n"
        "Друзья, я снял для вас новый ролик. Надеюсь, он подарит вам тёплые эмоции и хорошее настроение.\n\n"
        "👇 Нажмите на кнопку ниже, чтобы посмотреть:\n"
        f'🔥 <a href="{video_url}"><b>СМОТРЕТЬ НА YOUTUBE</b></a>'
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Смотреть", url=video_url)]
    ])

    # Публикация в канал
    try:
        await bot.send_message(
            chat_id=config.CHANNEL_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        logger.info(f"Video announcement sent to channel: {config.CHANNEL_ID}")
    except Exception as e:
        logger.exception(f"Failed to send video to channel: {e}")
        return {"total": 0, "sent": 0, "failed": 0}

    # Рассылка пользователям
    users = await db.get_active_users()
    if not users:
        await db.add_broadcast("video", 0, 0)
        return {"total": 0, "sent": 0, "failed": 0}

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
                disable_web_page_preview=True
            )
            sent += 1
            await asyncio.sleep(0.05)
        except TelegramRetryAfter as e:
            logger.warning(f"Retry after {e.retry_after}s for user {user_id}")
            await asyncio.sleep(e.retry_after)
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                    disable_web_page_preview=True
                )
                sent += 1
                await asyncio.sleep(0.05)
            except Exception as e2:
                error = str(e2).lower()
                if "blocked" in error or "bot was blocked" in error:
                    await db.set_blocked(user_id, True)
                failed += 1
                logger.error(f"Video broadcast retry failed for {user_id}: {e2}")
        except Exception as e:
            error = str(e).lower()
            if "blocked" in error or "bot was blocked" in error:
                await db.set_blocked(user_id, True)
            failed += 1
            logger.error(f"Video broadcast failed for {user_id}: {e}")

    await db.add_broadcast("video", sent, failed)
    logger.info(f"Video broadcast completed: sent={sent}, failed={failed}, total={total}")

    # === РЕАКЦИЯ КЕШИ В ЧАТ (с защитой try/except) ===
    try:
        if texts.VIDEO_REACTIONS:
            reaction = random.choice(texts.VIDEO_REACTIONS)
            await safe_send_message(
                bot=bot,
                chat_id=config.CHAT_ID,
                text=reaction
            )
            logger.info("Video reaction sent to chat")
    except Exception as e:
        logger.exception(f"Failed to send video reaction: {e}")

    return {"total": total, "sent": sent, "failed": failed}
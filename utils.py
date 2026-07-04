import html
import logging
from typing import Optional, List, Dict, Any

from aiogram import Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter

import config
import texts
from database import Database


logger = logging.getLogger(__name__)


async def safe_send_message(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup = None,
    reply_to_message_id: Optional[int] = None,
    disable_web_page_preview: bool = True,
    db: Database = None
) -> Optional[Message]:
    """Безопасная отправка сообщения с поддержкой reply_to_message_id"""
    try:
        return await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
            reply_to_message_id=reply_to_message_id,
            disable_web_page_preview=disable_web_page_preview
        )
    except TelegramRetryAfter as e:
        logger.warning(f"Retry after {e.retry_after}s for chat {chat_id}")
        await asyncio.sleep(e.retry_after)
        return await safe_send_message(
            bot, chat_id, text, reply_markup, reply_to_message_id,
            disable_web_page_preview, db
        )
    except TelegramBadRequest as e:
        error = str(e).lower()
        if "blocked" in error or "bot was blocked" in error:
            if db:
                await db.set_blocked(chat_id, True)
        elif "parse_mode" in error:
            return await safe_send_message(
                bot, chat_id, text, reply_markup, reply_to_message_id,
                disable_web_page_preview, db
            )
        logger.warning(f"Bad request: {e}")
        return None
    except Exception as e:
        logger.exception(f"safe_send_message error: {e}")
        return None


async def safe_edit_message(
    bot: Bot,
    text: str,
    chat_id: int = None,
    message_id: int = None,
    callback: CallbackQuery = None,
    reply_markup: InlineKeyboardMarkup = None,
    disable_web_page_preview: bool = True
) -> Optional[Message]:
    """Безопасное редактирование сообщения"""
    try:
        if callback:
            return await callback.message.edit_text(
                text=text,
                parse_mode="HTML",
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview
            )
        elif chat_id and message_id:
            return await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode="HTML",
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview
            )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return None
        logger.warning(f"Edit error: {e}")
        return None
    except Exception as e:
        logger.exception(f"safe_edit_message error: {e}")
        return None


async def safe_delete_message(
    bot: Bot,
    chat_id: int,
    message_id: int
) -> bool:
    """Безопасное удаление сообщения"""
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True
    except Exception as e:
        logger.warning(f"Delete failed: {e}")
        return False


def escape_html(text: str) -> str:
    """Экранирование HTML"""
    if not text:
        return ""
    return html.escape(text)


def format_donators(donators: List[Dict[str, Any]]) -> str:
    """Форматирование списка донатеров"""
    if not donators:
        return texts.DONATORS_EMPTY

    result = []
    for d in donators:
        name = escape_html(d['name'])
        if d.get('username'):
            result.append(f"🐾 {name} (@{escape_html(d['username'])})")
        else:
            result.append(f"🐾 {name}")

    return "\n".join(result)


def format_stats(stats: Dict[str, Any]) -> str:
    """Форматирование статистики"""
    return texts.ADMIN_STATS_TEXT.format(
        users=stats['users'],
        blocked=stats['blocked'],
        books=stats['books'],
        downloads=stats['downloads'],
        today=stats['today'],
        week=stats['week'],
        month=stats['month']
    )


def broadcast_progress(total: int, sent: int, failed: int) -> Dict[str, Any]:
    """Прогресс рассылки"""
    return {
        "total": total,
        "sent": sent,
        "failed": failed,
        "remaining": max(total - sent - failed, 0),
        "progress": int(((sent + failed) / total * 100) if total > 0 else 0)
    }
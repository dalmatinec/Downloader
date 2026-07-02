import asyncio
import html
import re
import logging
from typing import Optional, Dict, Any, List

from aiogram import Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter

import config
from database import Database


logger = logging.getLogger(__name__)
db = Database()


def is_super_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь суперадмином"""
    return user_id == config.SUPER_ADMIN_ID


async def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    if is_super_admin(user_id):
        return True
    return await db.get_admin_by_telegram_id(user_id) is not None


async def get_or_create_user(telegram_id: int, username: str = None, first_name: str = None, last_name: str = None) -> Optional[Dict[str, Any]]:
    """Получение пользователя из БД или автоматическое добавление при первом использовании"""
    user = await db.get_user_by_telegram_id(telegram_id)
    if not user:
        user_id = await db.add_user(telegram_id, username, first_name, last_name)
        if user_id:
            user = await db.get_user_by_id(user_id)
            await log_action(telegram_id, "user_registered", f"New user registered: {telegram_id}")
    return user


async def log_action(user_id: int, action: str, details: str = None) -> None:
    """Запись действия в таблицу logs"""
    await db.add_log(user_id, action, details)


async def safe_send_message(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup = None,
    parse_mode: str = "HTML",
    disable_web_page_preview: bool = True
) -> Optional[Message]:
    """Безопасная отправка сообщения с обработкой ошибок"""
    try:
        return await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview
        )
    except TelegramRetryAfter as e:
        logger.warning(f"Retry after {e.retry_after}s for chat {chat_id}")
        await asyncio.sleep(e.retry_after)
        return await safe_send_message(bot, chat_id, text, reply_markup, parse_mode, disable_web_page_preview)
    except TelegramBadRequest as e:
        if "parse_mode" in str(e):
            logger.warning(f"Parse_mode failed, retrying without: {e}")
            return await safe_send_message(bot, chat_id, text, reply_markup, None, disable_web_page_preview)
        logger.error(f"TelegramBadRequest: {e}")
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
    parse_mode: str = "HTML"
) -> Optional[Message]:
    """Безопасное редактирование сообщения с обработкой ошибок"""
    try:
        if callback:
            return await callback.message.edit_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        elif chat_id and message_id:
            return await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
    except TelegramRetryAfter as e:
        logger.warning(f"Retry after {e.retry_after}s")
        await asyncio.sleep(e.retry_after)
        return await safe_edit_message(bot, text, chat_id, message_id, callback, reply_markup, parse_mode)
    except TelegramBadRequest as e:
        if parse_mode and "parse_mode" in str(e):
            logger.warning(f"Parse_mode failed, retrying without: {e}")
            return await safe_edit_message(bot, text, chat_id, message_id, callback, reply_markup, None)
        logger.error(f"TelegramBadRequest: {e}")
        return None
    except Exception as e:
        logger.exception(f"safe_edit_message error: {e}")
        return None


async def safe_delete_message(
    bot: Bot,
    chat_id: int,
    message_id: int
) -> bool:
    """Безопасное удаление сообщения с обработкой ошибок"""
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True
    except TelegramBadRequest as e:
        logger.warning(f"Delete failed: {e}")
        return False
    except Exception as e:
        logger.exception(f"safe_delete_message error: {e}")
        return False


async def check_book_exists(book_id: int) -> bool:
    """Проверка существования книги"""
    book = await db.get_book_by_id(book_id)
    return book is not None


async def check_trigger_exists(trigger_id: int) -> bool:
    """Проверка существования триггера"""
    trigger = await db.get_trigger_by_id(trigger_id)
    return trigger is not None


async def check_admin_exists(telegram_id: int) -> bool:
    """Проверка существования администратора"""
    if is_super_admin(telegram_id):
        return True
    admin = await db.get_admin_by_telegram_id(telegram_id)
    return admin is not None


def escape_html(text: str) -> str:
    """Экранирование HTML для сообщений Telegram"""
    if not text:
        return ""
    return html.escape(text)


def format_duration(seconds: int) -> str:
    """Форматирование длительности в минуты, часы, дни"""
    if seconds <= 0:
        return "навсегда"
    
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}д")
    if hours > 0:
        parts.append(f"{hours}ч")
    if minutes > 0:
        parts.append(f"{minutes}м")
    
    return " ".join(parts) if parts else "0м"


def parse_duration(text: str) -> int:
    """Парсинг длительности из текста (поддерживает m/h/d и русские м/ч/д)"""
    if not text:
        return 0
    
    text = text.strip().lower()
    match = re.match(r'^(\d+)([mhдчdм])$', text)
    
    if not match:
        return 0
    
    value = int(match.group(1))
    unit = match.group(2)
    
    if unit in ('m', 'м'):
        return value * 60
    elif unit in ('h', 'ч'):
        return value * 3600
    elif unit in ('d', 'д'):
        return value * 86400
    
    return 0


def get_user_link(user_id: int, username: str = None, first_name: str = None) -> str:
    """Генерация HTML-ссылки на пользователя"""
    if username:
        return f"<a href='https://t.me/{username}'>{escape_html(username)}</a>"
    if first_name:
        return f"<a href='tg://user?id={user_id}'>{escape_html(first_name)}</a>"
    return f"<a href='tg://user?id={user_id}'>Пользователь</a>"


async def is_user_in_chat(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Проверка, находится ли пользователь в чате"""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.warning(f"is_user_in_chat error: {e}")
        return False
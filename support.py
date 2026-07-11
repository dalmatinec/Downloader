# support.py
import asyncio
import logging

from aiogram.types import CallbackQuery
from utils import safe_send_message
import texts
from setting_handlers import load_settings
from keyboards import get_book_thanks_kb, get_book_thanks_donate_kb

logger = logging.getLogger(__name__)


async def send_book_thanks(bot, chat_id: int) -> None:
    """Отправка сообщения благодарности после скачивания книги"""
    await asyncio.sleep(1.5)

    # Отправляем первое сообщение BOOK_THANKS с клавиатурой
    await safe_send_message(
        bot=bot,
        chat_id=chat_id,
        text=texts.BOOK_THANKS,
        reply_markup=get_book_thanks_kb()
    )


async def handle_book_thanks_donate(callback_query: CallbackQuery) -> None:
    """Обрабатывает нажатие кнопки поддержки автора"""
    # Удаляем первое сообщение
    await callback_query.message.delete()
    
    # Загружаем реквизиты
    settings = load_settings()
    
    # Подставляем реквизиты в текст
    text = texts.BOOK_THANKS_DONATE.format(
        kaspi=settings.get("KASPI_VISA", ""),
        freedom=settings.get("FREEDOM_VISA", ""),
        bcc=settings.get("BCC_VISA", ""),
        ru_phone=settings.get("RU_PHONE", "")
    )
    
    # Отправляем второе сообщение с реквизитами
    await safe_send_message(
        bot=callback_query.bot,
        chat_id=callback_query.message.chat.id,
        text=text,
        reply_markup=get_book_thanks_donate_kb()
    )
    
    await callback_query.answer()
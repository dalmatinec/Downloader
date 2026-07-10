import asyncio
import logging

from utils import safe_send_message
import texts
from setting_handlers import load_settings


logger = logging.getLogger(__name__)


async def send_book_thanks(bot, chat_id: int) -> None:
    """Отправка сообщения благодарности после скачивания книги"""
    await asyncio.sleep(1.5)
    
    settings = load_settings()
    
    text = texts.BOOK_THANKS.format(
        kaspi=settings.get("KASPI_VISA", ""),
        freedom=settings.get("FREEDOM_VISA", ""),
        bcc=settings.get("BCC_VISA", ""),
        ru_phone=settings.get("RU_PHONE", "")
    )
    
    await safe_send_message(
        bot=bot,
        chat_id=chat_id,
        text=text
    )
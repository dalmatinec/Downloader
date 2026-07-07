import re
import logging

from aiogram import Dispatcher, F
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
import texts
from utils import safe_send_message


logger = logging.getLogger(__name__)


class TriggerManager:
    def __init__(self):
        self.triggers = [
            r'(?i)книг[ауиейойе]?',      # книга, книги, книгу...
            r'(?i)книж[аиуе]?',          # книжка, книжки...
            r'(?i)почитать',
            r'(?i)посоветуй',
            r'(?i)посоветуете',
            r'(?i)творчеств',
            r'(?i)произведен',
            r'(?i)литератур',
        ]
        
        self.pattern = re.compile("|".join(self.triggers))

    def check_text(self, text: str) -> bool:
        if not text or len(text.strip()) < 3:
            return False
        return bool(self.pattern.search(text))


trigger_manager = TriggerManager()


async def handle_message(message: Message) -> None:
    if not message.text:
        return

    if message.from_user.is_bot:
        return

    if message.text.startswith("/"):
        return

    if not trigger_manager.check_text(message.text):
        return

    logger.info(
        f"Сработал триггер для пользователя {message.from_user.id}: {message.text[:50]}"
    )

    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.TRIGGER_RESPONSE_TEXT,
        reply_markup=await get_trigger_button(),
        reply_to_message_id=message.message_id
    )


async def get_trigger_button():
    builder = InlineKeyboardBuilder()
    builder.button(
        text=texts.TRIGGER_BUTTON_TEXT,
        url=f"https://t.me/{config.BOT_USERNAME.replace('@', '')}"
    )
    return builder.as_markup()


def register_trigger_handlers(dp: Dispatcher) -> None:
    dp.message.register(
        handle_message,
        F.chat.type.in_({"group", "supergroup"})
    )
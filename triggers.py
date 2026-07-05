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
            # Любые формы слов "книга", "книжка"
            r"\bкниг\w*\b",
            r"\bкниж\w*\b",

            # Читать
            r"\bпочита\w*\b",
            r"\bчитать\w*\b",
            r"\bчита\w*\b",

            # Просьбы посоветовать
            r"\bпосовет\w*\b",
            r"\bрекоменду\w*\b",

            # Получить книги
            r"\bпришл\w*\b.*\bкниг\w*\b",
            r"\bполуч\w*\b.*\bкниг\w*\b",
            r"\bдай\w*\b.*\bкниг\w*\b",
            r"\bможно\b.*\bкниг\w*\b",

            # Частые реальные сообщения
            r"\bинтерес\w*\b.*\bтворчеств\w*\b",
            r"\bваш\w*\b.*\bкниг\w*\b",
            r"\bваши\b.*\bкниг\w*\b",
            r"\bваше\b.*\bтворчеств\w*\b",
            r"\bполучить\b.*\bкниг\w*\b",
            r"\bблагодар\w*\b.*\bкниг\w*\b",

            # Общие запросы
            r"\bчто\b.*\bпочит\w*\b",
            r"\bкакую\b.*\bкниг\w*\b",
            r"\bкакие\b.*\bкниг\w*\b",
            r"\bесть\b.*\bкниг\w*\b",
            r"\bнайти\b.*\bкниг\w*\b",
            r"\bищу\b.*\bкниг\w*\b",
        ]

        self.pattern = re.compile("|".join(self.triggers), re.IGNORECASE)

    def check_text(self, text: str) -> bool:
        """Проверка текста на наличие триггеров"""
        if not text:
            return False
        return bool(self.pattern.search(text))


trigger_manager = TriggerManager()


async def handle_message(message: Message) -> None:
    """Обработчик всех сообщений в группе"""
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
        reply_markup=await get_trigger_button()
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
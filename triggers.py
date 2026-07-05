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
            # === ОСНОВНЫЕ СЛОВА ===
            r"\bкниг\w*\b",
            r"\bкниж\w*\b",
            r"\bпроизведени\w*\b",
            r"\bтворчеств\w*\b",

            # === ЧИТАТЬ / ПОЧИТАТЬ ===
            r"\bпочита\w*\b",
            r"\bчитать\w*\b",
            r"\bчита\w*\b",

            # === ПОСОВЕТОВАТЬ / РЕКОМЕНДОВАТЬ ===
            r"\bпосовет\w*\b",
            r"\bрекоменду\w*\b",

            # === ПОЛУЧИТЬ КНИГУ ===
            r"\bпришл\w*\b.*\bкниг\w*\b",
            r"\bполуч\w*\b.*\bкниг\w*\b",
            r"\bдай\w*\b.*\bкниг\w*\b",
            r"\bможно\b.*\bкниг\w*\b",
            r"\bхочу\b.*\bкниг\w*\b",
            r"\bполучить\b.*\bкниг\w*\b",

            # === ПРОИЗВЕДЕНИЕ ===
            r"\bможно\b.*\bпроизведени\w*",
            r"\bхочу\b.*\bпроизведени\w*",
            r"\bпришл\w*\b.*\bпроизведени\w*",
            r"\bпочита\w*\b.*\bпроизведени\w*",
            r"\bознаком\w*\b.*\bпроизведени\w*",
            r"\bознаком\w*\b.*\bкниг\w*",
            r"\bваш\w*\b.*\bпроизведени\w*",
            r"\bваш\w*\b.*\bкниг\w*",

            # === ИНТЕРЕС / ТВОРЧЕСТВО ===
            r"\bинтерес\w*\b.*\bтворчеств\w*\b",
            r"\bинтерес\w*\b.*\bкниг\w*",
            r"\bинтерес\w*\b.*\bпроизведени\w*",
            r"\bваш\w*\b.*\bтворчеств\w*",

            # === ОБЩИЕ ЗАПРОСЫ ===
            r"\bчто\b.*\bпочит\w*\b",
            r"\bкакую\b.*\bкниг\w*\b",
            r"\bкакие\b.*\bкниг\w*\b",
            r"\bесть\b.*\bкниг\w*\b",
            r"\bнайти\b.*\bкниг\w*\b",
            r"\bищу\b.*\bкниг\w*\b",

            # === ХОЧУ / МОГУ ПОЧИТАТЬ ===
            r"\bможно\b.*\bпочита\w*",
            r"\bмогу\b.*\bпочита\w*",
            r"\bхочу\b.*\bпочита\w*",

            # === ВЕЖЛИВЫЕ ПРОСЬБЫ (ТОЛЬКО С КНИГОЙ) ===
            r"\bможно\b.*\bпочита\w*.*\bваш\w*.*\b(книг\w*|произведени\w*)",
            r"\bхочу\b.*\bпочита\w*.*\bваш\w*.*\b(книг\w*|произведени\w*)",
            r"\bбуду\b.*\bблагодар\w*.*\bпришл\w*.*\b(книг\w*|произведени\w*)",
            r"\bинтересно\b.*\bчто\b.*\bпиш\w*.*\bкниг\w*",

            # === УВИДЕЛ (ТОЛЬКО С КНИГОЙ) ===
            r"\bувидел\w*\b.*\bтик\s*ток\w*.*\bпочита\w*.*\bкниг\w*",
            r"\bувидел\w*\b.*\bролик\w*.*\bпочита\w*.*\bкниг\w*",
            r"\bпервый\b.*\bувидел\w*.*\bкниг\w*",
        ]

        self.pattern = re.compile("|".join(self.triggers), re.IGNORECASE)

    def check_text(self, text: str) -> bool:
        if not text:
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
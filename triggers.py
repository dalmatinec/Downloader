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
            # === КНИГА (основное слово) ===
            r"\bкниг\w*\b",
            r"\bкниж\w*\b",

            # === ПРОИЗВЕДЕНИЕ ===
            r"\bпроизведени\w*\b",

            # === ЧИТАТЬ / ПОЧИТАТЬ ===
            r"\bпочита\w*\b",
            r"\bчитать\w*\b",
            r"\bчита\w*\b",

            # === ПОСОВЕТОВАТЬ / РЕКОМЕНДОВАТЬ ===
            r"\bпосовет\w*\b",
            r"\bрекоменду\w*\b",

            # === ВЗЯТЬ / ПОЛУЧИТЬ / ПРИСЛАТЬ / СКИНУТЬ ===
            r"\bпришл\w*\b.*\bкниг\w*\b",
            r"\bполуч\w*\b.*\bкниг\w*\b",
            r"\bдай\w*\b.*\bкниг\w*\b",
            r"\bвзят\w*\b.*\bкниг\w*\b",
            r"\bскин\w*\b.*\bкниг\w*\b",
            r"\bотправ\w*\b.*\bкниг\w*\b",
            r"\bподели\w*\b.*\bкниг\w*\b",

            # === МОЖНО / ХОЧУ С КНИГОЙ ===
            r"\bможно\b.*\bкниг\w*",
            r"\bхочу\b.*\bкниг\w*",
            r"\bможно\b.*\bпроизведени\w*",
            r"\bхочу\b.*\bпроизведени\w*",

            # === ВАШ / ВАШИ С КНИГОЙ ===
            r"\bваш\w*\b.*\bкниг\w*",
            r"\bваш\w*\b.*\bпроизведени\w*",

            # === ИНТЕРЕСНО + КНИГА / ПРОИЗВЕДЕНИЕ ===
            r"\bинтерес\w*\b.*\bкниг\w*",
            r"\bинтерес\w*\b.*\bпроизведени\w*",

            # === ВОПРОСЫ ГДЕ / КАК / КАКУЮ / КАКИЕ ===
            r"\bгде\b.*\bкниг\w*",
            r"\bкак\b.*\bкниг\w*",
            r"\bкакую\b.*\bкниг\w*",
            r"\bкакие\b.*\bкниг\w*",

            # === ЧТО ПОЧИТАТЬ / ЕСТЬ КНИГИ / ИЩУ ===
            r"\bчто\b.*\bпочита\w*",
            r"\bесть\b.*\bкниг\w*",
            r"\bнайти\b.*\bкниг\w*",
            r"\bищу\b.*\bкниг\w*",

            # === ОЗНАКОМИТЬСЯ ===
            r"\bознаком\w*\b.*\bкниг\w*",
            r"\bознаком\w*\b.*\bпроизведени\w*",

            # === ТВОРЧЕСТВО (ТОЛЬКО С ДЕЙСТВИЕМ) ===
            r"\bинтерес\w*\b.*\bтворчеств\w*",
            r"\bваш\w*\b.*\bтворчеств\w*",
            r"\bознаком\w*\b.*\bтворчеств\w*",
            r"\bпочита\w*\b.*\bтворчеств\w*",

            # === ВЕЖЛИВЫЕ ПРОСЬБЫ (ТОЛЬКО С КНИГОЙ ИЛИ ПРОИЗВЕДЕНИЕМ) ===
            r"\bможно\b.*\bпочита\w*.*\bваш\w*.*\b(книг\w*|произведени\w*)",
            r"\bхочу\b.*\bпочита\w*.*\bваш\w*.*\b(книг\w*|произведени\w*)",
            r"\bбуду\b.*\bблагодар\w*.*\bпришл\w*.*\b(книг\w*|произведени\w*)",
            r"\bинтересно\b.*\bчто\b.*\bпиш\w*.*\bкниг\w*",
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
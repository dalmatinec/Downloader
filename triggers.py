import re
import logging
from typing import Optional

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
            # Слова "книга" в разных падежах
            r'\bкниг[ауиейойе]?\b',
            r'\bкнижк[аиуе]?\b',
            r'\bкнижн[а-я]*\b',
            
            # Английские варианты
            r'\bbook\b',
            r'\bbooks\b',
            
            # Фразы с книгой
            r'посоветуй(?:те)?\s+книгу',
            r'как(?:ую)?\s+книг[уи]',
            r'какие\s+книги',
            r'где\s+взять\s+книгу',
            r'где\s+найти\s+книгу',
            r'где\s+почитать',
            r'что\s+почитать',
            r'что\s+можно\s+почитать',
            r'какую\s+книгу\s+почитать',
            r'какую\s+книгу\s+посоветуешь',
            r'какую\s+книгу\s+посоветуете',
            r'есть\s+книг[аи]',
            r'есть\s+книги',
            r'почитать\s+книгу',
            r'почитать\s+книги',
            r'найти\s+книгу',
            r'найти\s+книги'
        ]
        self.pattern = re.compile('|'.join(self.triggers), re.IGNORECASE)

    def check_text(self, text: str) -> bool:
        """Проверка текста на наличие триггеров"""
        if not text:
            return False
        return bool(self.pattern.search(text))


trigger_manager = TriggerManager()


async def handle_message(message: Message) -> None:
    """Обработчик всех сообщений в чате"""
    if not message.text:
        return

    if message.from_user.is_bot:
        return

    if message.text.startswith('/'):
        return

    if not trigger_manager.check_text(message.text):
        return

    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.TRIGGER_RESPONSE_TEXT,
        reply_markup=await get_trigger_button()
    )


async def get_trigger_button():
    """Кнопка для открытия бота"""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=texts.TRIGGER_BUTTON_TEXT,
        url=f"https://t.me/{config.BOT_USERNAME.replace('@', '')}"
    )
    return builder.as_markup()


def register_trigger_handlers(dp: Dispatcher) -> None:
    """Регистрация обработчика триггеров"""
    dp.message.register(handle_message)
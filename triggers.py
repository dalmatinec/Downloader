import re
import logging
from typing import Optional, List, Dict, Any

from aiogram import Dispatcher, F
from aiogram.types import Message

from database import Database
from utils import safe_send_message, log_action


logger = logging.getLogger(__name__)
db = Database()


class TriggerManager:
    def __init__(self):
        self.triggers_cache: List[Dict[str, Any]] = []

    async def refresh_cache(self) -> None:
        """Обновление кэша триггеров"""
        self.triggers_cache = await db.get_all_triggers()
        logger.info(f"Triggers cache refreshed: {len(self.triggers_cache)} triggers loaded")

    async def check_message(self, text: str) -> Optional[str]:
        """Проверка сообщения на наличие триггеров"""
        if not text:
            return None

        # Автозагрузка, если кэш пустой
        if not self.triggers_cache:
            await self.refresh_cache()
            if not self.triggers_cache:
                return None

        text_lower = text.lower()

        for trigger in self.triggers_cache:
            keywords = [kw.strip().lower() for kw in trigger['keywords'].split(',')]
            for keyword in keywords:
                pattern = rf'\b{re.escape(keyword)}\b'
                if re.search(pattern, text_lower):
                    logger.info(f"Trigger matched: '{keyword}' in text: '{text[:50]}...'")
                    return trigger['action']

        return None


trigger_manager = TriggerManager()


async def handle_message(message: Message) -> None:
    """Обработчик всех сообщений в чате для триггеров"""
    if not message.text:
        return

    if message.from_user.is_bot:
        return

    if message.text.startswith('/'):
        return

    response = await trigger_manager.check_message(message.text)
    if response:
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text=response,
            reply_to_message_id=message.message_id
        )
        await log_action(
            user_id=message.from_user.id,
            action="trigger_fired",
            details=f"Trigger: {response[:50]}..."
        )


def register_trigger_handlers(dp: Dispatcher) -> None:
    """Регистрация обработчика триггеров"""
    dp.message.register(handle_message)


async def refresh_triggers_cache() -> None:
    """Внешняя функция для обновления кэша из admin.py"""
    await trigger_manager.refresh_cache()
import logging  # 1. Импорт
from aiogram import Router, F
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
import texts
from triggers import trigger_manager
from utils import safe_send_message

logger = logging.getLogger(__name__)  # 2. Инициализация логгера
router = Router()

async def get_trigger_button():
    builder = InlineKeyboardBuilder()
    builder.button(
        text=texts.TRIGGER_BUTTON_TEXT,
        url=f"https://t.me/{config.BOT_USERNAME.replace('@', '')}"
    )
    return builder.as_markup()

@router.message(F.text.regexp(trigger_manager.pattern))
async def handle_trigger(message: Message) -> None:
    if message.from_user.is_bot or (message.text and message.text.startswith('/')):
        return

    # 3. Логируем срабатывание
    logger.info(f"Сработал триггер для пользователя {message.from_user.id}: {message.text[:30]}")

    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.TRIGGER_RESPONSE_TEXT,
        reply_markup=await get_trigger_button(),
        reply_to_message_id=message.message_id  # 4. Ответ реплаем
    )
from aiogram import Router, F
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
import texts
from triggers import trigger_manager
from utils import safe_send_message


router = Router()


async def get_trigger_button():
    """Кнопка для открытия бота"""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=texts.TRIGGER_BUTTON_TEXT,
        url=f"https://t.me/{config.BOT_USERNAME.replace('@', '')}"
    )
    return builder.as_markup()


@router.message(F.text.regexp(trigger_manager.pattern))
async def handle_trigger(message: Message) -> None:
    """Обработчик триггеров на книги"""
    if message.from_user.is_bot:
        return
    
    if message.text.startswith('/'):
        return
    
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.TRIGGER_RESPONSE_TEXT,
        reply_markup=await get_trigger_button()
    )
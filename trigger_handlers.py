from aiogram import Router, F
from aiogram.types import Message
import texts
import config
from triggers import trigger_manager, get_trigger_button
from utils import safe_send_message

router = Router()

@router.message(
    F.chat.type.in_({"group", "supergroup"}),
    F.text.regexp(trigger_manager.pattern)
)
async def trigger_handler(message: Message):
    # Если мы попали сюда — значит триггер сработал. 
    # После этого ИИ уже не будет дергаться, так как мы вернули ответ.
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.TRIGGER_RESPONSE_TEXT,
        reply_markup=await get_trigger_button()
    )

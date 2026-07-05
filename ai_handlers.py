from aiogram import Router, F
from aiogram.types import Message
from triggers import trigger_manager

from ai import (
    handle_kesha_mention,
    handle_book_keywords,
    handle_all_messages
)

router = Router()

@router.message(F.chat.type.in_({"group", "supergroup"}))
async def ai_router_handler(message: Message):
    """Единый обработчик AI для групп с приоритетами"""

    # 1. Приоритет: упоминание Кеши
    if await handle_kesha_mention(message):
        return

    # 2. Если это триггер (слова-кнопки), ИИ молчит, чтобы сработал trigger_handlers
    if message.text and trigger_manager.check_text(message.text):
        return 

    # 3. Если это обычный запрос про книги (не триггер), ИИ отвечает
    if await handle_book_keywords(message):
        return


    # 5. Сохранение сообщений
    await handle_all_messages(message)

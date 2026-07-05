from aiogram import Router, F
from aiogram.types import Message
from triggers import trigger_manager

from ai import (
    handle_reply_to_kesha,
    handle_kesha_mention,
    handle_book_keywords,
    handle_all_messages,
)

router = Router()


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def ai_router_handler(message: Message):
    """Единый обработчик AI"""

    # 1. Ответ на сообщение Кеши (Reply)
    if await handle_reply_to_kesha(message):
        return

    # 2. Упоминание Кеши
    if await handle_kesha_mention(message):
        return

    # 3. Если это триггер — ИИ молчит
    if message.text and trigger_manager.check_text(message.text):
        return

    # 4. Вопросы про книги
    if await handle_book_keywords(message):
        return

    # 5. Сохраняем историю сообщений
    await handle_all_messages(message)
from aiogram import Router, F
from aiogram.types import Message

from ai import (
    handle_kesha_mention,
    handle_book_keywords,
    handle_video_announcement,
    handle_all_messages
)


router = Router()


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def ai_router_handler(message: Message):
    """Единый обработчик AI для групп с приоритетами"""
    
    # Приоритет 1: упоминание Кеши (самый важный)
    if await handle_kesha_mention(message):
        return
    
    # Приоритет 2: ключевые слова про книги
    if await handle_book_keywords(message):
        return
    
    # Приоритет 3: новое видео в канале
    if await handle_video_announcement(message):
        return
    
    # Приоритет 4: сохранение всех сообщений в историю (всегда в конце)
    await handle_all_messages(message)
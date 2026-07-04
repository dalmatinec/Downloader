from aiogram import Router, F
from aiogram.types import Message
import ai

router = Router()

# Этот роутер будет идти ПОСЛЕДНИМ в main.py
@router.message(F.text & ~F.text.startswith("/"))
async def handle_ai_messages(message: Message):
    # 1. Сначала записываем контекст (всегда)
    await ai.handle_all_messages(message)
    
    # 2. Если упоминают Кешу — отвечаем
    await ai.handle_kesha_mention(message)
    
    # 3. Если видео с канала — реагируем
    await ai.handle_video_announcement(message)

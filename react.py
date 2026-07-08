import random
import logging
from aiogram import Router
from aiogram.types import Message, ReactionTypeEmoji
from aiogram.filters import BaseFilter

logger = logging.getLogger(__name__)
router = Router()

# Слова для реакции
REACT_WORDS = [
    "спасибо", "благодарю", "благодарен", "благодарна",
    "здравствуйте", "добрый день", "доброе утро", "добрый вечер", "доброй ночи",
    "приятного аппетита",
    "еда", "кушать", "поесть", "обед", "ужин", "завтрак",
    "кот", "котик", "кошка", "кошки", "мур", "мяу"
]

REACTION = "❤️"


class ReactManager:
    def __init__(self):
        self.keywords = REACT_WORDS

    def check_text(self, text: str) -> bool:
        if not text or len(text.strip()) < 3:
            return False
        
        text_lower = text.lower()
        for word in self.keywords:
            if word in text_lower:
                return True
        return False


react_manager = ReactManager()


class ReactFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False
        if message.chat.type not in {"group", "supergroup"}:
            return False
        if "кеша" in message.text.lower():
            return False
        if message.reply_to_message and message.reply_to_message.from_user.id == message.bot.id:
            return False
        
        return react_manager.check_text(message.text)


# ВНЕШНИЙ ОБРАБОТЧИК — срабатывает до всех роутеров
@router.message(ReactFilter())
async def handle_react(message: Message) -> None:
    logger.info("REACT HANDLER")
    
    try:
        await message.react(
            reaction=[ReactionTypeEmoji(emoji=REACTION)]
        )
        logger.info(f"Поставлена реакция {REACTION} пользователю {message.from_user.id}")
    except Exception as e:
        logger.error(f"Не удалось поставить реакцию: {e}")
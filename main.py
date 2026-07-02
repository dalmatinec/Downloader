import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config
from database import Database
from users import register_user_handlers
from admin import register_admin_handlers
from triggers import refresh_triggers_cache, register_trigger_handlers
from send import register_broadcast_handlers
from moderation import register_moderation_handlers
from scheduler import start_scheduler


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    logger.info("🐱 Запускаем Кешу...")
    
    # Инициализация БД
    db = Database()
    await db.init_db()
    logger.info("✅ База данных готова")
    
    # Обновление кэша триггеров
    await refresh_triggers_cache()
    logger.info("✅ Кэш триггеров загружен")
    
    # Инициализация бота
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Регистрация всех обработчиков
    register_user_handlers(dp)
    register_admin_handlers(dp)
    register_trigger_handlers(dp)
    register_broadcast_handlers(dp)
    register_moderation_handlers(dp)
    logger.info("✅ Все обработчики зарегистрированы")
    
    # Запуск планировщика в фоне
    asyncio.create_task(start_scheduler(bot))
    logger.info("✅ Планировщик запущен")
    
    # Запуск бота
    logger.info("✅ Кеша готов к работе!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
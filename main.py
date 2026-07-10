import asyncio
import logging
import sys

from ai import ai_loop, ai_auto_message
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.fsm.storage.memory import MemoryStorage

import config
from database import Database

# Импорты роутеров
from admin_handlers import router as admin_router
from user_handlers import router as user_router
from trigger_handlers import router as trigger_router
from ai_handlers import router as ai_router
from react import router as react_router
from setting_handlers import router as settings_router


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def set_bot_commands(bot: Bot) -> None:
    """Установка команд для меню бота"""
    commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="cancel", description="Отмена действия"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())


async def main() -> None:
    """Главная функция запуска бота"""
    logger.info("🐱 Запускаем бота Кеша...")

    # Инициализация базы данных
    db = Database()
    await db.init_db()
    logger.info("✅ База данных готова")

    # Создание бота и диспетчера
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Подключение роутеров
    dp.include_router(trigger_router)
    dp.include_router(admin_router)
    dp.include_router(user_router)
    dp.include_router(ai_router)
    dp.include_router(react_router)
    dp.include_router(settings_router)
    logger.info("✅ Все роутеры подключены")

    # Установка команд
    await set_bot_commands(bot)
    logger.info("✅ Команды бота установлены")

    # Запуск AI-цикла каждые 2 часа
    asyncio.create_task(ai_loop(bot))
    logger.info("✅ AI-цикл запущен")

    # Запуск поллинга
    logger.info("✅ Бот готов к работе!")

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")
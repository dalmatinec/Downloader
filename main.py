import asyncio
import logging
import sys

from ai import ai_loop
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.fsm.storage.memory import MemoryStorage

import config
from database import Database
from handlers import register_handlers
from triggers import register_trigger_handlers


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

    # Установка команд
    await set_bot_commands(bot)
    logger.info("✅ Команды бота установлены")

    # Регистрация всех обработчиков
    register_handlers(dp)
    register_trigger_handlers(dp)
    logger.info("✅ Все обработчики зарегистрированы")

    # Запуск AI-цикла в фоне
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
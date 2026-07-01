# main.py
import logging
import sqlite3
from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from config import BOT_TOKEN, DATABASE_PATH
from database import Database
from admin import AdminPanel
from handlers import Handlers
from callbacks import Callbacks


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Точка входа"""
    
    # Инициализация БД
    db = Database(DATABASE_PATH)
    logger.info("База данных инициализирована")
    
    # Инициализация бота
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(bot, storage=storage)
    logger.info("Бот и диспетчер инициализированы")
    
    # Проверка наличия сообщества при старте
    # Если нет - создаем дефолтное для админа (но админ сам создаст через админку)
    admin_panel = AdminPanel(db)
    
    # Проверяем есть ли хоть одно сообщество
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM communities')
        count = cursor.fetchone()[0]
        
        if count == 0:
            logger.info("Сообществ нет. Будет создано при первом входе администратора.")
    
    # Регистрация обработчиков
    handlers = Handlers(dp, db)
    handlers.register()
    logger.info("Handlers зарегистрированы")
    
    # Регистрация callback-обработчиков
    callbacks = Callbacks(dp, db)
    callbacks.register()
    logger.info("Callbacks зарегистрированы")
    
    # Запуск бота
    logger.info("Бот запущен")
    executor.start_polling(dp, skip_updates=True)


if __name__ == '__main__':
    main()
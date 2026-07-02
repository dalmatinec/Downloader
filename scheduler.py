import asyncio
import logging
from datetime import datetime

from aiogram import Bot
from aiogram.types import ChatPermissions

from database import Database
from utils import safe_send_message, log_action
import config


logger = logging.getLogger(__name__)
db = Database()


async def check_mutes(bot: Bot) -> None:
    """Проверка и автоматический размут пользователей"""
    try:
        muted_users = await db.get_muted_users()

        for user_data in muted_users:
            punishments = await db.get_active_punishments(user_data['id'])
            for p in punishments:
                if p['type'] == 'mute' and p['end_time']:
                    end_time = datetime.fromisoformat(p['end_time'])
                    if datetime.now() >= end_time:
                        await bot.restrict_chat_member(
                            chat_id=config.CHAT_ID,
                            user_id=user_data['telegram_id'],
                            permissions=ChatPermissions(
                                can_send_messages=True,
                                can_send_media_messages=True,
                                can_send_other_messages=True,
                                can_add_web_page_previews=True
                            )
                        )
                        await db.set_user_muted(user_data['telegram_id'], False)
                        await log_action(
                            user_id=user_data['telegram_id'],
                            action="auto_unmute",
                            details=f"Auto unmuted after {p['reason']}"
                        )
                        await safe_send_message(
                            bot=bot,
                            chat_id=user_data['telegram_id'],
                            text="🔊 Твой мут автоматически снят! Добро пожаловать обратно."
                        )
                        logger.info(f"Auto unmuted user {user_data['telegram_id']}")
    except Exception as e:
        logger.exception(f"check_mutes error: {e}")


async def ai_auto_message(bot: Bot) -> None:
    """Отправка автоматического сообщения от AI в чат"""
    try:
        # Заглушка. Позже здесь будет вызов ai.generate_chat_message()
        pass
    except Exception as e:
        logger.exception(f"ai_auto_message error: {e}")


async def scheduler(bot: Bot) -> None:
    """Фоновый планировщик задач"""
    logger.info("Scheduler started")

    while True:
        try:
            await check_mutes(bot)
            # await ai_auto_message(bot)
            await asyncio.sleep(60)
        except Exception as e:
            logger.exception(f"Scheduler error: {e}")
            await asyncio.sleep(60)


async def start_scheduler(bot: Bot) -> None:
    """Запуск планировщика в фоновом режиме"""
    await scheduler(bot)
import logging
from datetime import datetime, timedelta

from aiogram import Dispatcher, F
from aiogram.types import Message, ChatPermissions
from aiogram.filters import Command

from database import Database
from utils import is_admin, log_action, safe_send_message, parse_duration, format_duration, get_user_link
import texts


logger = logging.getLogger(__name__)
db = Database()


async def get_target_user(message: Message) -> tuple:
    """Получить пользователя из реплая"""
    if not message.reply_to_message:
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text="⚠️ Ответь на сообщение пользователя, чтобы применить действие."
        )
        return None, None
    
    target = message.reply_to_message.from_user
    if target.is_bot:
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text="🤖 Нельзя применять действия к боту."
        )
        return None, None
    
    return target, target.id


async def warn_command(message: Message) -> None:
    """Предупреждение через реплай (/warn)"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    
    target, target_id = await get_target_user(message)
    if not target:
        return
    
    reason = message.text.replace('/warn', '').strip() or "Без причины"
    
    # Получаем пользователя из БД
    target_data = await db.get_user_by_telegram_id(target_id)
    if not target_data:
        await safe_send_message(message.bot, message.chat.id, "❌ Пользователь не найден в базе")
        return
    
    new_warn_count = target_data['warn_count'] + 1
    await db.update_user_warn_count(target_id, new_warn_count)
    await db.add_punishment(
        user_id=target_data['id'],
        p_type="warning",
        reason=reason,
        issued_by=user.id
    )
    
    await log_action(user.id, "moderation_warn", f"Warned user {target_id} (count: {new_warn_count})")
    
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.WARN_MESSAGES.format(
            user_id=get_user_link(target_id, target.username, target.first_name),
            count=new_warn_count,
            reason=reason
        )
    )


async def mute_command(message: Message) -> None:
    """Мут через реплай (/mute [время])"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    
    target, target_id = await get_target_user(message)
    if not target:
        return
    
    # Парсим время
    parts = message.text.split()
    if len(parts) < 2:
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text="⚠️ Укажи время: /mute 1h, /mute 30m, /mute 7d"
        )
        return
    
    duration = parse_duration(parts[1])
    if duration == 0:
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text="⚠️ Неверный формат. Используй: 1h, 30m, 7d"
        )
        return
    
    reason = ' '.join(parts[2:]).strip() or "Без причины"
    
    target_data = await db.get_user_by_telegram_id(target_id)
    if not target_data:
        await safe_send_message(message.bot, message.chat.id, "❌ Пользователь не найден в базе")
        return
    
    # Мут в Telegram
    until_date = datetime.now() + timedelta(seconds=duration)
    await message.bot.restrict_chat_member(
        chat_id=message.chat.id,
        user_id=target_id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=until_date
    )
    
    # Сохраняем в БД
    await db.set_user_muted(target_id, True)
    end_time = until_date.isoformat()
    await db.add_punishment(
        user_id=target_data['id'],
        p_type="mute",
        reason=reason,
        issued_by=user.id,
        end_time=end_time
    )
    
    await log_action(user.id, "moderation_mute", f"Muted user {target_id} for {duration}s")
    
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.MUTE_MESSAGES.format(
            user_id=get_user_link(target_id, target.username, target.first_name),
            duration=format_duration(duration),
            reason=reason
        )
    )


async def unmute_command(message: Message) -> None:
    """Размут через реплай (/unmute)"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    
    target, target_id = await get_target_user(message)
    if not target:
        return
    
    target_data = await db.get_user_by_telegram_id(target_id)
    if not target_data:
        await safe_send_message(message.bot, message.chat.id, "❌ Пользователь не найден в базе")
        return
    
    # Размут в Telegram
    await message.bot.restrict_chat_member(
        chat_id=message.chat.id,
        user_id=target_id,
        permissions=ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
    )
    
    await db.set_user_muted(target_id, False)
    await log_action(user.id, "moderation_unmute", f"Unmuted user {target_id}")
    
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.UNMUTE_MESSAGES.format(
            user_id=get_user_link(target_id, target.username, target.first_name)
        )
    )


async def ban_command(message: Message) -> None:
    """Бан через реплай (/ban)"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    
    target, target_id = await get_target_user(message)
    if not target:
        return
    
    reason = message.text.replace('/ban', '').strip() or "Без причины"
    
    target_data = await db.get_user_by_telegram_id(target_id)
    if not target_data:
        await safe_send_message(message.bot, message.chat.id, "❌ Пользователь не найден в базе")
        return
    
    # Бан в Telegram
    await message.bot.ban_chat_member(
        chat_id=message.chat.id,
        user_id=target_id
    )
    
    await db.set_user_banned(target_id, True)
    await db.add_punishment(
        user_id=target_data['id'],
        p_type="ban",
        reason=reason,
        issued_by=user.id
    )
    
    await log_action(user.id, "moderation_ban", f"Banned user {target_id}")
    
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.BAN_MESSAGES.format(
            user_id=get_user_link(target_id, target.username, target.first_name)
        )
    )


async def unban_command(message: Message) -> None:
    """Разбан через реплай (/unban)"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    
    target, target_id = await get_target_user(message)
    if not target:
        return
    
    target_data = await db.get_user_by_telegram_id(target_id)
    if not target_data:
        await safe_send_message(message.bot, message.chat.id, "❌ Пользователь не найден в базе")
        return
    
    # Разбан в Telegram
    await message.bot.unban_chat_member(
        chat_id=message.chat.id,
        user_id=target_id
    )
    
    await db.set_user_banned(target_id, False)
    await log_action(user.id, "moderation_unban", f"Unbanned user {target_id}")
    
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.UNBAN_MESSAGES.format(
            user_id=get_user_link(target_id, target.username, target.first_name)
        )
    )


async def history_command(message: Message) -> None:
    """История наказаний через реплай (/history)"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    
    target, target_id = await get_target_user(message)
    if not target:
        return
    
    target_data = await db.get_user_by_telegram_id(target_id)
    if not target_data:
        await safe_send_message(message.bot, message.chat.id, "❌ Пользователь не найден в базе")
        return
    
    punishments = await db.get_punishment_history(target_data['id'])
    if not punishments:
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text=f"📄 У пользователя нет наказаний"
        )
        return
    
    text = f"📄 История наказаний для {get_user_link(target_id, target.username, target.first_name)}:\n\n"
    for p in punishments[:20]:
        text += f"• {p['type']} — {p['reason'] or 'Без причины'} ({p['start_time']})\n"
    
    await log_action(user.id, "moderation_history", f"Viewed history for {target_id}")
    await safe_send_message(message.bot, message.chat.id, text)


def register_moderation_handlers(dp: Dispatcher) -> None:
    """Регистрация команд модерации в чате"""
    
    dp.message.register(warn_command, Command("warn"))
    dp.message.register(mute_command, Command("mute"))
    dp.message.register(unmute_command, Command("unmute"))
    dp.message.register(ban_command, Command("ban"))
    dp.message.register(unban_command, Command("unban"))
    dp.message.register(history_command, Command("history"))
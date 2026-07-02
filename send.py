import asyncio
import logging
import aiosqlite

from aiogram import Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

import config
from database import Database
from keyboards import (
    get_admin_broadcast_kb,
    get_cancel_kb,
    get_confirm_kb,
    get_admin_main_kb
)
from states import BroadcastStates
from utils import (
    is_admin,
    log_action,
    safe_send_message,
    safe_edit_message,
    safe_delete_message,
    escape_html
)
import texts


logger = logging.getLogger(__name__)
db = Database()


async def admin_broadcast_menu(callback: CallbackQuery) -> None:
    """Меню рассылок"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await log_action(user.id, "admin_broadcast_menu", "Opened broadcast")
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.BROADCAST_MENU,
        reply_markup=get_admin_broadcast_kb()
    )
    await callback.answer()


async def admin_broadcast_manual_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало обычной рассылки"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await state.update_data(action="manual")
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.BROADCAST_ENTER_TEXT,
        reply_markup=get_cancel_kb()
    )
    await state.set_state(BroadcastStates.waiting_text)
    await callback.answer()


async def admin_broadcast_forward_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало пересылки сообщения"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await state.update_data(action="forward")
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.BROADCAST_FORWARD,
        reply_markup=get_cancel_kb()
    )
    await state.set_state(BroadcastStates.waiting_forward_message)
    await callback.answer()


async def admin_broadcast_video(callback: CallbackQuery, state: FSMContext) -> None:
    """Новое видео (рассылка с шаблоном)"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.BROADCAST_START,
        reply_markup=None
    )
    
    # Получаем всех пользователей
    async with aiosqlite.connect(config.DB_NAME) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute("SELECT telegram_id FROM users")
        users = await cursor.fetchall()
    
    if not users:
        await safe_edit_message(
            bot=callback.bot,
            callback=callback,
            text=texts.BROADCAST_NO_USERS,
            reply_markup=get_admin_broadcast_kb()
        )
        await callback.answer()
        return
    
    sent = 0
    failed = 0
    video_text = texts.BROADCAST_VIDEO
    
    for user_data in users:
        try:
            await callback.bot.send_message(
                chat_id=user_data['telegram_id'],
                text=video_text,
                parse_mode="HTML"
            )
            sent += 1
        except Exception as e:
            failed += 1
            logger.exception(f"Video broadcast failed to {user_data['telegram_id']}: {e}")
        finally:
            await asyncio.sleep(0.5)
    
    await db.add_broadcast({
        'type': 'video',
        'text': video_text,
        'sent_count': sent,
        'failed_count': failed,
        'created_by': user.id
    })
    
    await log_action(user.id, "broadcast_video", f"Sent to {sent} users, failed: {failed}")
    await state.clear()
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.BROADCAST_FINISHED.format(sent=sent, failed=failed),
        reply_markup=get_admin_broadcast_kb()
    )
    await callback.answer()


async def admin_broadcast_forward_message(message: Message, state: FSMContext) -> None:
    """Получение пересланного сообщения"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    
    if not message.forward_from and not message.forward_from_chat:
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text=texts.BROADCAST_FORWARD_ERROR,
            reply_markup=get_cancel_kb()
        )
        return
    
    await state.update_data(
        forward_message_id=message.message_id,
        forward_chat_id=message.chat.id
    )
    
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.BROADCAST_CONFIRM,
        reply_markup=get_confirm_kb("broadcast_forward")
    )
    await state.set_state(BroadcastStates.waiting_confirm)


async def admin_broadcast_text(message: Message, state: FSMContext) -> None:
    """Получение текста для рассылки"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    
    await state.update_data(text=message.text)
    
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.BROADCAST_PREVIEW.format(text=escape_html(message.text)),
        reply_markup=get_confirm_kb("broadcast_manual")
    )
    await state.set_state(BroadcastStates.waiting_confirm)


async def admin_broadcast_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение рассылки"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    
    data = await state.get_data()
    action = data.get('action')
    
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.BROADCAST_START,
        reply_markup=None
    )
    
    # Получаем всех пользователей
    async with aiosqlite.connect(config.DB_NAME) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute("SELECT telegram_id FROM users")
        users = await cursor.fetchall()
    
    if not users:
        await safe_edit_message(
            bot=callback.bot,
            callback=callback,
            text=texts.BROADCAST_NO_USERS,
            reply_markup=get_admin_broadcast_kb()
        )
        await callback.answer()
        return
    
    sent = 0
    failed = 0
    
    if action == "manual":
        text = data.get('text')
        if not text:
            await safe_edit_message(
                bot=callback.bot,
                callback=callback,
                text=texts.BROADCAST_TEXT_NOT_FOUND,
                reply_markup=get_admin_broadcast_kb()
            )
            await callback.answer()
            return
        
        for user_data in users:
            try:
                await callback.bot.send_message(
                    chat_id=user_data['telegram_id'],
                    text=text,
                    parse_mode="HTML"
                )
                sent += 1
            except Exception as e:
                failed += 1
                logger.exception(f"Broadcast failed to {user_data['telegram_id']}: {e}")
            finally:
                await asyncio.sleep(0.5)
        
        await db.add_broadcast({
            'type': 'manual',
            'text': text,
            'sent_count': sent,
            'failed_count': failed,
            'created_by': user.id
        })
        
        await log_action(user.id, "broadcast_manual", f"Sent to {sent} users, failed: {failed}")
    
    elif action == "forward":
        forward_msg_id = data.get('forward_message_id')
        forward_chat_id = data.get('forward_chat_id')
        
        if not forward_msg_id or not forward_chat_id:
            await safe_edit_message(
                bot=callback.bot,
                callback=callback,
                text=texts.BROADCAST_MESSAGE_NOT_FOUND,
                reply_markup=get_admin_broadcast_kb()
            )
            await callback.answer()
            return
        
        for user_data in users:
            try:
                await callback.bot.forward_message(
                    chat_id=user_data['telegram_id'],
                    from_chat_id=forward_chat_id,
                    message_id=forward_msg_id
                )
                sent += 1
            except Exception as e:
                failed += 1
                logger.exception(f"Broadcast forward failed to {user_data['telegram_id']}: {e}")
            finally:
                await asyncio.sleep(0.5)
        
        await db.add_broadcast({
            'type': 'forward',
            'forward_message_id': forward_msg_id,
            'forward_chat_id': forward_chat_id,
            'sent_count': sent,
            'failed_count': failed,
            'created_by': user.id
        })
        
        await log_action(user.id, "broadcast_forward", f"Sent to {sent} users, failed: {failed}")
    
    await state.clear()
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.BROADCAST_FINISHED.format(sent=sent, failed=failed),
        reply_markup=get_admin_broadcast_kb()
    )
    await callback.answer()


async def admin_cancel_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена рассылки"""
    user = callback.from_user
    await state.clear()
    await log_action(user.id, "admin_cancel_broadcast", "Cancelled broadcast")
    await safe_delete_message(callback.bot, callback.message.chat.id, callback.message.message_id)
    await safe_send_message(
        bot=callback.bot,
        chat_id=callback.message.chat.id,
        text=texts.BROADCAST_CANCEL,
        reply_markup=get_admin_broadcast_kb()
    )
    await callback.answer()


def register_broadcast_handlers(dp: Dispatcher) -> None:
    """Регистрация всех обработчиков рассылок"""
    
    dp.callback_query.register(admin_broadcast_menu, F.data == "admin:broadcast")
    dp.callback_query.register(admin_broadcast_manual_start, F.data == "admin:broadcast:manual")
    dp.callback_query.register(admin_broadcast_forward_start, F.data == "admin:broadcast:forward")
    dp.callback_query.register(admin_broadcast_video, F.data == "admin:broadcast:video")
    dp.callback_query.register(admin_broadcast_confirm, F.data.startswith("confirm_broadcast"))
    dp.callback_query.register(admin_cancel_broadcast, F.data == "cancel")
    
    dp.message.register(admin_broadcast_text, StateFilter(BroadcastStates.waiting_text))
    dp.message.register(admin_broadcast_forward_message, StateFilter(BroadcastStates.waiting_forward_message))
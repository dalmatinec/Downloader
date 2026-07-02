import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from triggers import refresh_triggers_cache

from aiogram import Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

import config
from database import Database
from keyboards import (
    get_admin_main_kb,
    get_admin_books_kb,
    get_admin_admins_kb,
    get_admin_triggers_kb,
    get_admin_broadcast_kb,
    get_admin_stats_kb,
    get_admin_moderation_kb,
    get_admin_donators_kb,
    get_admin_logs_kb,
    get_cancel_kb,
    get_confirm_kb,
    get_books_kb
)
from states import (
    BookStates,
    AdminStates,
    TriggerStates,
    ModerationStates,
    DonatorStates,
    BroadcastStates
)
from utils import (
    is_admin,
    is_super_admin,
    log_action,
    safe_send_message,
    safe_edit_message,
    safe_delete_message,
    escape_html,
    format_duration,
    parse_duration,
    get_user_link
)
import texts


logger = logging.getLogger(__name__)
db = Database()


async def admin_command(message: Message) -> None:
    """Обработчик команды /admin"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    await log_action(user.id, "admin_command", "Opened admin panel")
    await safe_send_message(message.bot, message.chat.id, texts.ADMIN_MENU, reply_markup=get_admin_main_kb())


async def admin_menu(callback: CallbackQuery) -> None:
    """Возврат в главное меню админки"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await log_action(user.id, "admin_menu", "Returned to admin menu")
    await safe_edit_message(callback.bot, callback=callback, text=texts.ADMIN_MENU, reply_markup=get_admin_main_kb())
    await callback.answer()


# ============================================================
# УПРАВЛЕНИЕ КНИГАМИ
# ============================================================

async def admin_books_menu(callback: CallbackQuery) -> None:
    """Меню управления книгами"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await log_action(user.id, "admin_books_menu", "Opened books management")
    await safe_edit_message(callback.bot, callback=callback, text="📚 Управление книгами\n\nВыберите действие:", reply_markup=get_admin_books_kb())
    await callback.answer()


async def admin_book_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало добавления книги"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await log_action(user.id, "admin_book_add_start", "Started book adding")
    await safe_edit_message(callback.bot, callback=callback, text="📖 Добавление книги\n\nВведите название книги:", reply_markup=get_cancel_kb())
    await state.set_state(BookStates.waiting_title)
    await callback.answer()


async def admin_book_add_title(message: Message, state: FSMContext) -> None:
    """Получение названия книги"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    await state.update_data(title=message.text)
    await safe_send_message(message.bot, message.chat.id, "✍️ Введите автора книги:", reply_markup=get_cancel_kb())
    await state.set_state(BookStates.waiting_author)


async def admin_book_add_author(message: Message, state: FSMContext) -> None:
    """Получение автора книги"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    await state.update_data(author=message.text)
    await safe_send_message(message.bot, message.chat.id, "📝 Введите описание книги (можно пропустить, отправьте '-'):", reply_markup=get_cancel_kb())
    await state.set_state(BookStates.waiting_description)


async def admin_book_add_description(message: Message, state: FSMContext) -> None:
    """Получение описания книги"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    description = None if message.text == '-' else message.text
    await state.update_data(description=description)
    await safe_send_message(message.bot, message.chat.id, "🖼 Отправьте постер книги (изображение):", reply_markup=get_cancel_kb())
    await state.set_state(BookStates.waiting_poster)


async def admin_book_add_poster(message: Message, state: FSMContext) -> None:
    """Получение постера книги"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    if not message.photo:
        await safe_send_message(message.bot, message.chat.id, "❌ Пожалуйста, отправьте изображение:", reply_markup=get_cancel_kb())
        return
    await state.update_data(poster_file_id=message.photo[-1].file_id)
    await safe_send_message(message.bot, message.chat.id, "📄 Отправьте файл книги:", reply_markup=get_cancel_kb())
    await state.set_state(BookStates.waiting_file)


async def admin_book_add_file(message: Message, state: FSMContext) -> None:
    """Получение файла книги"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    if not message.document:
        await safe_send_message(message.bot, message.chat.id, "❌ Пожалуйста, отправьте файл:", reply_markup=get_cancel_kb())
        return
    data = await state.get_data()
    book_id = await db.add_book(
        title=data['title'],
        author=data['author'],
        description=data.get('description'),
        poster_file_id=data['poster_file_id'],
        book_file_id=message.document.file_id,
        file_type=message.document.mime_type
    )
    await log_action(user.id, "admin_book_add", f"Added book: {data['title']} (ID: {book_id})")
    await state.clear()
    await safe_send_message(message.bot, message.chat.id, texts.BOOK_ADDED.format(title=escape_html(data['title'])), reply_markup=get_admin_books_kb())


async def admin_book_list(callback: CallbackQuery) -> None:
    """Просмотр списка книг"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    books = await db.get_all_books()
    if not books:
        await safe_edit_message(callback.bot, callback=callback, text="📚 Книг пока нет", reply_markup=get_admin_books_kb())
        await callback.answer()
        return
    await log_action(user.id, "admin_book_list", f"Showing {len(books)} books")
    text = "📖 Список книг:\n\n"
    for book in books:
        text += f"• {escape_html(book['title'])} — {book['downloads']} скачиваний\n"
    await safe_edit_message(callback.bot, callback=callback, text=text, reply_markup=get_admin_books_kb())
    await callback.answer()


async def admin_book_delete_start(callback: CallbackQuery) -> None:
    """Начало удаления книги"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    books = await db.get_all_books()
    if not books:
        await callback.answer("📚 Книг пока нет")
        return
    await log_action(user.id, "admin_book_delete_start", "Started book deletion")
    await safe_edit_message(callback.bot, callback=callback, text="🗑 Выберите книгу для удаления:", reply_markup=get_books_kb(books))
    await callback.answer()


async def admin_book_delete_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение удаления книги"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    try:
        book_id = int(callback.data.split(":")[2])
    except (IndexError, ValueError):
        await callback.answer(texts.ERROR)
        return
    book = await db.get_book_by_id(book_id)
    if not book:
        await callback.answer(texts.BOOK_NOT_FOUND)
        return
    await state.update_data(delete_book_id=book_id)
    text = f"🗑 Вы уверены, что хотите удалить книгу?\n\n📖 {escape_html(book['title'])}\n✍️ {escape_html(book['author'])}"
    await safe_edit_message(callback.bot, callback=callback, text=text, reply_markup=get_confirm_kb("admin_book_delete"))
    await callback.answer()


async def admin_book_delete_execute(callback: CallbackQuery, state: FSMContext) -> None:
    """Выполнение удаления книги"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    data = await state.get_data()
    book_id = data.get('delete_book_id')
    if not book_id:
        await callback.answer("❌ Книга не найдена")
        return
    book = await db.get_book_by_id(book_id)
    if not book:
        await callback.answer(texts.BOOK_NOT_FOUND)
        return
    await db.delete_book(book_id)
    await log_action(user.id, "admin_book_delete", f"Deleted book: {book['title']} (ID: {book_id})")
    await state.clear()
    await safe_edit_message(callback.bot, callback=callback, text=texts.BOOK_DELETED.format(title=escape_html(book['title'])), reply_markup=get_admin_books_kb())
    await callback.answer()

# ============================================================
# УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ
# ============================================================

async def admin_admins_menu(callback: CallbackQuery) -> None:
    """Меню управления администраторами"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    if not is_super_admin(user.id):
        await callback.answer("⛔ Только супер-администратор может управлять админами")
        return
    admins = await db.get_all_admins()
    text = "👤 Администраторы:\n\n"
    if admins:
        for admin in admins:
            text += f"• {admin['telegram_id']}\n"
    else:
        text += "Нет добавленных администраторов\n"
    await log_action(user.id, "admin_admins_menu", f"Showing {len(admins)} admins")
    await safe_edit_message(callback.bot, callback=callback, text=text, reply_markup=get_admin_admins_kb())
    await callback.answer()


async def admin_admin_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало добавления администратора"""
    user = callback.from_user
    if not await is_admin(user.id) or not is_super_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await state.update_data(action="admin_add")
    await safe_edit_message(callback.bot, callback=callback, text="➕ Добавление администратора\n\nВведите Telegram ID пользователя:", reply_markup=get_cancel_kb())
    await state.set_state(AdminStates.waiting_admin_id)
    await callback.answer()


async def admin_admin_remove_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало удаления администратора"""
    user = callback.from_user
    if not await is_admin(user.id) or not is_super_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    admins = await db.get_all_admins()
    if not admins:
        await callback.answer("Нет администраторов для удаления")
        return
    await state.update_data(action="admin_remove")
    text = "➖ Удаление администратора\n\nВведите Telegram ID для удаления:\n"
    for admin in admins:
        text += f"• {admin['telegram_id']}\n"
    await safe_edit_message(callback.bot, callback=callback, text=text, reply_markup=get_cancel_kb())
    await state.set_state(AdminStates.waiting_admin_id)
    await callback.answer()


async def admin_admin_handle_id(message: Message, state: FSMContext) -> None:
    """Обработка ID для администраторов (добавление или удаление)"""
    user = message.from_user
    if not await is_admin(user.id) or not is_super_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    
    data = await state.get_data()
    action = data.get('action')
    
    try:
        admin_id = int(message.text.strip())
    except ValueError:
        await safe_send_message(message.bot, message.chat.id, "❌ Введите корректный Telegram ID (только цифры):", reply_markup=get_cancel_kb())
        return
    
    if action == "admin_add":
        existing = await db.get_admin_by_telegram_id(admin_id)
        if existing:
            await safe_send_message(message.bot, message.chat.id, "❌ Этот пользователь уже администратор", reply_markup=get_admin_admins_kb())
            await state.clear()
            return
        await db.add_admin(admin_id)
        await log_action(user.id, "admin_add", f"Added admin: {admin_id}")
        await state.clear()
        await safe_send_message(message.bot, message.chat.id, texts.ADMIN_ADDED, reply_markup=get_admin_admins_kb())
    
    elif action == "admin_remove":
        if admin_id == user.id:
            await safe_send_message(message.bot, message.chat.id, "❌ Нельзя удалить самого себя", reply_markup=get_cancel_kb())
            return
        if admin_id == config.SUPER_ADMIN_ID:
            await safe_send_message(message.bot, message.chat.id, "❌ Нельзя удалить супер-администратора", reply_markup=get_cancel_kb())
            return
        existing = await db.get_admin_by_telegram_id(admin_id)
        if not existing:
            await safe_send_message(message.bot, message.chat.id, "❌ Этот пользователь не является администратором", reply_markup=get_cancel_kb())
            await state.clear()
            return
        await db.remove_admin(admin_id)
        await log_action(user.id, "admin_remove", f"Removed admin: {admin_id}")
        await state.clear()
        await safe_send_message(message.bot, message.chat.id, texts.ADMIN_REMOVED, reply_markup=get_admin_admins_kb())

# ============================================================
# УПРАВЛЕНИЕ ТРИГГЕРАМИ
# ============================================================

async def admin_triggers_menu(callback: CallbackQuery) -> None:
    """Меню управления триггерами"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await log_action(user.id, "admin_triggers_menu", "Opened triggers management")
    await safe_edit_message(callback.bot, callback=callback, text="⚡ Управление триггерами\n\nВыберите действие:", reply_markup=get_admin_triggers_kb())
    await callback.answer()


async def admin_trigger_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало добавления триггера"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await safe_edit_message(callback.bot, callback=callback, text="➕ Добавление триггера\n\nВведите ключевые слова (через запятую):", reply_markup=get_cancel_kb())
    await state.set_state(TriggerStates.waiting_keywords)
    await callback.answer()


async def admin_trigger_add_keywords(message: Message, state: FSMContext) -> None:
    """Получение ключевых слов триггера"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    await state.update_data(keywords=message.text.strip())
    await safe_send_message(message.bot, message.chat.id, "✍️ Введите действие (ответ) триггера:", reply_markup=get_cancel_kb())
    await state.set_state(TriggerStates.waiting_action)


async def admin_trigger_add_action(message: Message, state: FSMContext) -> None:
    """Получение действия триггера"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    await state.update_data(action=message.text.strip())
    await safe_send_message(message.bot, message.chat.id, "📝 Введите дополнительное значение (можно пропустить, отправьте '-'):", reply_markup=get_cancel_kb())
    await state.set_state(TriggerStates.waiting_value)


async def admin_trigger_add_value(message: Message, state: FSMContext) -> None:
    """Получение значения триггера"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    data = await state.get_data()
    value = None if message.text == '-' else message.text.strip()
    trigger_id = await db.add_trigger(keywords=data['keywords'], action=data['action'], value=value)
    await log_action(user.id, "admin_trigger_add", f"Added trigger: {data['keywords']} (ID: {trigger_id})")
    
    # Обновляем кэш триггеров
    await refresh_triggers_cache()
    
    await state.clear()
    await safe_send_message(message.bot, message.chat.id, texts.TRIGGER_ADDED, reply_markup=get_admin_triggers_kb())


async def admin_triggers_list(callback: CallbackQuery) -> None:
    """Список триггеров"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    triggers = await db.get_all_triggers()
    if not triggers:
        await safe_edit_message(callback.bot, callback=callback, text="⚡ Триггеров пока нет", reply_markup=get_admin_triggers_kb())
        await callback.answer()
        return
    text = "📋 Список триггеров:\n\n"
    for trigger in triggers:
        text += f"• {escape_html(trigger['keywords'])} → {escape_html(trigger['action'])}\n"
    await log_action(user.id, "admin_triggers_list", f"Showing {len(triggers)} triggers")
    await safe_edit_message(callback.bot, callback=callback, text=text, reply_markup=get_admin_triggers_kb())
    await callback.answer()


async def admin_trigger_delete_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало удаления триггера"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    triggers = await db.get_all_triggers()
    if not triggers:
        await callback.answer("⚡ Нет триггеров для удаления")
        return
    await state.update_data(action="trigger_delete")
    text = "🗑 Удаление триггера\n\nВведите ID триггера для удаления:\n"
    for trigger in triggers:
        text += f"• ID: {trigger['id']} — {escape_html(trigger['keywords'])}\n"
    await safe_edit_message(callback.bot, callback=callback, text=text, reply_markup=get_cancel_kb())
    await state.set_state(TriggerStates.waiting_edit)
    await callback.answer()


async def admin_trigger_delete_execute(message: Message, state: FSMContext) -> None:
    """Выполнение удаления триггера"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    try:
        trigger_id = int(message.text.strip())
    except ValueError:
        await safe_send_message(message.bot, message.chat.id, "❌ Введите корректный ID (только цифры):", reply_markup=get_cancel_kb())
        return
    trigger = await db.get_trigger_by_id(trigger_id)
    if not trigger:
        await safe_send_message(message.bot, message.chat.id, "❌ Триггер с таким ID не найден", reply_markup=get_cancel_kb())
        return
    await db.delete_trigger(trigger_id)
    await log_action(user.id, "admin_trigger_delete", f"Deleted trigger: {trigger['keywords']} (ID: {trigger_id})")
    
    # Обновляем кэш триггеров
    await refresh_triggers_cache()
    
    await state.clear()
    await safe_send_message(message.bot, message.chat.id, texts.TRIGGER_DELETED, reply_markup=get_admin_triggers_kb())

# ============================================================
# МОДЕРАЦИЯ
# ============================================================

async def admin_moderation_menu(callback: CallbackQuery) -> None:
    """Меню модерации"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await log_action(user.id, "admin_moderation_menu", "Opened moderation")
    await safe_edit_message(callback.bot, callback=callback, text="👥 Модерация\n\nВыберите действие:", reply_markup=get_admin_moderation_kb())
    await callback.answer()


async def admin_moderation_warn_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало выдачи предупреждения"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await state.update_data(action="warn")
    await safe_edit_message(callback.bot, callback=callback, text="⚠️ Выдача предупреждения\n\nВведите Telegram ID пользователя:", reply_markup=get_cancel_kb())
    await state.set_state(ModerationStates.waiting_user)
    await callback.answer()


async def admin_moderation_mute_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало выдачи мута"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await state.update_data(action="mute")
    await safe_edit_message(callback.bot, callback=callback, text="🔇 Выдача мута\n\nВведите Telegram ID пользователя:", reply_markup=get_cancel_kb())
    await state.set_state(ModerationStates.waiting_user)
    await callback.answer()


async def admin_moderation_unmute_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало размута"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await state.update_data(action="unmute")
    await safe_edit_message(callback.bot, callback=callback, text="🔊 Размут\n\nВведите Telegram ID пользователя:", reply_markup=get_cancel_kb())
    await state.set_state(ModerationStates.waiting_user)
    await callback.answer()


async def admin_moderation_ban_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало бана"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await state.update_data(action="ban")
    await safe_edit_message(callback.bot, callback=callback, text="🚫 Бан\n\nВведите Telegram ID пользователя:", reply_markup=get_cancel_kb())
    await state.set_state(ModerationStates.waiting_user)
    await callback.answer()


async def admin_moderation_unban_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало разбана"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await state.update_data(action="unban")
    await safe_edit_message(callback.bot, callback=callback, text="✅ Разбан\n\nВведите Telegram ID пользователя:", reply_markup=get_cancel_kb())
    await state.set_state(ModerationStates.waiting_user)
    await callback.answer()


async def admin_moderation_history(callback: CallbackQuery, state: FSMContext) -> None:
    """Просмотр истории наказаний"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await state.update_data(action="history")
    await safe_edit_message(callback.bot, callback=callback, text="📄 История наказаний\n\nВведите Telegram ID пользователя:", reply_markup=get_cancel_kb())
    await state.set_state(ModerationStates.waiting_user)
    await callback.answer()


async def admin_moderation_handle_user(message: Message, state: FSMContext) -> None:
    """Обработка пользователя для модерации"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    
    data = await state.get_data()
    action = data.get('action')
    
    try:
        target_id = int(message.text.strip())
    except ValueError:
        await safe_send_message(message.bot, message.chat.id, "❌ Введите корректный Telegram ID (только цифры):", reply_markup=get_cancel_kb())
        return
    
    target = await db.get_user_by_telegram_id(target_id)
    if not target:
        await safe_send_message(message.bot, message.chat.id, "❌ Пользователь не найден в базе", reply_markup=get_cancel_kb())
        return
    
    await state.update_data(target_id=target_id)
    
    if action == "warn":
        await safe_send_message(
            message.bot,
            message.chat.id,
            "✍️ Введите причину:",
            reply_markup=get_cancel_kb()
        )
        await state.set_state(ModerationStates.waiting_reason)
    
    elif action == "mute":
        await safe_send_message(
            message.bot,
            message.chat.id,
            "⏱ Введите длительность (например: 1h, 30m, 7d):",
            reply_markup=get_cancel_kb()
        )
        await state.set_state(ModerationStates.waiting_duration)
    
    elif action == "unmute":
        await db.set_user_muted(target_id, False)
        await log_action(user.id, "moderation_unmute", f"Unmuted user {target_id}")
        await state.clear()
        await safe_send_message(message.bot, message.chat.id, texts.UNMUTE_MESSAGES.format(user_id=target_id), reply_markup=get_admin_moderation_kb())
    
    elif action == "ban":
        await db.set_user_banned(target_id, True)
        await log_action(user.id, "moderation_ban", f"Banned user {target_id}")
        await state.clear()
        await safe_send_message(message.bot, message.chat.id, texts.BAN_MESSAGES.format(user_id=target_id), reply_markup=get_admin_moderation_kb())
    
    elif action == "unban":
        await db.set_user_banned(target_id, False)
        await log_action(user.id, "moderation_unban", f"Unbanned user {target_id}")
        await state.clear()
        await safe_send_message(message.bot, message.chat.id, texts.UNBAN_MESSAGES.format(user_id=target_id), reply_markup=get_admin_moderation_kb())
    
    elif action == "history":
        punishments = await db.get_punishment_history(target['id'])
        if not punishments:
            await safe_send_message(message.bot, message.chat.id, f"📄 У пользователя {target_id} нет наказаний", reply_markup=get_admin_moderation_kb())
            await state.clear()
            return
        text = f"📄 История наказаний для {target_id}:\n\n"
        for p in punishments[:20]:
            text += f"• {p['type']} — {p['reason'] or 'Без причины'} ({p['start_time']})\n"
        await log_action(user.id, "moderation_history", f"Viewed history for {target_id}")
        await state.clear()
        await safe_send_message(message.bot, message.chat.id, text, reply_markup=get_admin_moderation_kb())


async def admin_moderation_handle_duration(message: Message, state: FSMContext) -> None:
    """Обработка длительности для мута"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    
    duration = parse_duration(message.text)
    if duration == 0:
        await safe_send_message(message.bot, message.chat.id, "❌ Неверный формат. Используйте: 1h, 30m, 7d", reply_markup=get_cancel_kb())
        return
    
    await state.update_data(duration=duration)
    await safe_send_message(message.bot, message.chat.id, "✍️ Введите причину мута:", reply_markup=get_cancel_kb())
    await state.set_state(ModerationStates.waiting_reason)


async def admin_moderation_handle_reason(message: Message, state: FSMContext) -> None:
    """Обработка причины для модерации"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    
    data = await state.get_data()
    action = data.get('action')
    target_id = data.get('target_id')
    
    if action == "warn":
        target = await db.get_user_by_telegram_id(target_id)
        new_warn_count = target['warn_count'] + 1
        await db.update_user_warn_count(target_id, new_warn_count)
        await db.add_punishment(user_id=target['id'], p_type="warning", reason=message.text, issued_by=user.id)
        await log_action(user.id, "moderation_warn", f"Warned user {target_id} (count: {new_warn_count})")
        await state.clear()
        await safe_send_message(message.bot, message.chat.id, texts.WARN_MESSAGES.format(user_id=target_id, count=new_warn_count, reason=message.text), reply_markup=get_admin_moderation_kb())
    
    elif action == "mute":
        duration = data.get('duration')
        target = await db.get_user_by_telegram_id(target_id)
        await db.set_user_muted(target_id, True)
        end_time = (datetime.now() + timedelta(seconds=duration)).isoformat()
        await db.add_punishment(user_id=target['id'], p_type="mute", reason=message.text, issued_by=user.id, end_time=end_time)
        await log_action(user.id, "moderation_mute", f"Muted user {target_id} for {duration}s")
        await state.clear()
        await safe_send_message(message.bot, message.chat.id, texts.MUTE_MESSAGES.format(user_id=target_id, duration=format_duration(duration), reason=message.text), reply_markup=get_admin_moderation_kb())


# ============================================================
# СТАТИСТИКА
# ============================================================

async def admin_stats_menu(callback: CallbackQuery) -> None:
    """Меню статистики"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await log_action(user.id, "admin_stats_menu", "Opened stats")
    await safe_edit_message(callback.bot, callback=callback, text="📊 Статистика\n\nВыберите раздел:", reply_markup=get_admin_stats_kb())
    await callback.answer()


async def admin_stats_users(callback: CallbackQuery) -> None:
    """Статистика пользователей"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    total = await db.get_user_count()
    banned = await db.get_banned_users()
    muted = await db.get_muted_users()
    text = f"👥 Статистика пользователей:\n\n• Всего: {total}\n• Забанено: {len(banned)}\n• Замьючено: {len(muted)}"
    await log_action(user.id, "admin_stats_users", "Viewed users stats")
    await safe_edit_message(callback.bot, callback=callback, text=text, reply_markup=get_admin_stats_kb())
    await callback.answer()


async def admin_stats_books(callback: CallbackQuery) -> None:
    """Статистика книг"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    books = await db.get_all_books()
    if not books:
        await callback.answer("📚 Книг пока нет")
        return
    total_downloads = sum(book['downloads'] for book in books)
    most_downloaded = max(books, key=lambda x: x['downloads'])
    text = f"📚 Статистика книг:\n\n• Всего книг: {len(books)}\n• Всего скачиваний: {total_downloads}\n• Самая скачиваемая: {escape_html(most_downloaded['title'])} ({most_downloaded['downloads']} скачиваний)"
    await log_action(user.id, "admin_stats_books", "Viewed books stats")
    await safe_edit_message(callback.bot, callback=callback, text=text, reply_markup=get_admin_stats_kb())
    await callback.answer()


# ============================================================
# ЛОГИ
# ============================================================

async def admin_logs(callback: CallbackQuery) -> None:
    """Просмотр логов"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    logs = await db.get_logs(limit=config.LOG_LIMIT)
    if not logs:
        await callback.answer("📋 Логов пока нет")
        return
    text = "📋 Последние события:\n\n"
    for log in logs[:20]:
        text += f"• {log['timestamp']} — {escape_html(log['action'])}\n"
        if log.get('details'):
            text += f"  {escape_html(log['details'])}\n"
    await log_action(user.id, "admin_logs", f"Viewed {len(logs)} logs")
    await safe_edit_message(callback.bot, callback=callback, text=text, reply_markup=get_admin_logs_kb())
    await callback.answer()

# ============================================================
# УПРАВЛЕНИЕ ДОНАТЕРАМИ
# ============================================================

async def admin_donators_menu(callback: CallbackQuery) -> None:
    """Меню управления донатерами"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    donators = await db.get_all_donators()
    text = "⭐ Друзья проекта:\n\n"
    if donators:
        for d in donators:
            text += f"• {escape_html(d['name'])}"
            if d.get('username'):
                text += f" (@{escape_html(d['username'])})"
            text += "\n"
    else:
        text += "Пока нет друзей проекта\n"
    await log_action(user.id, "admin_donators_menu", f"Showing {len(donators)} donators")
    await safe_edit_message(callback.bot, callback=callback, text=text, reply_markup=get_admin_donators_kb())
    await callback.answer()


async def admin_donator_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало добавления донатера"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await state.update_data(action="donator_add")
    await safe_edit_message(callback.bot, callback=callback, text="➕ Добавление друга проекта\n\nВведите имя:", reply_markup=get_cancel_kb())
    await state.set_state(DonatorStates.waiting_name)
    await callback.answer()


async def admin_donator_add_name(message: Message, state: FSMContext) -> None:
    """Получение имени донатера"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    await state.update_data(name=message.text.strip())
    await safe_send_message(message.bot, message.chat.id, "📝 Введите username (можно пропустить, отправьте '-'):", reply_markup=get_cancel_kb())
    await state.set_state(DonatorStates.waiting_username)


async def admin_donator_add_username(message: Message, state: FSMContext) -> None:
    """Получение username донатера"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    username = None if message.text == '-' else message.text.strip()
    await state.update_data(username=username)
    await safe_send_message(message.bot, message.chat.id, "💬 Введите комментарий (можно пропустить, отправьте '-'):", reply_markup=get_cancel_kb())
    await state.set_state(DonatorStates.waiting_comment)


async def admin_donator_add_comment(message: Message, state: FSMContext) -> None:
    """Получение комментария донатера"""
    user = message.from_user
    if not await is_admin(user.id):
        await safe_send_message(message.bot, message.chat.id, texts.ACCESS_DENIED)
        return
    data = await state.get_data()
    action = data.get('action')
    
    if action == "donator_add":
        comment = None if message.text == '-' else message.text.strip()
        donator_id = await db.add_donator(name=data['name'], username=data.get('username'), comment=comment)
        await log_action(user.id, "admin_donator_add", f"Added donator: {data['name']} (ID: {donator_id})")
        await state.clear()
        await safe_send_message(message.bot, message.chat.id, "✅ Друг проекта добавлен", reply_markup=get_admin_donators_kb())
    
    elif action == "donator_remove":
        try:
            donator_id = int(message.text.strip())
        except ValueError:
            await safe_send_message(message.bot, message.chat.id, "❌ Введите корректный ID (только цифры):", reply_markup=get_cancel_kb())
            return
        donators = await db.get_all_donators()
        donator = next((d for d in donators if d['id'] == donator_id), None)
        if not donator:
            await safe_send_message(message.bot, message.chat.id, "❌ Друг проекта с таким ID не найден", reply_markup=get_cancel_kb())
            return
        await db.remove_donator(donator_id)
        await log_action(user.id, "admin_donator_remove", f"Removed donator: {donator['name']} (ID: {donator_id})")
        await state.clear()
        await safe_send_message(message.bot, message.chat.id, "✅ Друг проекта удален", reply_markup=get_admin_donators_kb())


async def admin_donator_remove_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало удаления донатера"""
    user = callback.from_user
    if not await is_admin(user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    donators = await db.get_all_donators()
    if not donators:
        await callback.answer("⭐ Нет друзей проекта для удаления")
        return
    await state.update_data(action="donator_remove")
    text = "🗑 Удаление друга проекта\n\nВведите ID для удаления:\n"
    for d in donators:
        text += f"• {d['id']} — {escape_html(d['name'])}\n"
    await safe_edit_message(callback.bot, callback=callback, text=text, reply_markup=get_cancel_kb())
    await state.set_state(DonatorStates.waiting_comment)
    await callback.answer()


# ============================================================
# ОТМЕНА
# ============================================================

async def admin_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена действия"""
    user = callback.from_user
    await state.clear()
    await log_action(user.id, "admin_cancel", "Cancelled action")
    await safe_delete_message(callback.bot, callback.message.chat.id, callback.message.message_id)
    await safe_send_message(callback.bot, callback.message.chat.id, texts.CANCEL, reply_markup=get_admin_main_kb())
    await callback.answer()


# ============================================================
# РЕГИСТРАЦИЯ
# ============================================================

def register_admin_handlers(dp: Dispatcher) -> None:
    """Регистрация всех административных обработчиков"""
    
    dp.message.register(admin_command, Command("admin"))
    
    dp.callback_query.register(admin_menu, F.data == "admin:menu")
    
    dp.callback_query.register(admin_books_menu, F.data == "admin:books")
    dp.callback_query.register(admin_book_add_start, F.data == "admin:books:add")
    dp.callback_query.register(admin_book_list, F.data == "admin:books:edit")
    dp.callback_query.register(admin_book_delete_start, F.data == "admin:books:delete")
    dp.callback_query.register(admin_book_delete_confirm, F.data.startswith("book:info:"))
    dp.callback_query.register(admin_book_delete_execute, F.data == "confirm_admin_book_delete")
    
    dp.callback_query.register(admin_admins_menu, F.data == "admin:admins")
    dp.callback_query.register(admin_admin_add_start, F.data == "admin:admins:add")
    dp.callback_query.register(admin_admin_remove_start, F.data == "admin:admins:remove")
    
    dp.callback_query.register(admin_triggers_menu, F.data == "admin:triggers")
    dp.callback_query.register(admin_trigger_add_start, F.data == "admin:triggers:add")
    dp.callback_query.register(admin_triggers_list, F.data == "admin:triggers:list")
    
    dp.callback_query.register(admin_stats_menu, F.data == "admin:stats")
    dp.callback_query.register(admin_stats_users, F.data == "admin:stats:users")
    dp.callback_query.register(admin_stats_books, F.data == "admin:stats:books")
    
    dp.callback_query.register(admin_moderation_menu, F.data == "admin:moderation")
    dp.callback_query.register(admin_moderation_warn_start, F.data == "admin:warn")
    dp.callback_query.register(admin_moderation_mute_start, F.data == "admin:mute")
    dp.callback_query.register(admin_moderation_unmute_start, F.data == "admin:unmute")
    dp.callback_query.register(admin_moderation_ban_start, F.data == "admin:ban")
    dp.callback_query.register(admin_moderation_unban_start, F.data == "admin:unban")
    dp.callback_query.register(admin_moderation_history, F.data == "admin:history")
    
    dp.callback_query.register(admin_donators_menu, F.data == "admin:donators")
    dp.callback_query.register(admin_donator_add_start, F.data == "admin:donators:add")
    dp.callback_query.register(admin_donator_remove_start, F.data == "admin:donators:remove")
    
    dp.callback_query.register(admin_logs, F.data == "admin:logs")
    
    dp.callback_query.register(admin_cancel, F.data == "cancel")
    
    dp.message.register(admin_book_add_title, StateFilter(BookStates.waiting_title))
    dp.message.register(admin_book_add_author, StateFilter(BookStates.waiting_author))
    dp.message.register(admin_book_add_description, StateFilter(BookStates.waiting_description))
    dp.message.register(admin_book_add_poster, StateFilter(BookStates.waiting_poster), F.content_type == "photo")
    dp.message.register(admin_book_add_file, StateFilter(BookStates.waiting_file), F.content_type == "document")
    
    dp.message.register(admin_admin_handle_id, StateFilter(AdminStates.waiting_admin_id))
    
    dp.message.register(admin_trigger_add_keywords, StateFilter(TriggerStates.waiting_keywords))
    dp.message.register(admin_trigger_add_action, StateFilter(TriggerStates.waiting_action))
    dp.message.register(admin_trigger_add_value, StateFilter(TriggerStates.waiting_value))
    
    dp.message.register(admin_moderation_handle_user, StateFilter(ModerationStates.waiting_user))
    dp.message.register(admin_moderation_handle_duration, StateFilter(ModerationStates.waiting_duration))
    dp.message.register(admin_moderation_handle_reason, StateFilter(ModerationStates.waiting_reason))
    
    dp.message.register(admin_donator_add_name, StateFilter(DonatorStates.waiting_name))
    dp.message.register(admin_donator_add_username, StateFilter(DonatorStates.waiting_username))
    dp.message.register(admin_donator_add_comment, StateFilter(DonatorStates.waiting_comment))
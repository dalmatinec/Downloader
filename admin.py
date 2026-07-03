import logging
import re
from typing import Optional

from aiogram import Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import config
import texts
from database import Database
from keyboards import (
    get_admin_kb,
    get_admin_books_kb,
    get_admin_delete_books_kb,
    get_admin_donators_kb,
    get_admin_delete_donators_kb,
    get_stats_kb,
    get_back_kb,
    get_cancel_kb
)
from send import send_broadcast, forward_broadcast, video_broadcast
from utils import (
    safe_send_message,
    safe_edit_message,
    safe_delete_message,
    escape_html,
    format_stats
)


logger = logging.getLogger(__name__)
db = Database()


# ============================================================
# FSM СОСТОЯНИЯ
# ============================================================

class AdminStates(StatesGroup):
    # Рассылки
    waiting_send_message = State()
    waiting_forward_message = State()
    waiting_video_url = State()
    
    # Книги
    waiting_book_title = State()
    waiting_book_author = State()
    waiting_book_description = State()
    waiting_book_poster = State()
    waiting_book_file = State()
    
    # Донатеры
    waiting_donator_name = State()
    waiting_donator_username = State()
    
    # Администраторы
    waiting_add_admin_id = State()
    waiting_del_admin_id = State()
    
    # Подтверждения
    waiting_confirm = State()


# ============================================================
# ПРОВЕРКА ПРАВ
# ============================================================

async def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    # Супер-администратор из config всегда имеет доступ
    if user_id == config.ADMIN_ID:
        return True
    # Остальные проверяются по таблице admins
    admin = await db.get_admin(user_id)
    return admin is not None


# ============================================================
# КОМАНДА /ADMIN
# ============================================================

async def admin_command(message: Message) -> None:
    """Открыть админ-панель"""
    if not await is_admin(message.from_user.id):
        return
    
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.ADMIN_MENU_TEXT,
        reply_markup=get_admin_kb()
    )


async def admin_menu_callback(callback: CallbackQuery) -> None:
    """Возврат в админ-панель через callback"""
    if not await is_admin(callback.from_user.id):
        await callback.answer()
        return
    
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.ADMIN_MENU_TEXT,
        reply_markup=get_admin_kb()
    )
    await callback.answer()


# ============================================================
# КОМАНДА /HELP
# ============================================================

async def help_command(message: Message) -> None:
    """Список команд администратора"""
    if not await is_admin(message.from_user.id):
        return
    
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.HELP_TEXT
    )

# ============================================================
# /SEND
# ============================================================

async def send_command(message: Message, state: FSMContext) -> None:
    """Начало рассылки"""
    if not await is_admin(message.from_user.id):
        return
    
    await state.set_state(AdminStates.waiting_send_message)
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.SEND_PROMPT,
        reply_markup=get_cancel_kb()
    )


async def send_receive_message(message: Message, state: FSMContext) -> None:
    """Получение сообщения для рассылки"""
    if not await is_admin(message.from_user.id):
        return
    
    await state.update_data(send_message=message)
    await state.set_state(AdminStates.waiting_confirm)
    
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.SEND_CONFIRM,
        reply_markup=await get_confirm_kb("send")
    )


async def send_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение рассылки"""
    if not await is_admin(callback.from_user.id):
        await callback.answer()
        return
    
    data = await state.get_data()
    admin_message = data.get('send_message')
    
    if not admin_message:
        await callback.answer(texts.ERROR_MESSAGE_NOT_FOUND)
        await state.clear()
        return
    
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.SEND_STARTED,
        reply_markup=None
    )
    
    result = await send_broadcast(
        bot=callback.bot,
        db=db,
        admin_message=admin_message
    )
    
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.SEND_FINISHED.format(
            total=result['total'],
            sent=result['sent'],
            failed=result['failed']
        ),
        reply_markup=get_back_kb("back:admin")
    )
    await state.clear()
    await callback.answer()


# ============================================================
# /FORWARD
# ============================================================

async def forward_command(message: Message, state: FSMContext) -> None:
    """Начало пересылки"""
    if not await is_admin(message.from_user.id):
        return
    
    await state.set_state(AdminStates.waiting_forward_message)
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.FORWARD_PROMPT,
        reply_markup=get_cancel_kb()
    )


async def forward_receive_message(message: Message, state: FSMContext) -> None:
    """Получение сообщения для пересылки"""
    if not await is_admin(message.from_user.id):
        return
    
    await state.update_data(forward_message=message)
    await state.set_state(AdminStates.waiting_confirm)
    
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.FORWARD_CONFIRM,
        reply_markup=await get_confirm_kb("forward")
    )


async def forward_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение пересылки"""
    if not await is_admin(callback.from_user.id):
        await callback.answer()
        return
    
    data = await state.get_data()
    admin_message = data.get('forward_message')
    
    if not admin_message:
        await callback.answer(texts.ERROR_MESSAGE_NOT_FOUND)
        await state.clear()
        return
    
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.FORWARD_STARTED,
        reply_markup=None
    )
    
    result = await forward_broadcast(
        bot=callback.bot,
        db=db,
        admin_message=admin_message
    )
    
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.FORWARD_FINISHED.format(
            total=result['total'],
            sent=result['sent'],
            failed=result['failed']
        ),
        reply_markup=get_back_kb("back:admin")
    )
    await state.clear()
    await callback.answer()


# ============================================================
# /VIDEO
# ============================================================

async def video_command(message: Message, state: FSMContext) -> None:
    """Начало видео-рассылки"""
    if not await is_admin(message.from_user.id):
        return
    
    await state.set_state(AdminStates.waiting_video_url)
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.VIDEO_PROMPT,
        reply_markup=get_cancel_kb()
    )


async def video_receive_url(message: Message, state: FSMContext) -> None:
    """Получение ссылки на видео"""
    if not await is_admin(message.from_user.id):
        return
    
    url = message.text.strip()
    
    # Проверка, что ссылка на YouTube
    if not re.match(r'^https?://(www\.)?(youtube\.com|youtu\.be)/[^\s]+$', url):
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text=texts.VIDEO_INVALID_URL,
            reply_markup=get_cancel_kb()
        )
        return
    
    await state.update_data(video_url=url)
    await state.set_state(AdminStates.waiting_confirm)
    
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.VIDEO_CONFIRM.format(url=url),
        reply_markup=await get_confirm_kb("video")
    )


async def video_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение видео-рассылки"""
    if not await is_admin(callback.from_user.id):
        await callback.answer()
        return
    
    data = await state.get_data()
    video_url = data.get('video_url')
    
    if not video_url:
        await callback.answer(texts.ERROR_URL_NOT_FOUND)
        await state.clear()
        return
    
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.VIDEO_STARTED,
        reply_markup=None
    )
    
    result = await video_broadcast(
        bot=callback.bot,
        db=db,
        video_url=video_url
    )
    
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.VIDEO_FINISHED.format(
            total=result['total'],
            sent=result['sent'],
            failed=result['failed']
        ),
        reply_markup=get_back_kb("back:admin")
    )
    await state.clear()
    await callback.answer()

# ============================================================
# /ADDADMIN
# ============================================================

async def add_admin_command(message: Message, state: FSMContext) -> None:
    """Добавление администратора"""
    if not await is_admin(message.from_user.id):
        return
    
    await state.set_state(AdminStates.waiting_add_admin_id)
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.ADD_ADMIN_PROMPT,
        reply_markup=get_cancel_kb()
    )


async def add_admin_receive_id(message: Message, state: FSMContext) -> None:
    """Получение ID для добавления администратора"""
    if not await is_admin(message.from_user.id):
        return
    
    try:
        admin_id = int(message.text.strip())
    except ValueError:
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text=texts.ADD_ADMIN_INVALID_ID,
            reply_markup=get_cancel_kb()
        )
        return
    
    existing = await db.get_admin(admin_id)
    if existing:
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text=texts.ADD_ADMIN_EXISTS,
            reply_markup=get_back_kb("back:admin")
        )
        await state.clear()
        return
    
    await db.add_admin(admin_id)
    logger.info(f"Admin added: {admin_id} by {message.from_user.id}")
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.ADD_ADMIN_SUCCESS,
        reply_markup=get_back_kb("back:admin")
    )
    await state.clear()


# ============================================================
# /DELADMIN
# ============================================================

async def del_admin_command(message: Message, state: FSMContext) -> None:
    """Удаление администратора"""
    if not await is_admin(message.from_user.id):
        return
    
    await state.set_state(AdminStates.waiting_del_admin_id)
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.DEL_ADMIN_PROMPT,
        reply_markup=get_cancel_kb()
    )


async def del_admin_receive_id(message: Message, state: FSMContext) -> None:
    """Получение ID для удаления администратора"""
    if not await is_admin(message.from_user.id):
        return
    
    try:
        admin_id = int(message.text.strip())
    except ValueError:
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text=texts.DEL_ADMIN_INVALID_ID,
            reply_markup=get_cancel_kb()
        )
        return
    
    # Запрет удаления самого себя
    if admin_id == message.from_user.id:
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text=texts.DEL_ADMIN_SELF,
            reply_markup=get_back_kb("back:admin")
        )
        await state.clear()
        return
    
    # Запрет удаления последнего администратора (не считая суперадмина из config)
    admins = await db.get_all_admins()
    if len(admins) <= 1:
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text=texts.DEL_ADMIN_LAST,
            reply_markup=get_back_kb("back:admin")
        )
        await state.clear()
        return
    
    existing = await db.get_admin(admin_id)
    if not existing:
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text=texts.DEL_ADMIN_NOT_FOUND,
            reply_markup=get_back_kb("back:admin")
        )
        await state.clear()
        return
    
    await db.delete_admin(admin_id)
    logger.info(f"Admin removed: {admin_id} by {message.from_user.id}")
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.DEL_ADMIN_SUCCESS,
        reply_markup=get_back_kb("back:admin")
    )
    await state.clear()

# ============================================================
# АДМИН-ПАНЕЛЬ: КНИГИ
# ============================================================

async def admin_books_menu(callback: CallbackQuery) -> None:
    """Меню управления книгами"""
    if not await is_admin(callback.from_user.id):
        await callback.answer()
        return
    
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.ADMIN_BOOKS_MENU,
        reply_markup=get_admin_books_kb()
    )
    await callback.answer()


# ---------- ДОБАВЛЕНИЕ КНИГИ ----------

async def admin_book_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало добавления книги"""
    if not await is_admin(callback.from_user.id):
        await callback.answer()
        return
    
    await state.set_state(AdminStates.waiting_book_title)
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.ADD_BOOK_TITLE,
        reply_markup=get_cancel_kb()
    )
    await callback.answer()


async def admin_book_add_title(message: Message, state: FSMContext) -> None:
    """Получение названия книги"""
    if not await is_admin(message.from_user.id):
        return
    
    title = message.text.strip()
    if len(title) > 150:
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text=texts.ADD_BOOK_TITLE_TOO_LONG,
            reply_markup=get_cancel_kb()
        )
        return
    
    await state.update_data(book_title=title)
    await state.set_state(AdminStates.waiting_book_author)
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.ADD_BOOK_AUTHOR,
        reply_markup=get_cancel_kb()
    )


async def admin_book_add_author(message: Message, state: FSMContext) -> None:
    """Получение автора книги"""
    if not await is_admin(message.from_user.id):
        return
    
    author = message.text.strip()
    if len(author) > 150:
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text=texts.ADD_BOOK_AUTHOR_TOO_LONG,
            reply_markup=get_cancel_kb()
        )
        return
    
    await state.update_data(book_author=author)
    await state.set_state(AdminStates.waiting_book_description)
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.ADD_BOOK_DESCRIPTION,
        reply_markup=get_cancel_kb()
    )


async def admin_book_add_description(message: Message, state: FSMContext) -> None:
    """Получение описания книги"""
    if not await is_admin(message.from_user.id):
        return
    
    description = message.text.strip()
    await state.update_data(book_description=description)
    await state.set_state(AdminStates.waiting_book_poster)
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.ADD_BOOK_POSTER,
        reply_markup=get_cancel_kb()
    )


async def admin_book_add_poster(message: Message, state: FSMContext) -> None:
    """Получение постера книги"""
    if not await is_admin(message.from_user.id):
        return
    
    if not message.photo:
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text=texts.ADD_BOOK_POSTER_INVALID,
            reply_markup=get_cancel_kb()
        )
        return
    
    await state.update_data(book_poster=message.photo[-1].file_id)
    await state.set_state(AdminStates.waiting_book_file)
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.ADD_BOOK_FILE,
        reply_markup=get_cancel_kb()
    )


async def admin_book_add_file(message: Message, state: FSMContext) -> None:
    """Получение файла книги"""
    if not await is_admin(message.from_user.id):
        return
    
    if not message.document:
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text=texts.ADD_BOOK_FILE_INVALID,
            reply_markup=get_cancel_kb()
        )
        return
    
    data = await state.get_data()
    
    book_id = await db.add_book(
        title=data['book_title'],
        author=data['book_author'],
        description=data['book_description'],
        poster_file_id=data['book_poster'],
        book_file_id=message.document.file_id
    )
    
    if book_id:
        logger.info(f"Book added: {data['book_title']} (ID: {book_id}) by {message.from_user.id}")
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text=texts.ADD_BOOK_SUCCESS,
            reply_markup=get_back_kb("back:admin:books")
        )
    else:
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text=texts.ADD_BOOK_ERROR,
            reply_markup=get_back_kb("back:admin:books")
        )
    
    await state.clear()


# ---------- УДАЛЕНИЕ КНИГИ ----------

async def admin_book_delete_start(callback: CallbackQuery) -> None:
    """Начало удаления книги (список)"""
    if not await is_admin(callback.from_user.id):
        await callback.answer()
        return
    
    books = await db.get_all_books()
    if not books:
        await callback.answer(texts.DELETE_BOOK_NO_BOOKS)
        return
    
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.DELETE_BOOK_LIST,
        reply_markup=get_admin_delete_books_kb(books)
    )
    await callback.answer()


async def admin_book_delete_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение удаления книги"""
    if not await is_admin(callback.from_user.id):
        await callback.answer()
        return
    
    try:
        book_id = int(callback.data.split(':')[-1])
    except ValueError:
        await callback.answer(texts.ERROR_INVALID_DATA)
        return
    
    book = await db.get_book(book_id)
    if not book:
        await callback.answer(texts.ERROR_BOOK_NOT_FOUND)
        return
    
    await state.update_data(delete_book_id=book_id)
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.DELETE_BOOK_CONFIRM.format(title=escape_html(book['title'])),
        reply_markup=await get_confirm_kb("delete_book")
    )
    await callback.answer()


async def admin_book_delete_execute(callback: CallbackQuery, state: FSMContext) -> None:
    """Выполнение удаления книги"""
    if not await is_admin(callback.from_user.id):
        await callback.answer()
        return
    
    data = await state.get_data()
    book_id = data.get('delete_book_id')
    
    if not book_id:
        await callback.answer(texts.ERROR_BOOK_NOT_FOUND)
        await state.clear()
        return
    
    book = await db.get_book(book_id)
    if book:
        await db.delete_book(book_id)
        logger.info(f"Book deleted: {book['title']} (ID: {book_id}) by {callback.from_user.id}")
        await safe_edit_message(
            bot=callback.bot,
            callback=callback,
            text=texts.DELETE_BOOK_SUCCESS.format(title=escape_html(book['title'])),
            reply_markup=get_back_kb("back:admin:books")
        )
    else:
        await safe_edit_message(
            bot=callback.bot,
            callback=callback,
            text=texts.DELETE_BOOK_ERROR,
            reply_markup=get_back_kb("back:admin:books")
        )
    
    await state.clear()
    await callback.answer()

# ============================================================
# АДМИН-ПАНЕЛЬ: ДОНАТЕРЫ
# ============================================================

async def admin_donators_menu(callback: CallbackQuery) -> None:
    """Меню управления донатерами"""
    if not await is_admin(callback.from_user.id):
        await callback.answer()
        return
    
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.ADMIN_DONATORS_MENU,
        reply_markup=get_admin_donators_kb()
    )
    await callback.answer()


# ---------- ДОБАВЛЕНИЕ ДОНАТЕРА ----------

async def admin_donator_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало добавления донатера"""
    if not await is_admin(callback.from_user.id):
        await callback.answer()
        return
    
    await state.set_state(AdminStates.waiting_donator_name)
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.ADD_DONATOR_NAME,
        reply_markup=get_cancel_kb()
    )
    await callback.answer()


async def admin_donator_add_name(message: Message, state: FSMContext) -> None:
    """Получение имени донатера"""
    if not await is_admin(message.from_user.id):
        return
    
    name = message.text.strip()
    if len(name) > 100:
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text=texts.ADD_DONATOR_NAME_TOO_LONG,
            reply_markup=get_cancel_kb()
        )
        return
    
    await state.update_data(donator_name=name)
    await state.set_state(AdminStates.waiting_donator_username)
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.ADD_DONATOR_USERNAME,
        reply_markup=get_cancel_kb()
    )


async def admin_donator_add_username(message: Message, state: FSMContext) -> None:
    """Получение username донатера (опционально)"""
    if not await is_admin(message.from_user.id):
        return
    
    username = message.text.strip()
    if len(username) > 32:
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text=texts.ADD_DONATOR_USERNAME_TOO_LONG,
            reply_markup=get_cancel_kb()
        )
        return
    
    if username == "-":
        username = ""
    
    data = await state.get_data()
    
    await db.add_donator(
        name=data['donator_name'],
        username=username
    )
    
    logger.info(f"Donator added: {data['donator_name']} by {message.from_user.id}")
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.ADD_DONATOR_SUCCESS,
        reply_markup=get_back_kb("back:admin:donators")
    )
    await state.clear()


# ---------- УДАЛЕНИЕ ДОНАТЕРА ----------

async def admin_donator_delete_start(callback: CallbackQuery) -> None:
    """Начало удаления донатера (список)"""
    if not await is_admin(callback.from_user.id):
        await callback.answer()
        return
    
    donators = await db.get_all_donators()
    if not donators:
        await callback.answer(texts.DELETE_DONATOR_NO_DONATORS)
        return
    
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.DELETE_DONATOR_LIST,
        reply_markup=get_admin_delete_donators_kb(donators)
    )
    await callback.answer()


async def admin_donator_delete_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение удаления донатера"""
    if not await is_admin(callback.from_user.id):
        await callback.answer()
        return
    
    try:
        donator_id = int(callback.data.split(':')[-1])
    except ValueError:
        await callback.answer(texts.ERROR_INVALID_DATA)
        return
    
    donator = await db.get_donator(donator_id)
    if not donator:
        await callback.answer(texts.ERROR_DONATOR_NOT_FOUND)
        return
    
    await state.update_data(delete_donator_id=donator_id)
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.DELETE_DONATOR_CONFIRM.format(name=escape_html(donator['name'])),
        reply_markup=await get_confirm_kb("delete_donator")
    )
    await callback.answer()


async def admin_donator_delete_execute(callback: CallbackQuery, state: FSMContext) -> None:
    """Выполнение удаления донатера"""
    if not await is_admin(callback.from_user.id):
        await callback.answer()
        return
    
    data = await state.get_data()
    donator_id = data.get('delete_donator_id')
    
    if not donator_id:
        await callback.answer(texts.ERROR_DONATOR_NOT_FOUND)
        await state.clear()
        return
    
    donator = await db.get_donator(donator_id)
    if donator:
        await db.delete_donator(donator_id)
        logger.info(f"Donator deleted: {donator['name']} (ID: {donator_id}) by {callback.from_user.id}")
        await safe_edit_message(
            bot=callback.bot,
            callback=callback,
            text=texts.DELETE_DONATOR_SUCCESS.format(name=escape_html(donator['name'])),
            reply_markup=get_back_kb("back:admin:donators")
        )
    else:
        await safe_edit_message(
            bot=callback.bot,
            callback=callback,
            text=texts.DELETE_DONATOR_ERROR,
            reply_markup=get_back_kb("back:admin:donators")
        )
    
    await state.clear()
    await callback.answer()


# ============================================================
# АДМИН-ПАНЕЛЬ: СТАТИСТИКА
# ============================================================

async def admin_stats(callback: CallbackQuery) -> None:
    """Показать статистику"""
    if not await is_admin(callback.from_user.id):
        await callback.answer()
        return
    
    stats = await db.get_stats()
    text = format_stats(stats)
    
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=text,
        reply_markup=get_stats_kb()
    )
    await callback.answer()


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

async def get_confirm_kb(action: str):
    """Клавиатура подтверждения с динамическим callback"""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text=texts.CONFIRM_BUTTON, callback_data=f"confirm:{action}")
    builder.button(text=texts.CANCEL_BUTTON, callback_data="action:cancel")
    builder.adjust(2)
    return builder.as_markup()


async def admin_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена действия"""
    await state.clear()
    await safe_delete_message(
        bot=callback.bot,
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id
    )
    await safe_send_message(
        bot=callback.bot,
        chat_id=callback.message.chat.id,
        text=texts.CANCEL_ACTION,
        reply_markup=get_back_kb("back:admin")
    )
    await callback.answer()


async def confirm_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Общий обработчик подтверждения"""
    if not await is_admin(callback.from_user.id):
        await callback.answer()
        return
    
    action = callback.data.split(':')[-1]
    
    if action == "send":
        await send_confirm(callback, state)
    elif action == "forward":
        await forward_confirm(callback, state)
    elif action == "video":
        await video_confirm(callback, state)
    elif action == "delete_book":
        await admin_book_delete_execute(callback, state)
    elif action == "delete_donator":
        await admin_donator_delete_execute(callback, state)
    else:
        await callback.answer(texts.ERROR_UNKNOWN_ACTION)


# ============================================================
# РЕГИСТРАЦИЯ
# ============================================================

def register_admin_handlers(dp: Dispatcher) -> None:
    """Регистрация всех административных обработчиков"""
    
    # Команды
    dp.message.register(admin_command, Command("admin"))
    dp.message.register(help_command, Command("help"))
    dp.message.register(send_command, Command("send"))
    dp.message.register(forward_command, Command("forward"))
    dp.message.register(video_command, Command("video"))
    dp.message.register(add_admin_command, Command("addadmin"))
    dp.message.register(del_admin_command, Command("deladmin"))
    
    # Админ-панель (callback)
    dp.callback_query.register(admin_menu_callback, F.data == "back:admin")
    dp.callback_query.register(admin_books_menu, F.data == "admin:books")
    dp.callback_query.register(admin_donators_menu, F.data == "admin:donators")
    dp.callback_query.register(admin_stats, F.data == "admin:stats")
    
    # Книги (callback)
    dp.callback_query.register(admin_book_add_start, F.data == "admin:book:add")
    dp.callback_query.register(admin_book_delete_start, F.data == "admin:book:delete")
    dp.callback_query.register(admin_book_delete_confirm, F.data.startswith("admin:book:delete:"))
    
    # Донатеры (callback)
    dp.callback_query.register(admin_donator_add_start, F.data == "admin:donator:add")
    dp.callback_query.register(admin_donator_delete_start, F.data == "admin:donator:delete")
    dp.callback_query.register(admin_donator_delete_confirm, F.data.startswith("admin:donator:delete:"))
    
    # Общие callback
    dp.callback_query.register(admin_cancel, F.data == "action:cancel")
    dp.callback_query.register(confirm_callback, F.data.startswith("confirm:"))
    
    # FSM: Рассылки
    dp.message.register(send_receive_message, StateFilter(AdminStates.waiting_send_message))
    dp.message.register(forward_receive_message, StateFilter(AdminStates.waiting_forward_message))
    dp.message.register(video_receive_url, StateFilter(AdminStates.waiting_video_url))
    
    # FSM: Книги
    dp.message.register(admin_book_add_title, StateFilter(AdminStates.waiting_book_title))
    dp.message.register(admin_book_add_author, StateFilter(AdminStates.waiting_book_author))
    dp.message.register(admin_book_add_description, StateFilter(AdminStates.waiting_book_description))
    dp.message.register(admin_book_add_poster, StateFilter(AdminStates.waiting_book_poster))
    dp.message.register(admin_book_add_file, StateFilter(AdminStates.waiting_book_file))
    
    # FSM: Донатеры
    dp.message.register(admin_donator_add_name, StateFilter(AdminStates.waiting_donator_name))
    dp.message.register(admin_donator_add_username, StateFilter(AdminStates.waiting_donator_username))
    
    # FSM: Администраторы
    dp.message.register(add_admin_receive_id, StateFilter(AdminStates.waiting_add_admin_id))
    dp.message.register(del_admin_receive_id, StateFilter(AdminStates.waiting_del_admin_id))
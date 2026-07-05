import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

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
# FSM СОСТОЯНИЯ (дублируем здесь)
# ============================================================

class AdminStates(StatesGroup):
    waiting_send_message = State()
    waiting_forward_message = State()
    waiting_video_url = State()
    waiting_book_title = State()
    waiting_book_author = State()
    waiting_book_description = State()
    waiting_book_poster = State()
    waiting_book_file = State()
    waiting_donator_name = State()
    waiting_donator_username = State()
    waiting_add_admin_id = State()
    waiting_del_admin_id = State()
    waiting_confirm = State()


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def get_confirm_kb(action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=texts.CONFIRM_BUTTON, callback_data=f"confirm:{action}")
    builder.button(text=texts.CANCEL_BUTTON, callback_data="action:cancel")
    builder.adjust(2)
    return builder.as_markup()


async def is_admin(user_id: int) -> bool:
    if user_id == config.ADMIN_ID:
        return True
    admin = await db.get_admin(user_id)
    return admin is not None


router = Router()

# ============================================================
# /CANCEL
# ============================================================

@router.message(Command("cancel"), StateFilter("*"))
async def cancel_command(message: Message, state: FSMContext) -> None:
    if not await is_admin(message.from_user.id):
        return

    await state.clear()

    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text="❌ Действие отменено.",
        reply_markup=get_admin_kb()
    )

# ============================================================
# /ADMIN
# ============================================================

@router.message(Command("admin"))
async def admin_command(message: Message) -> None:
    if not await is_admin(message.from_user.id):
        return
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.ADMIN_MENU_TEXT,
        reply_markup=get_admin_kb()
    )


@router.callback_query(F.data == "back:admin")
async def admin_menu(callback: CallbackQuery) -> None:
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
# /HELP
# ============================================================

@router.message(Command("help"))
async def help_command(message: Message) -> None:
    if not await is_admin(message.from_user.id):
        return
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.HELP_TEXT
    )


# ============================================================
# /ADMLIST
# ============================================================

@router.message(Command("admlist"))
async def admin_list_command(message: Message) -> None:
    if not await is_admin(message.from_user.id):
        return

    admins = await db.get_all_admins()

    text = "<b>👑 Список администраторов</b>\n\n"

    for i, admin in enumerate(admins, 1):
        text += f"{i}. <code>{admin['telegram_id']}</code>\n"

    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=text
    )

# ============================================================
# КНИГИ (АДМИН)
# ============================================================

@router.callback_query(F.data == "admin:books")
async def admin_books_menu(callback: CallbackQuery) -> None:
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


@router.callback_query(F.data == "admin:book:add")
async def admin_book_add_start(callback: CallbackQuery, state: FSMContext) -> None:
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


@router.message(StateFilter(AdminStates.waiting_book_title))
async def admin_book_add_title(message: Message, state: FSMContext) -> None:
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


@router.message(StateFilter(AdminStates.waiting_book_author))
async def admin_book_add_author(message: Message, state: FSMContext) -> None:
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


@router.message(StateFilter(AdminStates.waiting_book_description))
async def admin_book_add_description(message: Message, state: FSMContext) -> None:
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


@router.message(StateFilter(AdminStates.waiting_book_poster))
async def admin_book_add_poster(message: Message, state: FSMContext) -> None:
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


@router.message(StateFilter(AdminStates.waiting_book_file))
async def admin_book_add_file(message: Message, state: FSMContext) -> None:
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
        logger.info(f"Book added: {data['book_title']} by {message.from_user.id}")
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


@router.callback_query(F.data == "admin:book:delete")
async def admin_book_delete_start(callback: CallbackQuery) -> None:
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


@router.callback_query(F.data.startswith("admin:book:delete:"))
async def admin_book_delete_confirm(callback: CallbackQuery, state: FSMContext) -> None:
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
        reply_markup=get_confirm_kb("delete_book")
    )
    await callback.answer()


@router.callback_query(F.data == "confirm:delete_book")
async def admin_book_delete_execute(callback: CallbackQuery, state: FSMContext) -> None:
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
# ДОНАТЕРЫ (АДМИН)
# ============================================================

@router.callback_query(F.data == "admin:donators")
async def admin_donators_menu(callback: CallbackQuery) -> None:
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


@router.callback_query(F.data == "admin:donator:add")
async def admin_donator_add_start(callback: CallbackQuery, state: FSMContext) -> None:
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


@router.message(StateFilter(AdminStates.waiting_donator_name))
async def admin_donator_add_name(message: Message, state: FSMContext) -> None:
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


@router.message(StateFilter(AdminStates.waiting_donator_username))
async def admin_donator_add_username(message: Message, state: FSMContext) -> None:
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
    await db.add_donator(name=data['donator_name'], username=username)
    logger.info(f"Donator added: {data['donator_name']} by {message.from_user.id}")
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.ADD_DONATOR_SUCCESS,
        reply_markup=get_back_kb("back:admin:donators")
    )
    await state.clear()


@router.callback_query(F.data == "admin:donator:delete")
async def admin_donator_delete_start(callback: CallbackQuery) -> None:
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


@router.callback_query(F.data.startswith("admin:donator:delete:"))
async def admin_donator_delete_confirm(callback: CallbackQuery, state: FSMContext) -> None:
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
        reply_markup=get_confirm_kb("delete_donator")
    )
    await callback.answer()


@router.callback_query(F.data == "confirm:delete_donator")
async def admin_donator_delete_execute(callback: CallbackQuery, state: FSMContext) -> None:
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
# СТАТИСТИКА
# ============================================================

@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery) -> None:
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
# РАССЫЛКИ
# ============================================================

@router.message(Command("send"))
async def send_command(message: Message, state: FSMContext) -> None:
    if not await is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.waiting_send_message)
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.SEND_PROMPT,
        reply_markup=get_cancel_kb()
    )


@router.message(StateFilter(AdminStates.waiting_send_message))
async def send_receive_message(message: Message, state: FSMContext) -> None:
    if not await is_admin(message.from_user.id):
        return
    await state.update_data(send_message=message)
    await state.set_state(AdminStates.waiting_confirm)
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.SEND_CONFIRM,
        reply_markup=get_confirm_kb("send")
    )


@router.callback_query(F.data == "confirm:send")
async def send_confirm(callback: CallbackQuery, state: FSMContext) -> None:
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
    result = await send_broadcast(bot=callback.bot, db=db, admin_message=admin_message)
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.SEND_FINISHED.format(
            total=result['total'], sent=result['sent'], failed=result['failed']
        ),
        reply_markup=get_back_kb("back:admin")
    )
    await state.clear()
    await callback.answer()


@router.message(Command("forward"))
async def forward_command(message: Message, state: FSMContext) -> None:
    if not await is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.waiting_forward_message)
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.FORWARD_PROMPT,
        reply_markup=get_cancel_kb()
    )


@router.message(StateFilter(AdminStates.waiting_forward_message))
async def forward_receive_message(message: Message, state: FSMContext) -> None:
    if not await is_admin(message.from_user.id):
        return
    await state.update_data(forward_message=message)
    await state.set_state(AdminStates.waiting_confirm)
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.FORWARD_CONFIRM,
        reply_markup=get_confirm_kb("forward")
    )


@router.callback_query(F.data == "confirm:forward")
async def forward_confirm(callback: CallbackQuery, state: FSMContext) -> None:
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
    result = await forward_broadcast(bot=callback.bot, db=db, admin_message=admin_message)
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.FORWARD_FINISHED.format(
            total=result['total'], sent=result['sent'], failed=result['failed']
        ),
        reply_markup=get_back_kb("back:admin")
    )
    await state.clear()
    await callback.answer()


@router.message(Command("video"))
async def video_command(message: Message, state: FSMContext) -> None:
    if not await is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.waiting_video_url)
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.VIDEO_PROMPT,
        reply_markup=get_cancel_kb()
    )


@router.message(StateFilter(AdminStates.waiting_video_url))
async def video_receive_url(message: Message, state: FSMContext) -> None:
    if not await is_admin(message.from_user.id):
        return
    url = message.text.strip()
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
        reply_markup=get_confirm_kb("video")
    )


@router.callback_query(F.data == "confirm:video")
async def video_confirm(callback: CallbackQuery, state: FSMContext) -> None:
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
    result = await video_broadcast(bot=callback.bot, db=db, video_url=video_url)
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.VIDEO_FINISHED.format(
            total=result['total'], sent=result['sent'], failed=result['failed']
        ),
        reply_markup=get_back_kb("back:admin")
    )
    await state.clear()
    await callback.answer()


# ============================================================
# ДОБАВЛЕНИЕ/УДАЛЕНИЕ АДМИНА
# ============================================================

@router.message(Command("addadmin"))
async def add_admin_command(message: Message, state: FSMContext) -> None:
    if not await is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.waiting_add_admin_id)
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.ADD_ADMIN_PROMPT,
        reply_markup=get_cancel_kb()
    )


@router.message(StateFilter(AdminStates.waiting_add_admin_id))
async def add_admin_receive_id(message: Message, state: FSMContext) -> None:
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


@router.message(Command("deladmin"))
async def del_admin_command(message: Message, state: FSMContext) -> None:
    if not await is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.waiting_del_admin_id)
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.DEL_ADMIN_PROMPT,
        reply_markup=get_cancel_kb()
    )


@router.message(StateFilter(AdminStates.waiting_del_admin_id))
async def del_admin_receive_id(message: Message, state: FSMContext) -> None:
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
    if admin_id == message.from_user.id:
        await safe_send_message(
            bot=message.bot,
            chat_id=message.chat.id,
            text=texts.DEL_ADMIN_SELF,
            reply_markup=get_back_kb("back:admin")
        )
        await state.clear()
        return
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
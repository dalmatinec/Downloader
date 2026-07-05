import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

import config
import texts
from database import Database
from keyboards import (
    get_main_kb,
    get_links_kb,
    get_books_kb,
    get_book_kb,
    get_support_kb,
    get_donators_kb,
    get_back_kb
)
from utils import (
    safe_send_message,
    safe_edit_message,
    escape_html,
    format_donators
)

logger = logging.getLogger(__name__)
db = Database()
router = Router()


# ============================================================
# /START
# ============================================================

@router.message(Command("start"), F.chat.type == "private")  # только ЛС
async def start_command(message: Message) -> None:
    user = message.from_user
    await db.add_user(user.id, user.username or "")
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=texts.START_TEXT.format(name=escape_html(user.first_name)),
        reply_markup=get_main_kb()
    )


# ============================================================
# ГЛАВНОЕ МЕНЮ
# ============================================================

@router.callback_query(F.data == "back:main")
async def main_menu(callback: CallbackQuery) -> None:
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.START_TEXT.format(name=escape_html(callback.from_user.first_name)),
        reply_markup=get_main_kb()
    )
    await callback.answer()


# ============================================================
# ССЫЛКИ
# ============================================================

@router.callback_query(F.data == "links")
async def links_menu(callback: CallbackQuery) -> None:
    text = texts.LINKS_TEXT.format(
        youtube=config.YOUTUBE_LINK,
        tiktok=config.TIKTOK_LINK,
        instagram=config.INSTAGRAM_LINK,
        channel=config.CHANNEL_LINK,
        chat=config.CHAT_LINK
    )
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=text,
        reply_markup=get_links_kb()
    )
    await callback.answer()


# ============================================================
# КНИГИ
# ============================================================

@router.callback_query(F.data == "books")
async def books_list(callback: CallbackQuery) -> None:
    books = await db.get_all_books()
    if not books:
        await safe_edit_message(
            bot=callback.bot,
            callback=callback,
            text=texts.BOOKS_EMPTY,
            reply_markup=get_back_kb("back:main")
        )
        await callback.answer()
        return
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=texts.BOOKS_LIST,
        reply_markup=get_books_kb(books)
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^book:\d+$"))
async def book_detail(callback: CallbackQuery) -> None:
    try:
        book_id = int(callback.data.split(':')[1])
    except (IndexError, ValueError):
        await callback.answer(texts.ERROR)
        return
    book = await db.get_book(book_id)
    if not book:
        await callback.answer(texts.BOOK_NOT_FOUND)
        return
    text = texts.BOOK_INFO_TEXT.format(
        title=escape_html(book['title']),
        author=escape_html(book['author']),
        description=escape_html(book['description'] or '')
    )
    if book.get('poster_file_id'):
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=book['poster_file_id'],
            caption=text,
            reply_markup=get_book_kb(book_id)
        )
    else:
        await safe_edit_message(
            bot=callback.bot,
            callback=callback,
            text=text,
            reply_markup=get_book_kb(book_id)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("book:download:"))
async def download_book(callback: CallbackQuery) -> None:
    try:
        book_id = int(callback.data.split(':')[2])
    except (IndexError, ValueError):
        await callback.answer(texts.ERROR)
        return
    book = await db.get_book(book_id)
    if not book:
        await callback.answer(texts.BOOK_NOT_FOUND)
        return
    if not book.get('book_file_id'):
        await callback.answer(texts.BOOK_NO_FILE)
        return
    await db.increment_book_downloads(book_id)
    await db.add_download(callback.from_user.id)
    try:
        await callback.bot.send_document(
            chat_id=callback.from_user.id,
            document=book['book_file_id'],
            caption=texts.BOOK_DOWNLOADED.format(title=escape_html(book['title']))
        )
        await callback.answer(texts.BOOK_DOWNLOAD_SUCCESS)
    except Exception as e:
        logger.error(f"Download error for user {callback.from_user.id}: {e}")
        await callback.answer(texts.BOOK_DOWNLOAD_ERROR)


# ============================================================
# ПОДДЕРЖКА
# ============================================================

@router.callback_query(F.data == "support")
async def support_menu(callback: CallbackQuery) -> None:
    text = texts.SUPPORT_TEXT.format(
        kaspi=config.KASPI_VISA,
        centerkredit=config.BANK_CENTERKREDIT,
        freedom=config.FREEDOM_BANK,
        paypal=config.PAYPAL_LINK,
        sber=config.SBER,
        vtb=config.VTB,
        tinkoff=config.TINKOFF
    )
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=text,
        reply_markup=get_support_kb()
    )
    await callback.answer()

# ---------------- ДОБАВЛЕНО ----------------

@router.callback_query(F.data == "back:support")
async def support_back(callback: CallbackQuery) -> None:
    await support_menu(callback)

# -------------- КОНЕЦ ДОБАВЛЕНИЯ --------------


# ============================================================
# ДОНАТЕРЫ
# ============================================================

@router.callback_query(F.data == "donators")
async def donators_list(callback: CallbackQuery) -> None:
    donators = await db.get_all_donators()
    donators_text = format_donators(donators)
    text = texts.DONATORS_TEXT.format(donators_list=donators_text)
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=text,
        reply_markup=get_donators_kb()
    )
    await callback.answer()


# ============================================================
# НАЗАД К КНИГАМ
# ============================================================

@router.callback_query(F.data == "back:books")
async def books_back(callback: CallbackQuery) -> None:
    books = await db.get_all_books()

    if callback.message.photo:  # если открыта карточка с постером
        await callback.message.delete()
        await callback.message.answer(
            texts.BOOKS_EMPTY if not books else texts.BOOKS_LIST,
            reply_markup=get_back_kb("back:main") if not books else get_books_kb(books)
        )
        await callback.answer()
        return

    await books_list(callback)
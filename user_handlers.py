import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
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
from support import send_book_thanks, handle_book_thanks_donate


logger = logging.getLogger(__name__)
db = Database()
router = Router()

START_IMAGE = FSInputFile("images/start.jpg")


# ============================================================
# /START
# ============================================================

@router.message(Command("start"), F.chat.type == "private")
async def start_command(message: Message) -> None:
    user = message.from_user
    await db.add_user(user.id, user.username or "")
    await message.answer_photo(
        photo=START_IMAGE,
        caption=texts.START_TEXT.format(name=escape_html(user.first_name)),
        reply_markup=get_main_kb()
    )


# ============================================================
# ГЛАВНОЕ МЕНЮ (ВОЗВРАТ)
# ============================================================

@router.callback_query(F.data == "back:main")
async def main_menu(callback: CallbackQuery) -> None:
    text = texts.START_TEXT.format(
        name=escape_html(callback.from_user.first_name)
    )

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=START_IMAGE,
        caption=text,
        reply_markup=get_main_kb()
    )

    await callback.answer()


# ============================================================
# ССЫЛКИ
# ============================================================

@router.callback_query(F.data == "links")
async def links_menu(callback: CallbackQuery) -> None:
    text = texts.LINKS_TEXT

    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(
            text=text,
            reply_markup=get_links_kb()
        )
    else:
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

    if callback.message.photo:
        await callback.message.delete()
        if not books:
            await callback.message.answer(
                text=texts.BOOKS_EMPTY,
                reply_markup=get_back_kb("back:main")
            )
        else:
            await callback.message.answer(
                text=texts.BOOKS_LIST,
                reply_markup=get_books_kb(books)
            )
    else:
        if not books:
            await safe_edit_message(
                bot=callback.bot,
                callback=callback,
                text=texts.BOOKS_EMPTY,
                reply_markup=get_back_kb("back:main")
            )
        else:
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

        # === ОТПРАВКА БЛАГОДАРНОСТИ ===
        try:
            await send_book_thanks(
                bot=callback.bot,
                chat_id=callback.from_user.id
            )
        except Exception as e:
            logger.error(f"Book thanks error: {e}")

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
        freedom=config.FREEDOM_VISA,
        bcc=config.BCC_VISA,
        ru_phone=config.RU_PHONE,
        paypal=config.PAYPAL,
    )

    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(
            text=text,
            reply_markup=get_support_kb()
        )
    else:
        await safe_edit_message(
            bot=callback.bot,
            callback=callback,
            text=text,
            reply_markup=get_support_kb()
        )

    await callback.answer()


@router.callback_query(F.data == "back:support")
async def support_back(callback: CallbackQuery) -> None:
    await support_menu(callback)


# ============================================================
# ДОНАТЕРЫ
# ============================================================

@router.callback_query(F.data == "donators")
async def donators_list(callback: CallbackQuery) -> None:
    donators = await db.get_all_donators()
    donators_text = format_donators(donators)
    text = texts.DONATORS_TEXT.format(donators_list=donators_text)

    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(
            text=text,
            reply_markup=get_donators_kb()
        )
    else:
        await safe_edit_message(
            bot=callback.bot,
            callback=callback,
            text=text,
            reply_markup=get_donators_kb()
        )
    await callback.answer()


# ============================================================
# ПОКАЗАТЬ EMAIL
# ============================================================

@router.callback_query(F.data == "show_email")
async def show_email(callback: CallbackQuery):
    from setting_handlers import load_settings
    settings = load_settings()
    await callback.answer()
    await callback.message.answer(
        f"📧 Email для связи:\n\n<code>{settings.get('EMAIL')}</code>"
    )


# ============================================================
# НАЗАД К КНИГАМ
# ============================================================

@router.callback_query(F.data == "back:books")
async def books_back(callback: CallbackQuery) -> None:
    books = await db.get_all_books()

    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(
            texts.BOOKS_EMPTY if not books else texts.BOOKS_LIST,
            reply_markup=get_back_kb("back:main") if not books else get_books_kb(books)
        )
        await callback.answer()
        return

    await books_list(callback)

# ============================================================
# БЛАГОДАРНОСТЬ ЗА КНИГУ
# ============================================================

@router.callback_query(F.data == "book_thanks_donate")
async def book_thanks_donate(callback: CallbackQuery) -> None:
    """Поддержать автора после скачивания книги"""
    await handle_book_thanks_donate(callback)
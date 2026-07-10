from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
import texts


def get_main_kb() -> InlineKeyboardMarkup:
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=texts.CHAT_BUTTON, url=config.CHAT_LINK),
        InlineKeyboardButton(text=texts.CHANNEL_BUTTON, url=config.CHANNEL_LINK)
    )
    builder.add(
        InlineKeyboardButton(text=texts.LINKS_BUTTON, callback_data="links")
    )
    builder.add(
        InlineKeyboardButton(text=texts.BOOKS_BUTTON, callback_data="books"),
        InlineKeyboardButton(text=texts.SUPPORT_BUTTON, callback_data="support")
    )
    builder.adjust(2, 1, 2)
    return builder.as_markup()


def get_links_kb() -> InlineKeyboardMarkup:
    """Все наши ссылки"""
    return get_back_kb("back:main")


def get_books_kb(books: list) -> InlineKeyboardMarkup:
    """Список книг (пользовательский)"""
    builder = InlineKeyboardBuilder()
    for book in books:
        builder.add(
            InlineKeyboardButton(
                text=f"📚 {book['title']}",
                callback_data=f"book:{book['id']}"
            )
        )
    builder.add(
        InlineKeyboardButton(text=texts.BACK_BUTTON, callback_data="back:main")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_book_kb(book_id: int) -> InlineKeyboardMarkup:
    """Карточка книги"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=texts.DOWNLOAD_BUTTON, callback_data=f"book:download:{book_id}")
    )
    builder.add(
        InlineKeyboardButton(text=texts.BACK_BUTTON, callback_data="back:books")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_support_kb() -> InlineKeyboardMarkup:
    """Раздел поддержки"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=texts.DONATORS_BUTTON, callback_data="donators")
    )
    builder.add(
        InlineKeyboardButton(text=texts.BACK_BUTTON, callback_data="back:main")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_donators_kb() -> InlineKeyboardMarkup:
    """Друзья проекта"""
    return get_back_kb("back:support")


def get_admin_kb() -> InlineKeyboardMarkup:
    """Главное меню админки"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=texts.ADMIN_BOOKS_BUTTON, callback_data="admin:books")
    )
    builder.add(
        InlineKeyboardButton(text=texts.ADMIN_DONATORS_BUTTON, callback_data="admin:donators")
    )
    builder.add(
        InlineKeyboardButton(text=texts.ADMIN_STATS_BUTTON, callback_data="admin:stats")
    )
    builder.add(
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin:settings")
    )
    builder.add(
        InlineKeyboardButton(text=texts.BACK_BUTTON, callback_data="back:main")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_admin_settings_kb() -> InlineKeyboardMarkup:
    """Меню настроек (админ)"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🔗 Ссылки", callback_data="admin:settings:links"),
        InlineKeyboardButton(text="💳 Реквизиты", callback_data="admin:settings:payments")
    )
    builder.add(
        InlineKeyboardButton(text="🔧 Технические работы", callback_data="admin:settings:maintenance")
    )
    builder.add(
        InlineKeyboardButton(text=texts.BACK_BUTTON, callback_data="back:admin")
    )
    builder.adjust(2)
    return builder.as_markup()


def get_admin_settings_links_kb() -> InlineKeyboardMarkup:
    """Меню ссылок (админ)"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📢 Канал", callback_data="settings:link:channel"),
        InlineKeyboardButton(text="💬 Чат", callback_data="settings:link:chat")
    )
    builder.add(
        InlineKeyboardButton(text="📺 YouTube", callback_data="settings:link:youtube"),
        InlineKeyboardButton(text="🎵 TikTok", callback_data="settings:link:tiktok")
    )
    builder.add(
        InlineKeyboardButton(text="📷 Instagram", callback_data="settings:link:instagram"),
        InlineKeyboardButton(text="📷 Instagram Виталия", callback_data="settings:link:instagram_vitaliy")
    )
    builder.add(
        InlineKeyboardButton(text="🎵 TikTok Любашки", callback_data="settings:link:tiktok_lyubashka"),
        InlineKeyboardButton(text="📘 Facebook", callback_data="settings:link:facebook")
    )
    builder.add(
        InlineKeyboardButton(text="🎮 Twitch", callback_data="settings:link:twitch"),
        InlineKeyboardButton(text="🌐 VK", callback_data="settings:link:vk")
    )
    builder.add(
        InlineKeyboardButton(text="📧 Email", callback_data="settings:link:email")
    )
    builder.add(
        InlineKeyboardButton(text="👁 Показать все", callback_data="settings:link:view_all")
    )
    builder.add(
        InlineKeyboardButton(text=texts.BACK_BUTTON, callback_data="back:admin:settings")
    )
    builder.adjust(2)
    return builder.as_markup()


def get_admin_settings_payments_kb() -> InlineKeyboardMarkup:
    """Меню реквизитов (админ)"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🟢 Kaspi", callback_data="settings:payment:kaspi"),
        InlineKeyboardButton(text="💳 Freedom", callback_data="settings:payment:freedom")
    )
    builder.add(
        InlineKeyboardButton(text="🏦 BCC", callback_data="settings:payment:bcc"),
        InlineKeyboardButton(text="📱 РФ номер", callback_data="settings:payment:ru_phone")
    )
    builder.add(
        InlineKeyboardButton(text="💙 PayPal", callback_data="settings:payment:paypal")
    )
    builder.add(
        InlineKeyboardButton(text="👁 Показать все", callback_data="settings:payment:view_all")
    )
    builder.add(
        InlineKeyboardButton(text=texts.BACK_BUTTON, callback_data="back:admin:settings")
    )
    builder.adjust(2)
    return builder.as_markup()


def get_admin_settings_maintenance_kb(mode: bool) -> InlineKeyboardMarkup:
    """Меню технических работ (админ)"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="🔴 Включить" if not mode else "🟢 Выключить",
            callback_data="settings:maintenance:toggle"
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="✏️ Изменить сообщение",
            callback_data="settings:maintenance:message"
        )
    )
    builder.add(
        InlineKeyboardButton(text=texts.BACK_BUTTON, callback_data="back:admin:settings")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_admin_books_kb() -> InlineKeyboardMarkup:
    """Меню управления книгами (админ)"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=texts.ADD_BOOK_BUTTON, callback_data="admin:book:add")
    )
    builder.add(
        InlineKeyboardButton(text=texts.DELETE_BOOK_BUTTON, callback_data="admin:book:delete")
    )
    builder.add(
        InlineKeyboardButton(text=texts.BACK_BUTTON, callback_data="back:admin")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_admin_delete_books_kb(books: list) -> InlineKeyboardMarkup:
    """Список книг для удаления (админ)"""
    builder = InlineKeyboardBuilder()
    for book in books:
        builder.add(
            InlineKeyboardButton(
                text=f"🗑 {book['title']}",
                callback_data=f"admin:book:delete:{book['id']}"
            )
        )
    builder.add(
        InlineKeyboardButton(text=texts.BACK_BUTTON, callback_data="back:admin:books")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_admin_donators_kb() -> InlineKeyboardMarkup:
    """Меню управления донатерами (админ)"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=texts.ADD_DONATOR_BUTTON, callback_data="admin:donator:add")
    )
    builder.add(
        InlineKeyboardButton(text=texts.DELETE_DONATOR_BUTTON, callback_data="admin:donator:delete")
    )
    builder.add(
        InlineKeyboardButton(text=texts.BACK_BUTTON, callback_data="back:admin")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_admin_delete_donators_kb(donators: list) -> InlineKeyboardMarkup:
    """Список донатеров для удаления (админ)"""
    builder = InlineKeyboardBuilder()
    for donator in donators:
        if donator.get('username'):
            text = f"🐾 {donator['name']} (@{donator['username']})"
        else:
            text = f"🐾 {donator['name']}"
        builder.add(
            InlineKeyboardButton(
                text=text,
                callback_data=f"admin:donator:delete:{donator['id']}"
            )
        )
    builder.add(
        InlineKeyboardButton(text=texts.BACK_BUTTON, callback_data="back:admin:donators")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_stats_kb() -> InlineKeyboardMarkup:
    """Статистика"""
    return get_back_kb("back:admin")


def get_back_kb(callback_data: str) -> InlineKeyboardMarkup:
    """Универсальная кнопка назад"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=texts.BACK_BUTTON, callback_data=callback_data)
    )
    builder.adjust(1)
    return builder.as_markup()


def get_cancel_kb() -> InlineKeyboardMarkup:
    """Отмена (для FSM)"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=texts.CANCEL_BUTTON, callback_data="action:cancel")
    )
    builder.adjust(1)
    return builder.as_markup()
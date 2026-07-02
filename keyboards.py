from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import config


def get_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="💬 Наш чат", url=config.CHAT_URL),
        InlineKeyboardButton(text="📢 Наш канал", url=config.CHANNEL_URL)
    )
    builder.add(
        InlineKeyboardButton(text="🌐 Все наши ссылки", callback_data="links")
    )
    builder.add(
        InlineKeyboardButton(text="📚 Книги", callback_data="books"),
        InlineKeyboardButton(text="❤️ Поддержать проект", callback_data="support")
    )
    builder.adjust(2)
    return builder.as_markup()


def get_links_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    socials = [
        ("▶️ YouTube", config.YOUTUBE_URL),
        ("📷 Instagram Виталия", config.INSTAGRAM_VITALIY),
        ("📷 Instagram Любашки", config.INSTAGRAM_LYUBASHKA),
        ("🎵 TikTok Виталия", config.TIKTOK_VITALIY),
        ("🎵 TikTok Любашки", config.TIKTOK_LYUBASHKA)
    ]
    for text, url in socials:
        if url:
            builder.add(InlineKeyboardButton(text=text, url=url))
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="main"))
    builder.adjust(2)
    return builder.as_markup()


def get_books_kb(books: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for book in books:
        builder.add(InlineKeyboardButton(
            text=book['title'],
            callback_data=f"book:info:{book['id']}"
        ))
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="main"))
    builder.adjust(2)
    return builder.as_markup()


def get_book_info_kb(book_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="⬇️ Скачать",
        callback_data=f"book:download:{book_id}"
    ))
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="books"))
    builder.adjust(1)
    return builder.as_markup()


def get_support_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="💳 Способы поддержки", callback_data="donate_methods"),
        InlineKeyboardButton(text="⭐ Друзья проекта", callback_data="donators")
    )
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="main"))
    builder.adjust(2)
    return builder.as_markup()


def get_donate_methods_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    methods = [
        ("💳 Карта", config.DONATE_CARD),
        ("💸 Kaspi", config.DONATE_KASPI),
        ("🌍 Boosty", config.DONATE_BOOSTY),
        ("☕ Другое", config.DONATE_OTHER)
    ]
    for text, url in methods:
        if url:
            builder.add(InlineKeyboardButton(text=text, url=url))
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="support"))
    builder.adjust(2)
    return builder.as_markup()


def get_donators_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="support"))
    builder.adjust(1)
    return builder.as_markup()


def get_admin_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📚 Управление книгами", callback_data="admin:books"),
        InlineKeyboardButton(text="👤 Администраторы", callback_data="admin:admins")
    )
    builder.add(
        InlineKeyboardButton(text="⚡ Триггеры", callback_data="admin:triggers"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")
    )
    builder.add(
        InlineKeyboardButton(text="📢 Рассылки", callback_data="admin:broadcast"),
        InlineKeyboardButton(text="👥 Модерация", callback_data="admin:moderation")
    )
    builder.add(
        InlineKeyboardButton(text="🎥 Новое видео", callback_data="admin:broadcast:video"),
        InlineKeyboardButton(text="⭐ Друзья проекта", callback_data="admin:donators")
    )
    builder.add(
        InlineKeyboardButton(text="📋 Логи", callback_data="admin:logs")
    )
    builder.adjust(2)
    return builder.as_markup()


def get_admin_books_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="➕ Добавить", callback_data="admin:books:add"),
        InlineKeyboardButton(text="✏️ Редактировать", callback_data="admin:books:edit")
    )
    builder.add(
        InlineKeyboardButton(text="🗑 Удалить", callback_data="admin:books:delete")
    )
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:menu"))
    builder.adjust(2)
    return builder.as_markup()


def get_admin_book_edit_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:books"))
    builder.adjust(1)
    return builder.as_markup()


def get_admin_admins_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="➕ Добавить администратора", callback_data="admin:admins:add"),
        InlineKeyboardButton(text="➖ Удалить администратора", callback_data="admin:admins:remove")
    )
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:menu"))
    builder.adjust(2)
    return builder.as_markup()


def get_admin_triggers_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="➕ Добавить триггер", callback_data="admin:triggers:add"),
        InlineKeyboardButton(text="📋 Список триггеров", callback_data="admin:triggers:list")
    )
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:menu"))
    builder.adjust(2)
    return builder.as_markup()


def get_admin_broadcast_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✍️ Обычная рассылка", callback_data="admin:broadcast:manual"),
        InlineKeyboardButton(text="📨 Переслать сообщение", callback_data="admin:broadcast:forward")
    )
    builder.add(
        InlineKeyboardButton(text="🎥 Новое видео", callback_data="admin:broadcast:video")
    )
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:menu"))
    builder.adjust(2)
    return builder.as_markup()


def get_admin_stats_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="👥 Пользователи", callback_data="admin:stats:users"),
        InlineKeyboardButton(text="💬 Сообщения", callback_data="admin:stats:messages")
    )
    builder.add(
        InlineKeyboardButton(text="📚 Книги", callback_data="admin:stats:books"),
        InlineKeyboardButton(text="📈 Активность", callback_data="admin:stats:activity")
    )
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:menu"))
    builder.adjust(2)
    return builder.as_markup()


def get_admin_moderation_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="⚠️ Предупреждение", callback_data="admin:warn"),
        InlineKeyboardButton(text="🔇 Мут", callback_data="admin:mute")
    )
    builder.add(
        InlineKeyboardButton(text="🔊 Размут", callback_data="admin:unmute"),
        InlineKeyboardButton(text="🚫 Бан", callback_data="admin:ban")
    )
    builder.add(
        InlineKeyboardButton(text="✅ Разбан", callback_data="admin:unban"),
        InlineKeyboardButton(text="📄 История", callback_data="admin:history")
    )
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:menu"))
    builder.adjust(2)
    return builder.as_markup()


def get_admin_donators_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="➕ Добавить друга проекта", callback_data="admin:donators:add"),
        InlineKeyboardButton(text="🗑 Удалить друга проекта", callback_data="admin:donators:remove")
    )
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:menu"))
    builder.adjust(2)
    return builder.as_markup()


def get_admin_logs_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:menu"))
    builder.adjust(1)
    return builder.as_markup()


def get_confirm_kb(action: str = None) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения"""
    builder = InlineKeyboardBuilder()
    
    if action:
        confirm_callback = f"confirm_{action}"
    else:
        confirm_callback = "confirm"
    
    builder.add(
        InlineKeyboardButton(text="✅ Да", callback_data=confirm_callback),
        InlineKeyboardButton(text="❌ Нет", callback_data="cancel")
    )
    builder.adjust(2)
    return builder.as_markup()


def get_cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    builder.adjust(1)
    return builder.as_markup()
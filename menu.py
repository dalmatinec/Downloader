# ========================================
# КНОПКИ И МЕНЮ
# ========================================

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Главное меню
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📱 QR код")],
        [KeyboardButton(text="🎨 QR с лого")],
        [KeyboardButton(text="💎 Купить премиум")],
        [KeyboardButton(text="💰 Цены")],
        [KeyboardButton(text="🆘 Поддержка")],
    ],
    resize_keyboard=True
)

# Инлайн-кнопка для связи с тобой
premium_button = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="💎 Купить премиум",
            url="https://t.me/kz777LLL"
        )]
    ]
)

# Кнопка для поддержки
support_button = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="📩 Написать разработчику",
            url="https://t.me/kz777LLL"
        )]
    ]
)
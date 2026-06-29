# ========================================
# КНОПКИ И ТЕКСТЫ ДЛЯ МЕНЮ
# ========================================

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Главное меню (4 кнопки)
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="QR код")],          # Простая генерация
        [KeyboardButton(text="QR с лого")],       # Генерация с картинкой
        [KeyboardButton(text="Цены")],            # Информация о тарифах
        [KeyboardButton(text="Поддержка")],       # Связь с админом
    ],
    resize_keyboard=True  # Кнопки подстраиваются под экран
)
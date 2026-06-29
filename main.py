# ========================================
# ЗАПУСК БОТА И ОБРАБОТКА КОМАНД
# ========================================

import asyncio
import tempfile
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import TOKEN, ADMIN, SUPPORT_LINK, PREMIUM_REQUEST_TEXT
from qr import generate
from menu import menu, premium_button, support_button
from db import init_db, add_user, set_premium, is_premium, get_user

# Создаем бота и диспетчер
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Инициализируем базу данных
init_db()

# Состояния (машина состояний)
class Steps(StatesGroup):
    link = State()
    logo = State()

# ========================================
# КОМАНДА /start
# ========================================

@dp.message(Command("start"))
async def start(msg):
    user_id = msg.from_user.id
    username = msg.from_user.username or "нет_ника"
    add_user(user_id, username)
    
    await msg.answer(
        "👋 Привет! Я умею генерировать QR-коды.\n\n"
        "📱 *Бесплатно:* QR без лого\n"
        "🎨 *Премиум:* QR с логотипом (100₽)\n\n"
        "Выбери действие в меню ниже.",
        parse_mode="Markdown",
        reply_markup=menu
    )

# ========================================
# КНОПКА "QR код" (БЕЗ ЛОГО)
# ========================================

@dp.message(F.text == "📱 QR код")
async def qr_no_logo(msg, state):
    await msg.answer("🔗 Кинь ссылку:")
    await state.set_state(Steps.link)
    await state.update_data(logo=False)

# ========================================
# КНОПКА "QR с лого" (С ПРОВЕРКОЙ ПРЕМИУМ)
# ========================================

@dp.message(F.text == "🎨 QR с лого")
async def qr_with_logo(msg, state):
    user_id = msg.from_user.id
    username = msg.from_user.username or "нет_ника"
    
    # Добавляем юзера в БД
    add_user(user_id, username)
    
    # Проверяем премиум
    if not is_premium(user_id):
        await msg.answer(
            "🚫 *Это премиум-функция!*\n\n"
            "💎 Купи премиум и получи:\n"
            "• QR-коды с логотипом\n"
            "• Выбор цвета QR\n"
            "• Приоритетная поддержка\n\n"
            "💰 Стоимость: 100₽ на 30 дней\n\n"
            "Нажми на кнопку ниже, чтобы оформить.",
            parse_mode="Markdown",
            reply_markup=premium_button
        )
        return
    
    await msg.answer("🔗 Сначала кинь ссылку, потом лого:")
    await state.set_state(Steps.link)
    await state.update_data(logo=True)

# ========================================
# КНОПКА "Купить премиум"
# ========================================

@dp.message(F.text == "💎 Купить премиум")
async def buy_premium(msg):
    user_id = msg.from_user.id
    username = msg.from_user.username or "нет_ника"
    
    await msg.answer(
        f"💎 *Оформление премиум-доступа*\n\n"
        f"💰 Стоимость: 100₽ на 30 дней\n\n"
        f"📦 *Что получаешь:*\n"
        f"• QR-коды с логотипом\n"
        f"• Выбор цвета QR\n"
        f"• Приоритетная поддержка\n\n"
        f"📩 *Как купить:*\n"
        f"1️⃣ Нажми на кнопку ниже\n"
        f"2️⃣ Отправь заготовленный текст\n"
        f"3️⃣ Я дам реквизиты для оплаты\n"
        f"4️⃣ После оплаты активирую премиум\n\n"
        f"Твой Telegram ID: `{user_id}`",
        parse_mode="Markdown",
        reply_markup=premium_button
    )

# ========================================
# КНОПКА "Цены"
# ========================================

@dp.message(F.text == "💰 Цены")
async def prices(msg):
    await msg.answer(
        "💰 *Тарифы:*\n\n"
        "🔹 *Бесплатно*\n"
        "  • QR-код без лого\n"
        "  • Без ограничений\n\n"
        "🔸 *Премиум — 100₽/30 дней*\n"
        "  • QR-код с логотипом\n"
        "  • Выбор цвета QR\n"
        "  • Приоритетная поддержка\n\n"
        "💎 Купить: кнопка 'Купить премиум'",
        parse_mode="Markdown"
    )

# ========================================
# КНОПКА "Поддержка"
# ========================================

@dp.message(F.text == "🆘 Поддержка")
async def support(msg):
    await msg.answer(
        "👨‍💻 *Поддержка*\n\n"
        "По всем вопросам пиши сюда:\n"
        f"{SUPPORT_LINK}\n\n"
        "Отвечаю в течение 5-10 минут.",
        parse_mode="Markdown",
        reply_markup=support_button
    )

# ========================================
# ПРИНИМАЕМ ССЫЛКУ
# ========================================

@dp.message(Steps.link)
async def get_link(msg, state):
    link = msg.text.strip()
    data = await state.get_data()
    
    if data.get("logo"):
        await state.update_data(link=link)
        await msg.answer("🖼 Теперь кинь картинку с логотипом (PNG с прозрачным фоном):")
        await state.set_state(Steps.logo)
    else:
        await msg.answer("⏳ Генерирую...")
        bio = await generate(link)
        await msg.answer_photo(
            photo=types.BufferedInputFile(bio.read(), filename="qr.png"),
            caption=f"✅ Готово: {link}"
        )
        await state.clear()

# ========================================
# ПРИНИМАЕМ КАРТИНКУ С ЛОГО
# ========================================

@dp.message(Steps.logo, F.photo)
async def get_logo(msg, state):
    data = await state.get_data()
    link = data.get("link")
    
    if not link:
        await msg.answer("❌ Ошибка, начни заново /start")
        await state.clear()
        return
    
    # Скачиваем фото
    photo = msg.photo[-1]
    file = await bot.get_file(photo.file_id)
    
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        await bot.download_file(file.file_path, tmp.name)
        tmp_path = tmp.name
    
    await msg.answer("⏳ Генерирую премиум QR...")
    
    try:
        bio = await generate(link, tmp_path)
        await msg.answer_photo(
            photo=types.BufferedInputFile(bio.read(), filename="qr.png"),
            caption=f"✨ Премиум QR готов!\n🔗 Ссылка: {link}"
        )
    except Exception as e:
        await msg.answer(f"❌ Ошибка: {e}")
    finally:
        os.unlink(tmp_path)
        await state.clear()

# ========================================
# КОМАНДА ДЛЯ АДМИНА (выдать премиум)
# ========================================

@dp.message(Command("premium"))
async def give_premium(msg):
    if msg.from_user.id != ADMIN:
        await msg.answer("🚫 Только для админа.")
        return
    
    try:
        user_id = int(msg.text.split()[1])
        set_premium(user_id)
        await msg.answer(f"✅ Премиум выдан пользователю `{user_id}` на 30 дней.", parse_mode="Markdown")
    except:
        await msg.answer("❌ Используй: /premium 123456789")

# ========================================
# КОМАНДА ДЛЯ АДМИНА (проверить статус)
# ========================================

@dp.message(Command("check"))
async def check_user(msg):
    if msg.from_user.id != ADMIN:
        await msg.answer("🚫 Только для админа.")
        return
    
    try:
        user_id = int(msg.text.split()[1])
        user = get_user(user_id)
        if user:
            status = "✅ Премиум" if user[2] == 1 else "❌ Не премиум"
            until = user[3] or "нет"
            await msg.answer(
                f"📊 *Информация о пользователе*\n\n"
                f"ID: `{user[0]}`\n"
                f"Ник: @{user[1] or 'нет'}\n"
                f"Статус: {status}\n"
                f"До: {until}",
                parse_mode="Markdown"
            )
        else:
            await msg.answer(f"❌ Пользователь {user_id} не найден")
    except:
        await msg.answer("❌ Используй: /check 123456789")

# ========================================
# ЗАПУСК БОТА
# ========================================

async def main():
    print("🚀 Бот запущен!")
    print(f"👤 Админ: @kz777LLL")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
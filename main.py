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

from config import TOKEN          # Токен из конфига
from qr import generate           # Функция генерации QR
from menu import menu             # Кнопки

# Создаем бота и диспетчер
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Состояния (машина состояний, чтобы бот помнил, что ждет от юзера)
class Steps(StatesGroup):
    link = State()   # Ждем ссылку
    logo = State()   # Ждем картинку с лого

# ========================================
# КОМАНДА /start
# ========================================
@dp.message(Command("start"))
async def start(msg):
    await msg.answer("Кидай ссылку, получу QR.", reply_markup=menu)

# ========================================
# КНОПКА "QR код" (БЕЗ ЛОГО)
# ========================================
@dp.message(F.text == "QR код")
async def qr_no_logo(msg, state):
    await msg.answer("Кинь ссылку:")
    await state.set_state(Steps.link)          # Переключаем состояние
    await state.update_data(logo=False)        # Запоминаем, что лого не нужно

# ========================================
# КНОПКА "QR с лого" (С ЛОГОТИПОМ)
# ========================================
@dp.message(F.text == "QR с лого")
async def qr_with_logo(msg, state):
    await msg.answer("Сначала ссылку, потом лого:")
    await state.set_state(Steps.link)
    await state.update_data(logo=True)         # Запоминаем, что лого нужно

# ========================================
# ПРИНИМАЕМ ССЫЛКУ (ОБЩИЙ ХЕНДЛЕР)
# ========================================
@dp.message(Steps.link)
async def get_link(msg, state):
    link = msg.text.strip()                    # Получаем ссылку
    data = await state.get_data()              # Достаем данные (нужен ли лого)
    
    if data.get("logo"):
        # Если нужен лого - сохраняем ссылку и просим картинку
        await state.update_data(link=link)
        await msg.answer("Кинь картинку с лого:")
        await state.set_state(Steps.logo)
    else:
        # Если лого не нужен - сразу генерируем QR
        await msg.answer("Генерю...")
        bio = await generate(link)
        await msg.answer_photo(
            photo=types.BufferedInputFile(bio.read(), filename="qr.png"),
            caption=f"Готово: {link}"
        )
        await state.clear()  # Очищаем состояние

# ========================================
# ПРИНИМАЕМ КАРТИНКУ С ЛОГО
# ========================================
@dp.message(Steps.logo, F.photo)
async def get_logo(msg, state):
    data = await state.get_data()
    link = data.get("link")                    # Достаем сохраненную ссылку
    
    # Скачиваем фото от пользователя
    photo = msg.photo[-1]                      # Берем самое качественное
    file = await bot.get_file(photo.file_id)
    
    # Сохраняем во временный файл
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        await bot.download_file(file.file_path, tmp.name)
        tmp_path = tmp.name
    
    # Генерируем QR с лого
    await msg.answer("Генерю...")
    bio = await generate(link, tmp_path)
    await msg.answer_photo(
        photo=types.BufferedInputFile(bio.read(), filename="qr.png"),
        caption=f"Готово с лого: {link}"
    )
    
    # Удаляем временный файл
    os.unlink(tmp_path)
    await state.clear()

# ========================================
# КНОПКА "Цены"
# ========================================
@dp.message(F.text == "Цены")
async def prices(msg):
    await msg.answer("Без лого - бесплатно.\nС лого - 100р.")

# ========================================
# КНОПКА "Поддержка"
# ========================================
@dp.message(F.text == "Поддержка")
async def support(msg):
    await msg.answer("Пиши @твой_ник")

# ========================================
# ЗАПУСК БОТА
# ========================================
async def main():
    print("Запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
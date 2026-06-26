# main.py - ЧАСТЬ 1
# ============================================
# ИМПОРТЫ, ИНИЦИАЛИЗАЦИЯ, КОМАНДЫ, ГЛАВНОЕ МЕНЮ, ПОДДЕРЖКА, ПЛАТЕЖИ
# ============================================

import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

import config
from database import Database
from utils import *
from youtube import YouTubeDownloader
from tiktok import TikTokDownloader
from payment import PaymentManager
from admin import AdminHandler, AdminStates

# Принудительная загрузка текстов
texts = load_texts()
if not texts:
    logger.error("TEXTS.JSON НЕ ЗАГРУЗИЛСЯ!")
else:
    logger.info(f"TEXTS.JSON ЗАГРУЖЕН, ключей: {len(texts)}")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
db = Database()
youtube = YouTubeDownloader()
tiktok = TikTokDownloader()
payment = PaymentManager(bot, db)
admin = AdminHandler(bot, db)

# Загрузка текстов
texts = load_texts()

# Состояния
class DownloadStates(StatesGroup):
    waiting_for_url = State()


# ============================================
# КОМАНДЫ
# ============================================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    db.add_user(user_id, message.from_user.username, message.from_user.first_name, message.from_user.last_name)
    db.check_premium_expired()
    
    user = db.get_user(user_id)
    if user and not user[4]:
        can_show, ad_text = should_show_ad(user_id, "start", db)
        if can_show:
            await message.answer(ad_text)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❤️ Поддержать проект", callback_data="support"), 
         InlineKeyboardButton(text="💼 Разработка", callback_data="development")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"), 
         InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ])

    
 try:
    await message.answer(
        texts["start"],
        parse_mode="HTML",
        reply_markup=keyboard
    )
except KeyError:
    await message.answer(
        f"❌ Ошибка: в texts.json нет ключа 'start'",
        reply_markup=keyboard
    )
except Exception as e:
    await message.answer(
        f"❌ Ошибка загрузки текста: {e}",
        reply_markup=keyboard
    )


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer(texts.get("admin_not_authorized", "⛔ Нет доступа"))
        return
    await admin.show_admin_panel(message)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(texts.get("help", "❓ Помощь").format(developer=config.DEVELOPER_USERNAME), parse_mode="HTML")


# ============================================
# ГЛАВНОЕ МЕНЮ
# ============================================

async def show_main_menu(message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if user and not user[4]:
        can_show, ad_text = should_show_ad(user_id, "menu", db)
        if can_show:
            await message.answer(ad_text)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❤️ Поддержать проект", callback_data="support"), 
         InlineKeyboardButton(text="💼 Разработка", callback_data="development")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"), 
         InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ])
    await message.answer(texts.get("main_menu", "🏠 Главное меню"), reply_markup=keyboard)


# ============================================
# CALLBACK НАВИГАЦИЯ
# ============================================

@dp.callback_query(F.data == "back_to_menu")
async def cb_back_to_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.delete()
    await show_main_menu(callback.message)


@dp.callback_query(F.data == "support")
async def cb_support(callback: CallbackQuery):
    await callback.answer()
    await show_support_menu(callback.message)


@dp.callback_query(F.data == "development")
async def cb_development(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        texts.get("development", "💼 Разработка").format(developer=config.DEVELOPER_USERNAME),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
        ])
    )


@dp.callback_query(F.data == "settings")
async def cb_settings(callback: CallbackQuery):
    await callback.answer()
    downloads = db.get_user_downloads_count(callback.from_user.id)
    await callback.message.edit_text(
        texts.get("settings", "⚙️ Настройки").format(downloads=downloads),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
        ])
    )


@dp.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        texts.get("help", "❓ Помощь").format(developer=config.DEVELOPER_USERNAME),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
        ])
    )


# ============================================
# ПОДДЕРЖКА ПРОЕКТА
# ============================================

async def show_support_menu(message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if user and user[4]:
        await message.answer(
            texts.get("already_premium", "🌟 У вас активна подписка!").format(
                until=user[5].strftime("%d.%m.%Y %H:%M") if user[5] else "",
                subscription=user[6] or ""
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
            ])
        )
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Оплатить Stars", callback_data="pay_stars")],
        [InlineKeyboardButton(text="👨‍💻 Ручная оплата", callback_data="pay_manual")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
    ])
    
    await message.answer(
        texts.get("premium_features", "").format(
            price1=config.PRICE_1_MONTH, stars1=config.STARS_1_MONTH,
            price3=config.PRICE_3_MONTH, stars3=config.STARS_3_MONTH,
            price6=config.PRICE_6_MONTH, stars6=config.STARS_6_MONTH,
            price12=config.PRICE_12_MONTH, stars12=config.STARS_12_MONTH,
            pricelife=config.PRICE_LIFETIME, starslife=config.STARS_LIFETIME
        ),
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "pay_stars")
async def cb_pay_stars(callback: CallbackQuery):
    await callback.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 месяц - 215 ⭐", callback_data="sub_30_stars")],
        [InlineKeyboardButton(text="3 месяца - 560 ⭐", callback_data="sub_90_stars")],
        [InlineKeyboardButton(text="6 месяцев - 855 ⭐", callback_data="sub_180_stars")],
        [InlineKeyboardButton(text="12 месяцев - 1500 ⭐", callback_data="sub_365_stars")],
        [InlineKeyboardButton(text="Навсегда - 3000 ⭐", callback_data="sub_99999_stars")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="support")]
    ])
    await callback.message.edit_text("💳 Выберите срок:", reply_markup=keyboard)


@dp.callback_query(F.data == "pay_manual")
async def cb_pay_manual(callback: CallbackQuery):
    await callback.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍💻 Связаться с разработчиком", url="https://t.me/kz777LLL")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="support")]
    ])
    await callback.message.edit_text(
        "👨‍💻 Ручная оплата\n\n💰 Стоимость: от 2500 ₸\n📅 Срок: 1 месяц, 3 месяца, 6 месяцев, 12 месяцев, Навсегда\n\nНажмите на кнопку ниже, чтобы связаться с разработчиком.",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("sub_"))
async def cb_subscription(callback: CallbackQuery):
    await callback.answer()
    data = callback.data.split("_")
    days = int(data[1])
    payment_type = data[2]
    user_id = callback.from_user.id
    
    if payment_type == "stars":
        await payment.process_stars_payment(callback.message, user_id, days)
    else:
        price = get_subscription_price(days)
        sub_text = get_subscription_type_text(days)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👨‍💻 Связаться с разработчиком", url="https://t.me/kz777LLL")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="support")]
        ])
        await callback.message.edit_text(
            f"👨‍💻 Ручная оплата\n\n💰 {price} ₸\n📅 {sub_text}\n\nНажмите на кнопку ниже, чтобы оплатить.",
            reply_markup=keyboard
        )


# ============================================
# ПЛАТЕЖИ (STARS)
# ============================================

@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: types.PreCheckoutQuery):
    await payment.process_pre_checkout(pre_checkout_query)


@dp.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    await payment.process_successful_payment(message)


# ============================================
# КОНЕЦ ЧАСТИ 1
# ============================================
# main.py - ЧАСТЬ 2
# ============================================
# ОБРАБОТКА ССЫЛОК, КАЧЕСТВА, СКАЧИВАНИЕ, АДМИН, ЗАПУСК
# ============================================

@dp.message(StateFilter(DownloadStates.waiting_for_url))
async def handle_url(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    can_proceed, flood_message = check_flood(user_id)
    if not can_proceed:
        await message.answer(flood_message)
        return
    
    url = message.text.strip()
    
    if not url.startswith(('http://', 'https://')):
        await message.answer(texts.get("invalid_url", "❌ Отправьте корректную ссылку"))
        return
    
    platform = detect_platform(url)
    
    if platform == 'unknown':
        await message.answer(texts.get("unsupported_platform", "❌ Платформа не поддерживается"))
        return
    
    wait_msg = await message.answer(texts.get("processing", "⏳ Обрабатываю ссылку..."))
    
    try:
        if platform == 'youtube':
            info = youtube.get_video_info(url)
        elif platform == 'tiktok':
            info = tiktok.get_video_info(url)
        else:
            await wait_msg.delete()
            await message.answer(texts.get("unsupported_platform", "❌ Платформа не поддерживается"))
            return
        
        if not info:
            await wait_msg.delete()
            await message.answer(texts.get("download_error", "❌ Ошибка получения информации"))
            return
        
        await state.update_data({
            'url': url,
            'platform': platform,
            'info': info
        })
        
        duration_str = format_duration(info.get('duration', 0))
        views = info.get('view_count', 0)
        views_str = f"{views/1000000:.1f}M" if views > 1000000 else f"{views/1000:.1f}K" if views > 1000 else str(views)
        
        info_text = texts.get("video_info", "📹 {title}").format(
            title=info.get('title', 'Без названия')[:100],
            uploader=info.get('uploader', 'Неизвестно'),
            duration=duration_str,
            views=views_str
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎬 Доступные качества", callback_data="show_qualities")],
            [InlineKeyboardButton(text="🎵 MP3", callback_data="download_mp3")],
            [InlineKeyboardButton(text="🖼 Превью", callback_data="show_thumbnail")],
            [InlineKeyboardButton(text="ℹ️ Информация", callback_data="show_info")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
        ])
        
        await wait_msg.delete()
        await message.answer(info_text, parse_mode="HTML", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка обработки ссылки: {e}")
        await wait_msg.delete()
        await message.answer(texts.get("download_error", "❌ Произошла ошибка"))


@dp.callback_query(F.data == "show_qualities")
async def cb_show_qualities(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    data = await state.get_data()
    info = data.get('info')
    
    if not info:
        await callback.message.answer(texts.get("download_error", "❌ Ошибка"))
        return
    
    formats = info.get('formats', [])
    if not formats:
        await callback.message.answer(texts.get("no_qualities", "❌ Нет доступных качеств"))
        return
    
    keyboard_buttons = []
    for f in formats:
        quality = f.get('quality', 'Unknown')
        size = format_size(f.get('filesize', 0))
        keyboard_buttons.append([InlineKeyboardButton(
            text=f"{quality} ({size})",
            callback_data=f"quality_{f.get('format_id', 'best')}"
        )])
    
    keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_video")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.edit_text(
        texts.get("select_quality", "🎬 Выберите качество:"),
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "back_to_video")
async def cb_back_to_video(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(texts.get("download_prompt", "📥 Отправьте ссылку на видео:"))


@dp.callback_query(F.data.startswith("quality_"))
async def cb_download_quality(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    format_id = callback.data.replace("quality_", "")
    data = await state.get_data()
    url = data.get('url')
    platform = data.get('platform')
    info = data.get('info')
    
    if not url:
        await callback.message.answer(texts.get("download_error", "❌ Ошибка"))
        return
    
    selected_format = None
    for f in info.get('formats', []):
        if f.get('format_id') == format_id:
            selected_format = f
            break
    
    quality_text = selected_format.get('quality', 'Unknown') if selected_format else format_id
    size_text = format_size(selected_format.get('filesize', 0)) if selected_format else 'Unknown'
    
    await callback.message.edit_text(
        texts.get("downloading", "⬇️ Скачиваю...").format(
            quality=quality_text,
            size=size_text
        )
    )
    
    try:
        if platform == 'youtube':
            filepath = youtube.download_video(url, format_id)
        elif platform == 'tiktok':
            filepath = tiktok.download_video(url, format_id)
        else:
            await callback.message.answer(texts.get("download_error", "❌ Ошибка"))
            return
        
        if not filepath:
            await callback.message.answer(texts.get("download_error", "❌ Ошибка скачивания"))
            return
        
        file_size = os.path.getsize(filepath)
        title = info.get('title', 'video')[:50]
        
        await callback.message.delete()
        
        video_file = FSInputFile(filepath)
        await callback.message.answer_video(
            video=video_file,
            caption=f"✅ Видео готово!\n\n📹 {title}\n🎬 {quality_text}\n📦 {format_size(file_size)}"
        )
        
        user_id = callback.from_user.id
        user = db.get_user(user_id)
        if user and not user[4]:
            can_show, ad_text = should_show_ad(user_id, "after_download", db)
            if can_show:
                await callback.message.answer(ad_text)
        
        db.add_download(user_id, platform, 'video', quality_text, file_size)
        
        if config.DELETE_AFTER_SEND:
            delete_file(filepath)
        
    except Exception as e:
        logger.error(f"Ошибка скачивания: {e}")
        await callback.message.answer(texts.get("download_error", "❌ Ошибка скачивания"))


@dp.callback_query(F.data == "download_mp3")
async def cb_download_mp3(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    data = await state.get_data()
    url = data.get('url')
    platform = data.get('platform')
    info = data.get('info')
    
    if not url:
        await callback.message.answer(texts.get("download_error", "❌ Ошибка"))
        return
    
    await callback.message.edit_text("🎵 Скачиваю аудио...")
    
    try:
        if platform == 'youtube':
            filepath = youtube.download_audio(url)
        elif platform == 'tiktok':
            filepath = tiktok.download_audio(url)
        else:
            await callback.message.answer(texts.get("download_error", "❌ Ошибка"))
            return
        
        if not filepath:
            await callback.message.answer(texts.get("download_error", "❌ Ошибка скачивания"))
            return
        
        file_size = os.path.getsize(filepath)
        title = info.get('title', 'audio')[:50]
        
        await callback.message.delete()
        
        audio_file = FSInputFile(filepath)
        await callback.message.answer_audio(
            audio=audio_file,
            title=title,
            performer=info.get('uploader', 'Unknown')
        )
        
        await callback.message.answer(f"✅ Аудио готово!\n\n🎵 {title}\n📦 {format_size(file_size)}")
        
        user_id = callback.from_user.id
        user = db.get_user(user_id)
        if user and not user[4]:
            can_show, ad_text = should_show_ad(user_id, "after_download", db)
            if can_show:
                await callback.message.answer(ad_text)
        
        db.add_download(user_id, platform, 'audio', 'MP3', file_size)
        
        if config.DELETE_AFTER_SEND:
            delete_file(filepath)
        
    except Exception as e:
        logger.error(f"Ошибка скачивания MP3: {e}")
        await callback.message.answer(texts.get("download_error", "❌ Ошибка скачивания"))


@dp.callback_query(F.data == "show_thumbnail")
async def cb_show_thumbnail(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    data = await state.get_data()
    url = data.get('url')
    platform = data.get('platform')
    info = data.get('info')
    
    if not url:
        await callback.message.answer(texts.get("download_error", "❌ Ошибка"))
        return
    
    await callback.message.edit_text("🖼 Загружаю превью...")
    
    try:
        if platform == 'youtube':
            filepath = youtube.download_thumbnail(url)
        elif platform == 'tiktok':
            filepath = tiktok.download_thumbnail(url)
        else:
            await callback.message.answer(texts.get("download_error", "❌ Ошибка"))
            return
        
        if not filepath:
            await callback.message.answer("❌ Не удалось загрузить превью")
            return
        
        await callback.message.delete()
        
        photo_file = FSInputFile(filepath)
        title = info.get('title', 'Видео')[:100]
        
        await callback.message.answer_photo(
            photo=photo_file,
            caption=texts.get("thumbnail_success", "🖼 Превью").format(title=title)
        )
        
        if config.DELETE_AFTER_SEND:
            delete_file(filepath)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки превью: {e}")
        await callback.message.answer("❌ Ошибка загрузки превью")


@dp.callback_query(F.data == "show_info")
async def cb_show_info(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    data = await state.get_data()
    info = data.get('info')
    
    if not info:
        await callback.message.answer("❌ Нет информации")
        return
    
    duration_str = format_duration(info.get('duration', 0))
    views = info.get('view_count', 0)
    views_str = f"{views/1000000:.1f}M" if views > 1000000 else f"{views/1000:.1f}K" if views > 1000 else str(views)
    
    info_text = texts.get("info_text", "ℹ️ Информация").format(
        title=info.get('title', 'Без названия'),
        uploader=info.get('uploader', 'Неизвестно'),
        duration=duration_str,
        views=views_str,
        date=datetime.now().strftime("%d.%m.%Y"),
        description=info.get('description', 'Нет описания')[:200]
    )
    
    await callback.message.edit_text(
        info_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_video")]
        ])
    )


# ============================================
# АДМИН CALLBACK
# ============================================

@dp.callback_query(F.data.startswith("admin_"))
async def handle_admin_callbacks(callback: CallbackQuery, state: FSMContext):
    await admin.handle_admin_callback(callback, state)


@dp.message(StateFilter(AdminStates.waiting_for_user_id))
async def process_admin_user_id(message: Message, state: FSMContext):
    await admin.process_user_id(message, state)


@dp.message(StateFilter(AdminStates.waiting_for_broadcast))
async def process_admin_broadcast(message: Message, state: FSMContext):
    await admin.process_broadcast(message, state)


@dp.callback_query(F.data == "admin_panel")
async def callback_admin_panel(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await admin.show_admin_panel(callback.message)


# ============================================
# ЗАПУСК БОТА
# ============================================

async def main():
    clean_temp_folder()
    logger.info("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    finally:
        db.close()


# ============================================
# КОНЕЦ ЧАСТИ 2
# ============================================
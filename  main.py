# main.py
import asyncio
import logging
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
from admin import AdminHandler

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
    choosing_quality = State()
    choosing_action = State()

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_user_id = State()
    waiting_for_subscription_type = State()

# ==================== ОБРАБОТЧИКИ КОМАНД ====================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    # Добавляем пользователя в БД
    db.add_user(user_id, username, first_name, last_name)
    db.update_user_activity(user_id)
    
    # Проверяем истекшие подписки
    db.check_premium_expired()
    
    # Клавиатура главного меню
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Скачать", callback_data="download")],
        [InlineKeyboardButton(text="❤️ Поддержать проект", callback_data="support")],
        [InlineKeyboardButton(text="💼 Разработка", callback_data="development")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ])
    
    # Проверка подписки
    user = db.get_user(user_id)
    is_premium = user[4] if user else False
    
    welcome_text = texts.get("start", "👋 Добро пожаловать!")
    if is_premium:
        welcome_text += "\n\n🌟 У вас активная подписка!"
    
    await message.answer(welcome_text, reply_markup=keyboard)

@dp.message(Command("download"))
async def cmd_download(message: Message, state: FSMContext):
    """Обработчик команды /download"""
    await state.set_state(DownloadStates.waiting_for_url)
    await message.answer(texts.get("download_prompt", "📥 Отправьте ссылку на видео:"))

@dp.message(Command("support"))
async def cmd_support(message: Message):
    """Обработчик команды /support"""
    await show_support_menu(message)

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = texts.get("help", "❓ Помощь").format(developer=config.DEVELOPER_USERNAME)
    await message.answer(help_text, parse_mode="HTML")

# ==================== ОБРАБОТЧИКИ CALLBACK ====================

@dp.callback_query(F.data == "download")
async def callback_download(callback: CallbackQuery, state: FSMContext):
    """Кнопка Скачать"""
    await callback.answer()
    await state.set_state(DownloadStates.waiting_for_url)
    await callback.message.edit_text(
        texts.get("download_prompt", "📥 Отправьте ссылку на видео:"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
        ])
    )

@dp.callback_query(F.data == "support")
async def callback_support(callback: CallbackQuery):
    """Кнопка Поддержать проект"""
    await callback.answer()
    await show_support_menu(callback.message)

@dp.callback_query(F.data == "development")
async def callback_development(callback: CallbackQuery):
    """Кнопка Разработка"""
    await callback.answer()
    dev_text = texts.get("development", "💼 Разработка").format(developer=config.DEVELOPER_USERNAME)
    await callback.message.edit_text(
        dev_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
        ])
    )

@dp.callback_query(F.data == "settings")
async def callback_settings(callback: CallbackQuery):
    """Кнопка Настройки"""
    await callback.answer()
    user_id = callback.from_user.id
    downloads_count = db.get_user_downloads_count(user_id)
    
    settings_text = texts.get("settings", "⚙️ Настройки").format(downloads=downloads_count)
    await callback.message.edit_text(
        settings_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
        ])
    )

@dp.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Кнопка Помощь"""
    await callback.answer()
    help_text = texts.get("help", "❓ Помощь").format(developer=config.DEVELOPER_USERNAME)
    await callback.message.edit_text(
        help_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
        ])
    )

@dp.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: CallbackQuery):
    """Кнопка Назад в главное меню"""
    await callback.answer()
    await show_main_menu(callback.message)

@dp.callback_query(F.data == "back_to_video")
async def callback_back_to_video(callback: CallbackQuery, state: FSMContext):
    """Кнопка Назад к видео"""
    await callback.answer()
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(texts.get("download_prompt", "📥 Отправьте ссылку на видео:"))

# ==================== ПОДДЕРЖКА ПРОЕКТА ====================

async def show_support_menu(message: Message):
    """Показать меню поддержки"""
    user_id = message.from_user.id
    user = db.get_user(user_id)
    is_premium = user[4] if user else False
    
    if is_premium:
        premium_until = user[5]
        sub_type = user[6]
        if premium_until:
            until_str = premium_until.strftime("%d.%m.%Y %H:%M")
            await message.answer(
                texts.get("already_premium", "🌟 У вас активная подписка!").format(
                    until=until_str,
                    subscription=sub_type
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
                ])
            )
            return
    
    # Формируем цены
    price_text = texts.get("premium_features", "").format(
        price1=config.PRICE_1_MONTH,
        stars1=config.STARS_1_MONTH,
        price3=config.PRICE_3_MONTH,
        stars3=config.STARS_3_MONTH,
        price6=config.PRICE_6_MONTH,
        stars6=config.STARS_6_MONTH,
        price12=config.PRICE_12_MONTH,
        stars12=config.STARS_12_MONTH,
        pricelife=config.PRICE_LIFETIME,
        starslife=config.STARS_LIFETIME
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Оплатить Stars", callback_data="pay_stars")],
        [InlineKeyboardButton(text="👨‍💻 Оплатить напрямую", callback_data="pay_manual")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
    ])
    
    await message.answer(price_text, parse_mode="HTML", reply_markup=keyboard)

@dp.callback_query(F.data == "pay_stars")
async def callback_pay_stars(callback: CallbackQuery):
    """Оплата через Telegram Stars"""
    await callback.answer()
    await show_subscription_options(callback.message, "stars")

@dp.callback_query(F.data == "pay_manual")
async def callback_pay_manual(callback: CallbackQuery):
    """Ручная оплата"""
    await callback.answer()
    
    manual_text = texts.get("payment_manual", "👨‍💻 Ручная оплата").format(
        developer=config.DEVELOPER_USERNAME,
        price=config.PRICE_1_MONTH
    )
    
    await callback.message.edit_text(
        manual_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="support")]
        ])
    )

async def show_subscription_options(message: Message, payment_type: str):
    """Показать варианты подписки"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 месяц - 2500 ₸ (215 ⭐)", callback_data=f"sub_30_{payment_type}")],
        [InlineKeyboardButton(text="3 месяца - 6500 ₸ (560 ⭐)", callback_data=f"sub_90_{payment_type}")],
        [InlineKeyboardButton(text="6 месяцев - 10000 ₸ (855 ⭐)", callback_data=f"sub_180_{payment_type}")],
        [InlineKeyboardButton(text="12 месяцев - 17500 ₸ (1500 ⭐)", callback_data=f"sub_365_{payment_type}")],
        [InlineKeyboardButton(text="Навсегда - 35000 ₸ (3000 ⭐)", callback_data=f"sub_99999_{payment_type}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="support")]
    ])
    
    await message.edit_text(
        texts.get("payment_options", "💳 Выберите срок подписки:"),
        reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("sub_"))
async def callback_subscription(callback: CallbackQuery):
    """Обработка выбора подписки"""
    await callback.answer()
    
    data = callback.data.split("_")
    days = int(data[1])
    payment_type = data[2]
    user_id = callback.from_user.id
    
    if payment_type == "stars":
        # Оплата через Stars
        await payment.process_stars_payment(callback.message, user_id, days)
    else:
        # Ручная оплата
        price = get_subscription_price(days)
        sub_text = get_subscription_type_text(days)
        
        manual_text = texts.get("payment_manual", "👨‍💻 Ручная оплата").format(
            developer=config.DEVELOPER_USERNAME,
            price=price
        )
        manual_text += f"\n\n📅 Подписка: {sub_text}"
        
        await callback.message.edit_text(
            manual_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="support")]
            ])
        )

# ==================== ОБРАБОТЧИКИ СООБЩЕНИЙ ====================

@dp.message(StateFilter(DownloadStates.waiting_for_url))
async def handle_url(message: Message, state: FSMContext):
    """Обработка ссылки от пользователя"""
    user_id = message.from_user.id
    
    # Антифлуд
    can_proceed, flood_message = check_flood(user_id)
    if not can_proceed:
        await message.answer(flood_message)
        return
    
    url = message.text.strip()
    
    # Проверяем, что это ссылка
    if not url.startswith(('http://', 'https://')):
        await message.answer(texts.get("invalid_url", "❌ Отправьте корректную ссылку"))
        return
    
    # Определяем платформу
    platform = detect_platform(url)
    
    if platform == 'unknown':
        await message.answer(texts.get("unsupported_platform", "❌ Платформа не поддерживается"))
        return
    
    # Отправляем сообщение о начале обработки
    wait_msg = await message.answer(texts.get("processing", "⏳ Обрабатываю ссылку..."))
    
    try:
        # Получаем информацию о видео
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
        
        # Сохраняем информацию в состояние
        await state.update_data({
            'url': url,
            'platform': platform,
            'info': info
        })
        
        # Формируем сообщение с информацией
        duration_str = format_duration(info.get('duration', 0))
        views = info.get('view_count', 0)
        if views > 1000000:
            views_str = f"{views/1000000:.1f}M"
        elif views > 1000:
            views_str = f"{views/1000:.1f}K"
        else:
            views_str = str(views)
        
        info_text = texts.get("video_info", "📹 {title}").format(
            title=info.get('title', 'Без названия')[:100],
            uploader=info.get('uploader', 'Неизвестно'),
            duration=duration_str,
            views=views_str
        )
        
        # Клавиатура действий
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
async def callback_show_qualities(callback: CallbackQuery, state: FSMContext):
    """Показать доступные качества"""
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
    
    # Формируем кнопки с качествами
    keyboard_buttons = []
    for f in formats:
        quality = f.get('quality', 'Unknown')
        size = format_size(f.get('filesize', 0))
        button_text = f"{quality} ({size})"
        keyboard_buttons.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"quality_{f.get('format_id', 'best')}"
        )])
    
    keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_video")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.edit_text(
        texts.get("select_quality", "🎬 Выберите качество:"),
        reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("quality_"))
async def callback_download_quality(callback: CallbackQuery, state: FSMContext):
    """Скачать видео выбранного качества"""
    await callback.answer()
    
    format_id = callback.data.replace("quality_", "")
    data = await state.get_data()
    url = data.get('url')
    platform = data.get('platform')
    info = data.get('info')
    
    if not url:
        await callback.message.answer(texts.get("download_error", "❌ Ошибка"))
        return
    
    # Находим качество
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
        # Скачиваем видео
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
        
        # Отправляем видео
        file_size = os.path.getsize(filepath)
        title = info.get('title', 'video')[:50]
        
        await callback.message.delete()
        
        await callback.message.answer(
            texts.get("download_success", "✅ Видео готово!").format(
                title=title,
                quality=quality_text,
                size=format_size(file_size)
            ),
            parse_mode="HTML"
        )
        
        # Отправляем файл
        video_file = FSInputFile(filepath)
        await callback.message.answer_video(
            video=video_file,
            caption=f"📹 {title}\n🎬 {quality_text}\n📦 {format_size(file_size)}"
        )
        
        # Логируем скачивание
        db.add_download(callback.from_user.id, platform, 'video', quality_text, file_size)
        
        # Удаляем файл
        if config.DELETE_AFTER_SEND:
            delete_file(filepath)
        
    except Exception as e:
        logger.error(f"Ошибка скачивания: {e}")
        await callback.message.answer(texts.get("download_error", "❌ Ошибка скачивания"))

@dp.callback_query(F.data == "download_mp3")
async def callback_download_mp3(callback: CallbackQuery, state: FSMContext):
    """Скачать аудио"""
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
        # Скачиваем аудио
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
        
        await callback.message.answer(
            texts.get("mp3_success", "🎵 Аудио готово!").format(
                title=title,
                size=format_size(file_size)
            ),
            parse_mode="HTML"
        )
        
        # Отправляем аудио
        audio_file = FSInputFile(filepath)
        await callback.message.answer_audio(
            audio=audio_file,
            title=title,
            performer=info.get('uploader', 'Unknown')
        )
        
        # Логируем
        db.add_download(callback.from_user.id, platform, 'audio', 'MP3', file_size)
        
        if config.DELETE_AFTER_SEND:
            delete_file(filepath)
        
    except Exception as e:
        logger.error(f"Ошибка скачивания MP3: {e}")
        await callback.me
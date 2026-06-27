import asyncio
import logging
import os
from datetime import datetime
from dataclasses import dataclass, field

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    PreCheckoutQuery, SuccessfulPayment,
    URLInputFile,
)
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

import database as db
import admin as admin_module
import payment as pay
import youtube as yt
import tiktok as tt
from utils import (
    detect_platform, format_duration, format_views,
    format_size, format_date, format_subscription_type,
    load_ads, should_show_ad, get_ad_text, clean_temp_file,
)
from config import (
    BOT_TOKEN, ADMIN_ID, DEVELOPER_USERNAME,
    FLOOD_SECONDS, LOG_FILE, DELETE_AFTER_SEND,
    MAX_SIMULTANEOUS_DOWNLOADS, QUEUE_MESSAGE,
)

# ─── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ─── Bot & Dispatcher ──────────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# ─── Flood control ────────────────────────────────────────────────────────────
flood_map: dict[int, float] = {}


def is_flooded(user_id: int) -> bool:
    import time
    now = time.time()
    last = flood_map.get(user_id, 0)
    if now - last < FLOOD_SECONDS:
        return True
    flood_map[user_id] = now
    return False


# ─── FSM ──────────────────────────────────────────────────────────────────────
class VideoState(StatesGroup):
    waiting_quality = State()


# ─── Download queue ────────────────────────────────────────────────────────────
@dataclass
class QueueEntry:
    user_id: int
    event: asyncio.Event = field(default_factory=asyncio.Event)


# Активные загрузки обычных пользователей
_active_downloads: set[int] = set()
# Очередь обычных пользователей
_download_queue: list[QueueEntry] = []
_queue_lock = asyncio.Lock()


async def _try_dispatch():
    """Запускает следующих из очереди пока есть свободные слоты."""
    async with _queue_lock:
        while (
            _download_queue
            and len(_active_downloads) < MAX_SIMULTANEOUS_DOWNLOADS
        ):
            entry = _download_queue[0]
            if entry.user_id in _active_downloads:
                _download_queue.pop(0)
                continue
            _download_queue.pop(0)
            _active_downloads.add(entry.user_id)
            entry.event.set()


async def _release_slot(user_id: int):
    """Освобождает слот и будит следующего в очереди."""
    async with _queue_lock:
        _active_downloads.discard(user_id)
    await _try_dispatch()


async def acquire_download_slot(user_id: int, status_msg) -> None:
    """
    Премиум — проходит без очереди мгновенно.
    Обычный — ждёт свободного слота, периодически обновляет позицию в сообщении.
    """
    if db.is_premium(user_id):
        return

    # Есть свободный слот — занимаем сразу
    async with _queue_lock:
        if (
            len(_active_downloads) < MAX_SIMULTANEOUS_DOWNLOADS
            and user_id not in _active_downloads
        ):
            _active_downloads.add(user_id)
            return

    # Свободных слотов нет — встаём в очередь
    entry = QueueEntry(user_id=user_id)
    async with _queue_lock:
        _download_queue.append(entry)

    # Ждём своего слота, периодически обновляя позицию
    while True:
        async with _queue_lock:
            try:
                pos = _download_queue.index(entry) + 1
            except ValueError:
                # Нас вытащили из очереди через _try_dispatch
                break

        try:
            await status_msg.edit_text(QUEUE_MESSAGE.format(position=pos))
        except Exception:
            pass

        try:
            await asyncio.wait_for(asyncio.shield(entry.event.wait()), timeout=5)
            break
        except asyncio.TimeoutError:
            continue


# ─── In-memory video cache ────────────────────────────────────────────────────
# url_hash -> { url, platform, info, qualities }
video_cache: dict[str, dict] = {}


def make_url_hash(url: str) -> str:
    import hashlib
    return hashlib.md5(url.encode()).hexdigest()[:10]


# ─── Keyboards ────────────────────────────────────────────────────────────────
def main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❤️ Поддержать проект", callback_data="support"),
            InlineKeyboardButton(text="💼 Разработка", callback_data="dev"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"),
            InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
        ],
    ])


def back_kb(target: str = "start") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_{target}")]
    ])


def support_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐ Оплатить Stars", callback_data="pay_stars"),
            InlineKeyboardButton(text="👨‍💻 Ручная оплата", callback_data="pay_manual"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_start")],
    ])


def stars_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1 месяц - 215 ⭐", callback_data="stars_1_month"),
            InlineKeyboardButton(text="3 месяца - 560 ⭐", callback_data="stars_3_months"),
        ],
        [
            InlineKeyboardButton(text="6 месяцев - 855 ⭐", callback_data="stars_6_months"),
            InlineKeyboardButton(text="12 месяцев - 1500 ⭐", callback_data="stars_12_months"),
        ],
        [InlineKeyboardButton(text="Навсегда - 3000 ⭐", callback_data="stars_lifetime")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_support")],
    ])


def video_actions_kb(url_hash: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 Качества", callback_data=f"qualities_{url_hash}"),
            InlineKeyboardButton(text="🎵 MP3", callback_data=f"mp3_{url_hash}"),
            InlineKeyboardButton(text="🖼 Превью", callback_data=f"thumb_{url_hash}"),
            InlineKeyboardButton(text="ℹ️ Информация", callback_data=f"info_{url_hash}"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_start")],
    ])


def qualities_kb(url_hash: str, qualities: list) -> InlineKeyboardMarkup:
    rows = []
    for q in qualities:
        size_str = format_size(q["filesize"]) if q["filesize"] else ""
        label = q["label"]
        if size_str:
            label += f" • {size_str}"
        rows.append([InlineKeyboardButton(
            text=label,
            callback_data=f"dl_{url_hash}_{q['format_id']}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_video_{url_hash}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─── Texts ────────────────────────────────────────────────────────────────────
START_TEXT = (
    "👋 Добро пожаловать в VideoDownloaderBot!\n\n"
    "Я помогу вам скачать видео с YouTube и TikTok.\n\n"
    "📥 Просто отправьте мне ссылку на видео, и я скачаю его для вас.\n\n"
    "Доступные платформы:\n"
    "✅ YouTube\n"
    "✅ YouTube Shorts\n"
    "✅ TikTok"
)

SUPPORT_TEXT = (
    "❤️ Поддержать проект\n\n"
    "Спасибо, что пользуетесь ботом!\n\n"
    "Каждая ваша поддержка помогает оплачивать сервер, развивать проект, "
    "повышать скорость работы и добавлять новые платформы.\n\n"
    "В знак благодарности вы получите:\n\n"
    "🚫 Полное отключение рекламы\n"
    "⚡ Приоритетную обработку запросов\n"
    "📥 Одновременное скачивание нескольких файлов\n"
    "📃 Скачивание YouTube-плейлистов\n"
    "🆕 Ранний доступ ко всем новым функциям\n\n"
    "Выберите удобный срок поддержки ниже.\n\n"
    "💰 Цены:\n\n"
    "1 месяц - 2500 ₸ (215 ⭐)\n"
    "3 месяца - 6500 ₸ (560 ⭐)\n"
    "6 месяцев - 10000 ₸ (855 ⭐)\n"
    "12 месяцев - 17500 ₸ (1500 ⭐)\n"
    "Навсегда - 35000 ₸ (3000 ⭐)"
)

STARS_TEXT = "💳 Выберите срок:"

MANUAL_PAY_TEXT = (
    "👨‍💻 Ручная оплата\n\n"
    "💰 Стоимость: от 2500 ₸\n"
    "📅 Срок: 1 месяц, 3 месяца, 6 месяцев, 12 месяцев, Навсегда\n\n"
    "Нажмите на кнопку ниже, чтобы связаться с разработчиком."
)

DEV_TEXT = (
    "💼 Разработка\n\n"
    "Предлагаю услуги по разработке:\n\n"
    "🤖 Telegram-ботов\n"
    "🌐 Сайтов\n"
    "⚙️ Автоматизации\n"
    "🛒 Интернет-магазинов\n"
    "📊 CRM\n"
    "🔗 API\n"
    "☁️ VPS\n"
    "🧩 Индивидуальных решений\n\n"
    f"📩 Связь: {DEVELOPER_USERNAME}"
)

HELP_TEXT = (
    "❓ Помощь\n\n"
    "Как использовать бота:\n\n"
    "1️⃣ Отправьте ссылку на видео с YouTube или TikTok\n"
    "2️⃣ Бот автоматически определит платформу\n"
    "3️⃣ Выберите качество для скачивания\n"
    "4️⃣ Получите видео или аудио\n\n"
    "Доступные команды:\n"
    "/start - Главное меню\n"
    "/help - Помощь\n\n"
    "Поддерживаемые платформы:\n"
    "✅ YouTube\n"
    "✅ YouTube Shorts\n"
    "✅ TikTok\n\n"
    f"Вопросы и предложения: {DEVELOPER_USERNAME}"
)


def settings_text(downloads: int) -> str:
    return (
        f"⚙️ Настройки\n\n"
        f"📊 Статистика ваших скачиваний: {downloads}\n\n"
        "Дополнительные настройки будут добавлены позже."
    )


def active_sub_text(until: str, sub_type: str) -> str:
    return (
        f"🌟 У вас активная подписка!\n\n"
        f"Срок действия: {until}\n"
        f"Тип: {sub_type}\n\n"
        "Спасибо за поддержку проекта! ❤️"
    )


def video_info_short(info: dict) -> str:
    title = info.get("title", "Неизвестно")
    uploader = info.get("uploader") or info.get("channel") or "Неизвестно"
    duration = format_duration(info.get("duration"))
    views = format_views(info.get("view_count"))
    return (
        f"📹 {title}\n\n"
        f"👤 Автор: {uploader}\n"
        f"⏱ Длительность: {duration}\n"
        f"📊 Просмотров: {views}"
    )


def video_info_full(info: dict) -> str:
    title = info.get("title", "Неизвестно")
    uploader = info.get("uploader") or info.get("channel") or "Неизвестно"
    duration = format_duration(info.get("duration"))
    views = format_views(info.get("view_count"))
    date = format_date(info.get("upload_date"))
    description = info.get("description") or "Нет описания"
    if len(description) > 500:
        description = description[:500] + "..."
    return (
        f"ℹ️ Информация о видео\n\n"
        f"📹 Название: {title}\n"
        f"👤 Автор: {uploader}\n"
        f"⏱ Длительность: {duration}\n"
        f"📊 Просмотров: {views}\n"
        f"📅 Дата загрузки: {date}\n\n"
        f"📝 Описание:\n{description}"
    )


def caption_video(title: str, quality: str, size: str) -> str:
    return (
        f"✅ Видео готово!\n\n"
        f"📹 {title}\n"
        f"🎬 {quality}\n"
        f"📦 {size}"
    )


def caption_audio(title: str, size: str) -> str:
    return (
        f"✅ Аудио готово!\n\n"
        f"🎵 {title}\n"
        f"📦 {size}"
    )


def caption_thumb(title: str) -> str:
    return f"🖼 Превью\n\n{title}"


# ─── Helpers ──────────────────────────────────────────────────────────────────
async def safe_edit(call: CallbackQuery, text: str, reply_markup=None):
    try:
        await call.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest:
        pass


async def maybe_send_ad(user_id: int, placement: str):
    if db.is_premium(user_id):
        return
    ads = load_ads()
    if should_show_ad(ads, placement):
        text = get_ad_text(ads, placement)
        if text:
            try:
                await bot.send_message(user_id, text)
            except Exception:
                pass


# ─── /start ───────────────────────────────────────────────────────────────────
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user = message.from_user
    db.register_user(user.id, user.username or "", user.full_name or "")
    if db.is_banned(user.id):
        await message.answer("⛔ Нет доступа")
        return
    await state.clear()
    await message.answer(START_TEXT, reply_markup=main_kb())
    await maybe_send_ad(user.id, "start")


@router.message(Command("help"))
async def cmd_help(message: Message):
    if db.is_banned(message.from_user.id):
        return
    await message.answer(HELP_TEXT, reply_markup=back_kb("start"))


# ─── Main menu callbacks ───────────────────────────────────────────────────────
@router.callback_query(F.data == "back_start")
async def cb_back_start(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(call, START_TEXT, reply_markup=main_kb())


@router.callback_query(F.data == "support")
async def cb_support(call: CallbackQuery):
    uid = call.from_user.id
    sub = db.get_subscription(uid)
    if sub:
        expires = datetime.fromisoformat(sub["expires_at"])
        until = expires.strftime("%d.%m.%Y")
        sub_type = format_subscription_type(sub["sub_type"])
        await safe_edit(call, active_sub_text(until, sub_type), reply_markup=back_kb("start"))
        return
    await safe_edit(call, SUPPORT_TEXT, reply_markup=support_kb())


@router.callback_query(F.data == "pay_stars")
async def cb_pay_stars(call: CallbackQuery):
    await safe_edit(call, STARS_TEXT, reply_markup=stars_kb())


@router.callback_query(F.data == "back_support")
async def cb_back_support(call: CallbackQuery):
    await safe_edit(call, SUPPORT_TEXT, reply_markup=support_kb())


@router.callback_query(F.data == "pay_manual")
async def cb_pay_manual(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="👨‍💻 Связаться с разработчиком",
            url=f"https://t.me/{DEVELOPER_USERNAME.lstrip('@')}"
        )],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_support")],
    ])
    await safe_edit(call, MANUAL_PAY_TEXT, reply_markup=kb)


@router.callback_query(F.data.startswith("stars_"))
async def cb_stars_plan(call: CallbackQuery):
    plan_key = call.data.replace("stars_", "")
    if plan_key not in pay.PLANS:
        await call.answer("Неверный план")
        return
    await call.answer()
    await pay.send_stars_invoice(bot, call.from_user.id, plan_key)


@router.callback_query(F.data == "dev")
async def cb_dev(call: CallbackQuery):
    await safe_edit(call, DEV_TEXT, reply_markup=back_kb("start"))


@router.callback_query(F.data == "settings")
async def cb_settings(call: CallbackQuery):
    downloads = db.get_user_downloads_count(call.from_user.id)
    await safe_edit(call, settings_text(downloads), reply_markup=back_kb("start"))


@router.callback_query(F.data == "help")
async def cb_help(call: CallbackQuery):
    await safe_edit(call, HELP_TEXT, reply_markup=back_kb("start"))


# ─── Payment handlers ─────────────────────────────────────────────────────────
@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    uid = message.from_user.id
    stars_amount = message.successful_payment.total_amount
    success = await pay.process_successful_payment(uid, payload)
    if success:
        plan_key = payload[4:]
        db.log_payment(
            user_id=uid,
            amount=stars_amount,
            payment_type="stars",
            subscription_type=plan_key,
        )
        sub = db.get_subscription(uid)
        expires = datetime.fromisoformat(sub["expires_at"])
        until = expires.strftime("%d.%m.%Y")
        sub_type = format_subscription_type(sub["sub_type"])
        await message.answer(
            f"🎉 Оплата прошла успешно!\n\n"
            f"✅ Подписка активирована\n"
            f"Тип: {sub_type}\n"
            f"Действует до: {until}"
        )
    else:
        await message.answer("❌ Ошибка активации подписки. Обратитесь к разработчику.")


# ─── URL detection & video flow ───────────────────────────────────────────────
@router.message(F.text)
async def handle_message(message: Message, state: FSMContext):
    uid = message.from_user.id

    if db.is_banned(uid):
        await message.answer("⛔ Нет доступа")
        return

    db.register_user(uid, message.from_user.username or "", message.from_user.full_name or "")

    text = message.text or ""
    platform, url = detect_platform(text)

    if not platform:
        return

    if is_flooded(uid):
        import time
        remaining = int(FLOOD_SECONDS - (time.time() - flood_map.get(uid, 0))) + 1
        await message.answer(f"⏳ Подождите {remaining} секунд")
        return

    processing_msg = await message.answer("⏳ Обрабатываю ссылку...")

    try:
        if platform == "youtube":
            info = yt.get_video_info(url)
        else:
            info = tt.get_video_info(url)

        if not info:
            await processing_msg.edit_text("❌ Ошибка получения информации")
            return

        url_hash = make_url_hash(url)
        video_cache[url_hash] = {
            "url": url,
            "platform": platform,
            "info": info,
        }

        await processing_msg.edit_text(
            video_info_short(info),
            reply_markup=video_actions_kb(url_hash)
        )

    except Exception as e:
        logger.error(f"handle_message error: {e}")
        await processing_msg.edit_text("❌ Ошибка получения информации")


# ─── Video action callbacks ───────────────────────────────────────────────────
@router.callback_query(F.data.startswith("back_video_"))
async def cb_back_video(call: CallbackQuery):
    url_hash = call.data.replace("back_video_", "")
    cached = video_cache.get(url_hash)
    if not cached:
        await safe_edit(call, "❌ Данные устарели. Отправьте ссылку снова.", reply_markup=back_kb("start"))
        return
    await safe_edit(call, video_info_short(cached["info"]), reply_markup=video_actions_kb(url_hash))


@router.callback_query(F.data.startswith("qualities_"))
async def cb_qualities(call: CallbackQuery):
    url_hash = call.data.replace("qualities_", "")
    cached = video_cache.get(url_hash)
    if not cached:
        await safe_edit(call, "❌ Данные устарели. Отправьте ссылку снова.", reply_markup=back_kb("start"))
        return

    info = cached["info"]
    platform = cached["platform"]

    if platform == "youtube":
        qualities = yt.get_available_qualities(info)
    else:
        qualities = tt.get_available_qualities(info)

    if not qualities:
        await call.answer("❌ Нет доступных качеств", show_alert=True)
        return

    cached["qualities"] = qualities
    await safe_edit(
        call,
        "🎬 Доступные качества:\n\nВыберите качество:",
        reply_markup=qualities_kb(url_hash, qualities)
    )


@router.callback_query(F.data.startswith("dl_"))
async def cb_download(call: CallbackQuery):
    # callback_data: dl_{url_hash}_{format_id}
    # format_id может содержать символы, поэтому split только на 2 части после префикса
    raw = call.data[3:]  # убираем "dl_"
    sep = raw.index("_")
    url_hash = raw[:sep]
    format_id = raw[sep + 1:]

    cached = video_cache.get(url_hash)
    if not cached:
        await safe_edit(call, "❌ Данные устарели. Отправьте ссылку снова.", reply_markup=back_kb("start"))
        return

    uid = call.from_user.id
    url = cached["url"]
    platform = cached["platform"]
    info = cached["info"]
    title = info.get("title", "Видео")

    qualities = cached.get("qualities", [])
    quality_info = next((q for q in qualities if q["format_id"] == format_id), None)
    quality_label = quality_info["label"] if quality_info else format_id
    size_str = (
        format_size(quality_info["filesize"])
        if quality_info and quality_info["filesize"]
        else "Неизвестно"
    )

    status_msg = await call.message.edit_text(
        f"⬇️ Скачиваю...\n\nКачество: {quality_label}\nРазмер: {size_str}"
    )

    # ── Очередь ───────────────────────────────────────────────────────────────
    await acquire_download_slot(uid, status_msg)
    try:
        await status_msg.edit_text(
            f"⬇️ Скачиваю...\n\nКачество: {quality_label}\nРазмер: {size_str}"
        )
    except Exception:
        pass
    # ─────────────────────────────────────────────────────────────────────────

    try:
        video_id = info.get("id", url_hash)

        if platform == "youtube":
            filepath = yt.download_video(url, format_id, video_id)
        else:
            filepath = tt.download_video(url, format_id, video_id)

        if not filepath or not os.path.exists(filepath):
            await status_msg.edit_text("❌ Ошибка скачивания")
            return

        actual_size = format_size(os.path.getsize(filepath))
        caption = caption_video(title, quality_label, actual_size)

        await bot.send_video(
            uid,
            video=open(filepath, "rb"),
            caption=caption,
            supports_streaming=True,
        )

        db.increment_downloads(uid, url, platform, quality_label)

        try:
            await status_msg.delete()
        except Exception:
            pass

        if DELETE_AFTER_SEND:
            clean_temp_file(filepath)

        await maybe_send_ad(uid, "after_download")

    except Exception as e:
        logger.error(f"cb_download error: {e}")
        try:
            await status_msg.edit_text("❌ Ошибка скачивания")
        except Exception:
            pass
    finally:
        if not db.is_premium(uid):
            await _release_slot(uid)


@router.callback_query(F.data.startswith("mp3_"))
async def cb_mp3(call: CallbackQuery):
    url_hash = call.data.replace("mp3_", "")
    cached = video_cache.get(url_hash)
    if not cached:
        await safe_edit(call, "❌ Данные устарели. Отправьте ссылку снова.", reply_markup=back_kb("start"))
        return

    uid = call.from_user.id
    url = cached["url"]
    platform = cached["platform"]
    info = cached["info"]
    title = info.get("title", "Аудио")
    video_id = info.get("id", url_hash)

    status_msg = await call.message.edit_text("⬇️ Скачиваю MP3...")

    # ── Очередь ───────────────────────────────────────────────────────────────
    await acquire_download_slot(uid, status_msg)
    try:
        await status_msg.edit_text("⬇️ Скачиваю MP3...")
    except Exception:
        pass
    # ─────────────────────────────────────────────────────────────────────────

    try:
        if platform == "youtube":
            filepath = yt.download_audio(url, video_id)
        else:
            filepath = tt.download_audio(url, video_id)

        if not filepath or not os.path.exists(filepath):
            await status_msg.edit_text("❌ Ошибка скачивания")
            return

        actual_size = format_size(os.path.getsize(filepath))
        caption = caption_audio(title, actual_size)

        await bot.send_audio(
            uid,
            audio=open(filepath, "rb"),
            caption=caption,
            title=title,
        )

        db.increment_downloads(uid, url, platform, "mp3")

        try:
            await status_msg.delete()
        except Exception:
            pass

        if DELETE_AFTER_SEND:
            clean_temp_file(filepath)

        await maybe_send_ad(uid, "after_download")

    except Exception as e:
        logger.error(f"cb_mp3 error: {e}")
        try:
            await status_msg.edit_text("❌ Ошибка скачивания")
        except Exception:
            pass
    finally:
        if not db.is_premium(uid):
            await _release_slot(uid)


@router.callback_query(F.data.startswith("thumb_"))
async def cb_thumb(call: CallbackQuery):
    url_hash = call.data.replace("thumb_", "")
    cached = video_cache.get(url_hash)
    if not cached:
        await safe_edit(call, "❌ Данные устарели. Отправьте ссылку снова.", reply_markup=back_kb("start"))
        return

    info = cached["info"]
    platform = cached["platform"]
    title = info.get("title", "Видео")

    thumb_url = yt.get_thumbnail_url(info) if platform == "youtube" else tt.get_thumbnail_url(info)

    if not thumb_url:
        await call.answer("❌ Превью недоступно", show_alert=True)
        return

    try:
        await bot.send_photo(
            call.from_user.id,
            photo=URLInputFile(thumb_url),
            caption=caption_thumb(title),
        )
        await call.answer()
    except Exception as e:
        logger.error(f"cb_thumb error: {e}")
        await call.answer("❌ Ошибка загрузки превью", show_alert=True)


@router.callback_query(F.data.startswith("info_"))
async def cb_info(call: CallbackQuery):
    url_hash = call.data.replace("info_", "")
    cached = video_cache.get(url_hash)
    if not cached:
        await safe_edit(call, "❌ Данные устарели. Отправьте ссылку снова.", reply_markup=back_kb("start"))
        return

    info = cached["info"]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_video_{url_hash}")]
    ])
    await safe_edit(call, video_info_full(info), reply_markup=kb)


# ─── Background tasks ─────────────────────────────────────────────────────────
async def _cleanup_task():
    """Каждый час удаляет истекшие подписки из БД."""
    while True:
        await asyncio.sleep(3600)
        db.check_premium_expired()


# ─── Entry point ──────────────────────────────────────────────────────────────
async def main():
    db.init_db()
    dp.include_router(admin_module.router)
    dp.include_router(router)
    logger.info("Bot starting...")
    asyncio.create_task(_cleanup_task())
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
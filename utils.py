import re
import os
import json
import time
import logging
from datetime import datetime
from config import TEMP_FOLDER, FLOOD_SECONDS, ADMIN_ID

logger = logging.getLogger(__name__)

YOUTUBE_PATTERN = re.compile(
    r"(https?://)?(www\.)?"
    r"(youtube\.com/(watch\?v=|shorts/|embed/)|youtu\.be/)"
    r"[\w\-]+"
)
TIKTOK_PATTERN = re.compile(
    r"(https?://)?(www\.|vm\.|vt\.)?"
    r"tiktok\.com/[\S]+"
)

# ─── Flood control ────────────────────────────────────────────────────────────
_flood_map: dict[int, float] = {}


def check_flood(user_id: int) -> bool:
    """
    Возвращает True если пользователь флудит (запрос раньше FLOOD_SECONDS),
    False если всё ок (и обновляет время последнего запроса).
    """
    now = time.time()
    last = _flood_map.get(user_id, 0)
    if now - last < FLOOD_SECONDS:
        return True
    _flood_map[user_id] = now
    return False


def flood_remaining(user_id: int) -> int:
    """Возвращает оставшиеся секунды ожидания для пользователя."""
    now = time.time()
    last = _flood_map.get(user_id, 0)
    remaining = FLOOD_SECONDS - (now - last)
    return max(1, int(remaining) + 1)


# ─── Admin check ──────────────────────────────────────────────────────────────
def is_admin(user_id: int) -> bool:
    """Возвращает True если user_id совпадает с ADMIN_ID из config.py."""
    return user_id == ADMIN_ID


# ─── Safe filename ────────────────────────────────────────────────────────────
def safe_filename(filename: str) -> str:
    """
    Очищает имя файла от недопустимых символов.
    Оставляет только буквы, цифры, пробелы, дефисы, подчёркивания и точки.
    Обрезает до 100 символов.
    """
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    filename = re.sub(r"[^\w\s\-.]", "", filename, flags=re.UNICODE)
    filename = filename.strip(". ")
    filename = re.sub(r"\s+", "_", filename)
    return filename[:100] if filename else "file"


# ─── Platform detection ───────────────────────────────────────────────────────
def detect_platform(text: str):
    """Returns ('youtube', url) | ('tiktok', url) | (None, None)"""
    urls = re.findall(r"https?://\S+", text)
    if not urls:
        urls = re.findall(r"(?:www\.|vm\.|vt\.)?(?:youtube|youtu|tiktok)\S+", text)
        if urls:
            urls = ["https://" + u for u in urls]

    for url in urls:
        if YOUTUBE_PATTERN.search(url):
            return "youtube", url
        if TIKTOK_PATTERN.search(url):
            return "tiktok", url
    return None, None


# ─── Formatters ───────────────────────────────────────────────────────────────
def format_duration(seconds) -> str:
    if not seconds:
        return "Неизвестно"
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_views(views) -> str:
    if not views:
        return "Неизвестно"
    views = int(views)
    if views >= 1_000_000:
        return f"{views / 1_000_000:.1f}M"
    if views >= 1_000:
        return f"{views / 1_000:.1f}K"
    return str(views)


def format_size(bytes_size) -> str:
    if not bytes_size:
        return "Неизвестно"
    bytes_size = int(bytes_size)
    if bytes_size >= 1024 ** 3:
        return f"{bytes_size / 1024 ** 3:.1f} GB"
    if bytes_size >= 1024 ** 2:
        return f"{bytes_size / 1024 ** 2:.1f} MB"
    if bytes_size >= 1024:
        return f"{bytes_size / 1024:.1f} KB"
    return f"{bytes_size} B"


def format_date(date_str) -> str:
    if not date_str:
        return "Неизвестно"
    try:
        dt = datetime.strptime(str(date_str), "%Y%m%d")
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return str(date_str)


def format_subscription_type(sub_type: str) -> str:
    mapping = {
        "1_month":   "1 месяц",
        "3_months":  "3 месяца",
        "6_months":  "6 месяцев",
        "12_months": "12 месяцев",
        "lifetime":  "Навсегда",
    }
    return mapping.get(sub_type, sub_type)


# ─── Ads ──────────────────────────────────────────────────────────────────────
def load_ads() -> dict:
    try:
        with open("ads.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "enabled": False,
            "start": {"text": "", "enabled": False},
            "after_download": {"text": "", "enabled": False},
        }


def should_show_ad(ads: dict, placement: str) -> bool:
    if not ads.get("enabled", False):
        return False
    return ads.get(placement, {}).get("enabled", False)


def get_ad_text(ads: dict, placement: str) -> str:
    return ads.get(placement, {}).get("text", "")


# ─── Temp files ───────────────────────────────────────────────────────────────
def ensure_temp_folder():
    os.makedirs(TEMP_FOLDER, exist_ok=True)


def clean_temp_file(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
            logger.debug(f"Deleted temp file: {path}")
    except Exception as e:
        logger.warning(f"Failed to delete {path}: {e}")
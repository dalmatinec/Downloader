# utils.py
import os
import re
import json
import time
import shutil
import logging
import uuid
from datetime import datetime
from typing import Optional, Tuple, Dict

from config import (
    TEMP_FOLDER,
    FLOOD_SECONDS,
    MONTH_DAYS,
    THREE_MONTHS_DAYS,
    SIX_MONTHS_DAYS,
    YEAR_DAYS,
    LIFETIME,
    PRICE_1_MONTH,
    PRICE_3_MONTH,
    PRICE_6_MONTH,
    PRICE_12_MONTH,
    PRICE_LIFETIME,
    STARS_1_MONTH,
    STARS_3_MONTH,
    STARS_6_MONTH,
    STARS_12_MONTH,
    STARS_LIFETIME,
    ADMIN_ID
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Хранилище для антифлуда
user_last_request = {}


def load_texts() -> Dict:
    """Загрузка текстов из JSON"""
    try:
        with open('texts.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def load_ads() -> Dict:
    """Загрузка рекламных текстов"""
    try:
        with open('ads.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Создаем файл с настройками по умолчанию
        default_ads = {
            "enabled": False,
            "start": {
                "text": "📢 Поддержи проект - отключи рекламу!",
                "enabled": False
            },
            "menu": {
                "text": "📢 Рекламный баннер в меню",
                "enabled": False
            },
            "after_download": {
                "text": "📢 Спасибо за скачивание! Поддержи проект ❤️",
                "enabled": False
            }
        }
        with open('ads.json', 'w', encoding='utf-8') as f:
            json.dump(default_ads, f, indent=4, ensure_ascii=False)
        return default_ads
    except:
        return {"enabled": False}


def should_show_ad(user_id: int, ad_type: str, db) -> Tuple[bool, str]:
    """Проверка нужно ли показывать рекламу"""
    # Проверяем премиум
    user = db.get_user(user_id)
    if user and user[4]:  # is_premium
        return False, ""
    
    # Загружаем настройки рекламы
    ads = load_ads()
    
    # Проверяем включена ли реклама вообще
    if not ads.get('enabled', False):
        return False, ""
    
    # Проверяем конкретный тип
    ad_data = ads.get(ad_type, {})
    if not ad_data.get('enabled', False):
        return False, ""
    
    return True, ad_data.get('text', "")


def ensure_temp_folder():
    """Создание папки temp"""
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)


def clean_temp_folder():
    """Очистка папки temp"""
    if os.path.exists(TEMP_FOLDER):
        for filename in os.listdir(TEMP_FOLDER):
            file_path = os.path.join(TEMP_FOLDER, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except:
                pass
    ensure_temp_folder()
    logger.info("Temp очищен")


def delete_file(file_path: str) -> bool:
    """Удаление файла"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
    except:
        pass
    return False


def is_admin(user_id: int) -> bool:
    """Проверка админа"""
    return user_id == ADMIN_ID


def format_size(size_bytes: int) -> str:
    """Форматирование размера"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_duration(seconds: int) -> str:
    """Форматирование времени"""
    if not seconds:
        return "00:00"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def detect_platform(url: str) -> str:
    """Определение платформы"""
    url = url.lower()
    if 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    elif 'tiktok.com' in url or 'vm.tiktok.com' in url:
        return 'tiktok'
    elif 'instagram.com' in url:
        return 'instagram'
    elif 'vk.com' in url:
        return 'vk'
    elif 'pinterest.com' in url:
        return 'pinterest'
    elif 'facebook.com' in url:
        return 'facebook'
    elif 'twitter.com' in url or 'x.com' in url:
        return 'twitter'
    elif 'vimeo.com' in url:
        return 'vimeo'
    elif 'rutube.ru' in url:
        return 'rutube'
    return 'unknown'


def get_unique_filename(extension: str) -> str:
    """Уникальное имя файла"""
    return f"{uuid.uuid4()}.{extension}"


def safe_filename(filename: str) -> str:
    """Безопасное имя файла"""
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    return filename[:255]


def check_flood(user_id: int) -> Tuple[bool, str]:
    """Проверка антифлуда"""
    current_time = time.time()
    if user_id in user_last_request:
        time_diff = current_time - user_last_request[user_id]
        if time_diff < FLOOD_SECONDS:
            wait_time = int(FLOOD_SECONDS - time_diff) + 1
            return False, f"⏳ Подождите {wait_time} секунд"
    user_last_request[user_id] = current_time
    return True, ""


def get_subscription_type_text(days: int) -> str:
    """Текст типа подписки"""
    if days == LIFETIME:
        return "Навсегда"
    elif days == MONTH_DAYS:
        return "1 месяц"
    elif days == THREE_MONTHS_DAYS:
        return "3 месяца"
    elif days == SIX_MONTHS_DAYS:
        return "6 месяцев"
    elif days == YEAR_DAYS:
        return "12 месяцев"
    return f"{days} дней"


def get_subscription_price(days: int) -> int:
    """Цена в тенге"""
    if days == LIFETIME:
        return PRICE_LIFETIME
    elif days == MONTH_DAYS:
        return PRICE_1_MONTH
    elif days == THREE_MONTHS_DAYS:
        return PRICE_3_MONTH
    elif days == SIX_MONTHS_DAYS:
        return PRICE_6_MONTH
    elif days == YEAR_DAYS:
        return PRICE_12_MONTH
    return 0


def get_subscription_stars(days: int) -> int:
    """Цена в звездах"""
    if days == LIFETIME:
        return STARS_LIFETIME
    elif days == MONTH_DAYS:
        return STARS_1_MONTH
    elif days == THREE_MONTHS_DAYS:
        return STARS_3_MONTH
    elif days == SIX_MONTHS_DAYS:
        return STARS_6_MONTH
    elif days == YEAR_DAYS:
        return STARS_12_MONTH
    return 0
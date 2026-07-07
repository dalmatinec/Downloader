import asyncio
import aiohttp
import random
import logging
import time
from collections import deque
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo
from typing import Optional

from aiogram.types import Message

import config
from database import Database
from utils import safe_send_message


logger = logging.getLogger(__name__)
db = Database()

# ============================================================
# ЧАСОВОЙ ПОЯС АЛМАТЫ
# ============================================================

ALMATY_TZ = ZoneInfo("Asia/Almaty")


# ============================================================
# API КЛЮЧИ
# ============================================================

CLOUDFLARE_ACCOUNT_ID = "2f2346065a56065e768d5c6c9c7d71eb"
CLOUDFLARE_API_TOKEN = ""
CLOUDFLARE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/meta/llama-3.2-3b-instruct"


# ============================================================
# ПОГОДА
# ============================================================

WEATHER_API_KEY = "285bb0213af2bacf33ed8c43761543e0"
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


# ============================================================
# КОНТЕКСТ СООБЩЕНИЙ (В ПАМЯТИ)
# ============================================================

chat_history = deque(maxlen=20)


def add_message_to_history(username: str, text: str) -> None:
    if not text:
        return
    chat_history.append(f"{username}: {text}")


def add_ai_message_to_history(text: str) -> None:
    if not text:
        return
    chat_history.append(f"Кеша: {text}")


async def get_recent_messages(limit: int = 20) -> str:
    if not chat_history:
        return ""
    recent = list(chat_history)[-limit:]
    return "\n".join(recent)


# ============================================================
# СИСТЕМНЫЙ ПРОМПТ
# ============================================================

SYSTEM_PROMPT = """
Ты Кеша — домашний рыжий кот и постоянный участник Telegram-чата.

Никогда не говори, что ты ИИ, языковая модель или бот.

Всегда отвечай только на русском языке.
Никогда не используй английские слова, латиницу или другие языки, даже если пользователь написал не на русском.

Пиши естественно, как обычный человек.
Максимум 1–2 коротких предложения.
Не используй шаблонные фразы и не повторяйся.

Не навязывай темы.
Если пользователь говорит о погоде — говори о погоде.
Если о фильмах — о фильмах.
Если просто общается — просто поддерживай разговор.

Не придумывай факты.
Если чего-то не знаешь — честно скажи об этом.

Учитывай предыдущие сообщения чата, если они есть в переданном контексте.
"""


# ============================================================
# ОГРАНИЧИТЕЛЬ ЗАПРОСОВ
# ============================================================

_rate_limit = {
    "last_request_time": 0,
    "request_count": 0
}


async def check_rate_limit(user_id: int) -> bool:
    now = time.time()
    if now - _rate_limit["last_request_time"] > 60:
        _rate_limit["request_count"] = 0
        _rate_limit["last_request_time"] = now
    if _rate_limit["request_count"] >= 5:
        logger.warning(f"Rate limit exceeded. User: {user_id}")
        return False
    _rate_limit["request_count"] += 1
    _rate_limit["last_request_time"] = now
    return True


# ============================================================
# ОСНОВНЫЕ ФУНКЦИИ
# ============================================================

async def ask_ai(prompt: str, context: str = "") -> Optional[str]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    if context:
        messages.append({"role": "user", "content": f"Контекст предыдущих сообщений:\n{context}"})
    messages.append({
        "role": "user",
        "content": (
            "Отвечай только на русском языке.\n"
            "Запрещено использовать иностранные слова, латиницу и смешение языков.\n\n"
            f"{prompt}"
        )
    })
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {"messages": messages}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(CLOUDFLARE_URL, headers=headers, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if "result" in result and "response" in result["result"]:
                        response = result["result"]["response"].strip()
                        if response:
                            logger.info("AI response generated")
                            return response
                    elif "result" in result and "choices" in result["result"]:
                        response = result["result"]["choices"][0]["message"]["content"].strip()
                        if response:
                            logger.info("AI response generated")
                            return response
                    else:
                        logger.error(f"Неожиданный ответ: {result}")
                        return None
                else:
                    error_text = await resp.text()
                    logger.error(f"Cloudflare AI error: {resp.status} - {error_text}")
                    return None
    except Exception as e:
        logger.exception(f"Cloudflare AI request failed: {e}")
        return None


async def get_weather() -> Optional[dict]:
    params = {
        "q": "Almaty",
        "appid": WEATHER_API_KEY,
        "units": "metric",
        "lang": "ru"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(WEATHER_URL, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "temp": data["main"]["temp"],
                        "feels_like": data["main"]["feels_like"],
                        "condition": data["weather"][0]["description"],
                        "wind": data["wind"]["speed"],
                        "humidity": data["main"]["humidity"]
                    }
                else:
                    return None
    except Exception as e:
        logger.exception(f"Weather error: {e}")
        return None


def get_weather_emoji(condition: str) -> str:
    condition_lower = condition.lower()
    if "ясно" in condition_lower or "солнечно" in condition_lower:
        return "☀️"
    elif "облачно" in condition_lower or "переменная облачность" in condition_lower:
        return "🌤"
    elif "пасмурно" in condition_lower:
        return "☁️"
    elif "дождь" in condition_lower or "ливень" in condition_lower:
        return "🌧"
    elif "гроза" in condition_lower:
        return "⛈"
    elif "снег" in condition_lower:
        return "❄️"
    elif "туман" in condition_lower:
        return "🌫"
    else:
        return "🌤"


def is_silent_hour() -> bool:
    now = datetime.now(ALMATY_TZ).time()
    return dt_time(1, 0) <= now <= dt_time(7, 0)


def is_kesha_mentioned(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    names = ["кеша", "кешенька", "кешу", "кеше", "кеш", "kesha", "kescha"]
    return any(name in text_lower for name in names)


def is_weather_question(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    keywords = ["погода", "температура", "дождь", "жарко", "холодно", "ветер"]
    return any(keyword in text_lower for keyword in keywords)


def format_weather_message(weather: dict) -> str:
    now = datetime.now(ALMATY_TZ)
    date_str = now.strftime("%d.%m.%Y")
    time_str = now.strftime("%H:%M")
    emoji = get_weather_emoji(weather['condition'])
    return (
        f"🌤 Погода в Алматы\n\n"
        f"📅 {date_str}\n"
        f"🕘 {time_str}\n\n"
        f"🌡 Температура: {weather['temp']:.0f}°\n"
        f"🤗 Ощущается как: {weather['feels_like']:.0f}°\n"
        f"{emoji} {weather['condition'].capitalize()}\n"
        f"💨 Ветер: {weather['wind']:.1f} м/с\n"
        f"💧 Влажность: {weather['humidity']}%"
    )


async def get_weather_advice(weather: dict, context: str = "") -> Optional[str]:
    prompt = f"""Погода в Алматы: {weather['temp']:.0f}°C, {weather['condition']}

Напиши короткий совет от имени Кеши. Естественно, без повторов."""
    return await ask_ai(prompt, context)


async def send_weather(bot) -> None:
    weather = await get_weather()
    if not weather:
        return
    context = await get_recent_messages()
    weather_message = format_weather_message(weather)
    advice = await get_weather_advice(weather, context)
    full_message = f"{weather_message}\n\n🐱 {advice}" if advice else weather_message
    await safe_send_message(bot=bot, chat_id=config.CHAT_ID, text=full_message)
    if advice:
        add_ai_message_to_history(advice)
    logger.info("Weather sent to chat")


async def ai_auto_message(bot) -> None:
    if is_silent_hour():
        return
    now = datetime.now(ALMATY_TZ)
    if now.hour == 9 and now.minute < 5:
        await send_weather(bot)
        return
    prompt = """
Напиши одно короткое сообщение от имени Кеши — обычного участника чата.

Выбери одну тему:
- спросить как проходит день
- спросить кто что читает (если хочешь, но не навязывай)
- сказать что хочется чая
- пошутить
- вспомнить книгу
- поговорить про котов
- поговорить про уют

Только одна тема. Не смешивай. Максимум два коротких предложения.
"""
    response = await ask_ai(prompt)
    if response:
        await safe_send_message(bot=bot, chat_id=config.CHAT_ID, text=response)
        add_ai_message_to_history(response)
        logger.info("AI auto message sent")


async def handle_kesha_mention(message) -> bool:
    logger.info("handle_kesha_mention")
    bot = message.bot
    if not message.text or not is_kesha_mentioned(message.text):
        return False
    if not await check_rate_limit(message.from_user.id):
        return False
    context = await get_recent_messages()

    if is_weather_question(message.text):
        weather = await get_weather()
        if weather:
            weather_message = format_weather_message(weather)
            advice = await get_weather_advice(weather, context)
            full_message = f"{weather_message}\n\n🐱 {advice}" if advice else weather_message
            await safe_send_message(
                bot=bot,
                chat_id=message.chat.id,
                text=full_message,
                reply_to_message_id=message.message_id
            )
            if advice:
                add_ai_message_to_history(advice)
            return True

    prompt = f"""Тебя позвали по имени. Сообщение пользователя: {message.text}

Ответь как Кеша — обычный участник чата. Будь дружелюбным, коротким, по делу."""
    response = await ask_ai(prompt, context)
    if response:
        await safe_send_message(
            bot=bot,
            chat_id=message.chat.id,
            text=response,
            reply_to_message_id=message.message_id
        )
        add_ai_message_to_history(response)
        return True
    return False


async def handle_book_keywords(message) -> bool:
    logger.info("handle_book_keywords")
    bot = message.bot
    if not message.text:
        return False
    if is_kesha_mentioned(message.text):
        return False

    text_lower = message.text.lower()
    keywords = ["книга", "книги", "книгу", "посоветуй", "что почитать", "почитать", "совет"]
    if any(keyword in text_lower for keyword in keywords):
        if not await check_rate_limit(message.from_user.id):
            return False
        context = await get_recent_messages()
        books = await db.get_all_books()
        if books:
            book_list = ", ".join(f'{book["title"]} — {book["author"]}' for book in books)
            book_prompt = f"Список книг: {book_list}. Выбери одну книгу из списка и порекомендуй её. Если пользователь уже читал её — выбери другую. Не придумывай книги, которых нет в списке."
        else:
            book_prompt = "Список книг пуст. Можешь советовать любые книги, обязательно указывая автора и жанр."

        prompt = f"Пользователь спросил про книги: {message.text}\n{book_prompt}\n\nОтветь коротко, тепло, по делу."
        response = await ask_ai(prompt, context)
        if response:
            await safe_send_message(
                bot=bot,
                chat_id=message.chat.id,
                text=response,
                reply_to_message_id=message.message_id
            )
            add_ai_message_to_history(response)
            return True
    return False


async def handle_all_messages(message: Message) -> bool:
    if not message.text:
        return False
    if message.from_user.is_bot:
        return False
    username = message.from_user.first_name or "Пользователь"
    add_message_to_history(username, message.text)
    return False


async def handle_reply_to_kesha(message: Message) -> bool:
    if not message.reply_to_message:
        return False
    if message.reply_to_message.from_user.id != message.bot.id:
        return False
    logger.info("handle_reply_to_kesha")
    bot = message.bot
    if not await check_rate_limit(message.from_user.id):
        return False
    context = await get_recent_messages()
    
    prompt = f"""Ты Кеша. Пользователь ответил на твоё сообщение: {message.text}

Ответь естественно, как обычный участник чата. Будь коротким, дружелюбным.
Не используй шаблоны. Не повторяй одну мысль.
Если вопрос не по теме — просто поддержи разговор.
"""
    
    response = await ask_ai(prompt, context)
    if response:
        await safe_send_message(
            bot=bot,
            chat_id=message.chat.id,
            text=response,
            reply_to_message_id=message.message_id
        )
        add_ai_message_to_history(response)
        return True
    return False


async def ai_loop(bot):
    while True:
        await asyncio.sleep(7200)
        await ai_auto_message(bot)
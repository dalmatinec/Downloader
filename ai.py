import asyncio
import aiohttp
import random
import logging
from collections import deque
from datetime import datetime, time
from zoneinfo import ZoneInfo
from typing import Optional

from aiogram.types import Message

import config
from utils import safe_send_message


logger = logging.getLogger(__name__)

# ============================================================
# ЧАСОВОЙ ПОЯС АЛМАТЫ
# ============================================================

ALMATY_TZ = ZoneInfo("Asia/Almaty")

# ============================================================
# КАНАЛ
# ============================================================

CHANNEL_USERNAME = "vashemurlichestvo"


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
# КНИГИ (ПУСТОЙ СПИСОК)
# ============================================================

BOOKS = [
    # позже сюда будут добавлены книги
]


# ============================================================
# КОНТЕКСТ СООБЩЕНИЙ (В ПАМЯТИ)
# ============================================================

chat_history = deque(maxlen=20)


def add_message_to_history(username: str, text: str) -> None:
    if not text:
        return
    chat_history.append(f"{username}: {text}")


async def get_recent_messages(limit: int = 15) -> str:
    if not chat_history:
        return ""
    recent = list(chat_history)[-limit:]
    return "\n".join(recent)


# ============================================================
# СИСТЕМНЫЙ ПРОМПТ
# ============================================================

SYSTEM_PROMPT = """
Ты Кеша — домашний кот и постоянный участник этого Telegram-чата.

Ты живёшь здесь постоянно и общаешься как обычный человек, только кот.

Ты никогда не говоришь, что ты ИИ, языковая модель или бот.

Твой характер:
- спокойный;
- дружелюбный;
- уютный;
- немного саркастичный;
- любишь книги, чай, котов и YouTube.

Главные правила:

• Одно сообщение = одна мысль.
• Не смешивай несколько тем.
• Не придумывай случайные истории.
• Не выдумывай исторические факты.
• Не придумывай новости.
• Не сочиняй абсурдные ситуации.
• Если нечего сказать — лучше ответить коротко.
• Не философствуй без причины.
• Не пытайся быть смешным любой ценой.
• Не используй одинаковые начала сообщений.
• Не используй шаблоны.
• Отвечай максимально естественно.
• Обычно 1–3 предложения.
• Никогда не пиши поток сознания.

Перед отправкой ответа всегда мысленно проверяй:

"Все ли предложения относятся к одной теме?"

Если нет — перепиши ответ.
"""


# ============================================================
# ОСНОВНЫЕ ФУНКЦИИ
# ============================================================

async def ask_ai(prompt: str, context: str = "") -> Optional[str]:
    """Запрос к Cloudflare Workers AI (Llama 3.2 3B) с контекстом"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    if context:
        messages.append({"role": "user", "content": f"Контекст предыдущих сообщений чата:\n{context}"})

    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messages": messages
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(CLOUDFLARE_URL, headers=headers, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if "result" in result and "response" in result["result"]:
                        return result["result"]["response"].strip()
                    elif "result" in result and "choices" in result["result"]:
                        return result["result"]["choices"][0]["message"]["content"].strip()
                    else:
                        logger.error(f"Неожиданный ответ Cloudflare: {result}")
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
    return time(1, 0) <= now <= time(7, 0)


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


# ============================================================
# ОСНОВНЫЕ ФУНКЦИИ AI
# ============================================================

async def get_weather_advice(weather: dict, context: str = "") -> Optional[str]:
    prompt = f"""Погода в Алматы сейчас: {weather['temp']:.0f}°C, {weather['condition']}

Напиши короткий совет от имени Кеши.

Важно:
- Никогда не начинай совет одинаково
- Не используй постоянно фразы вроде «я выглянул в окно»
- Каждый раз формулируй мысль по-разному
- Совет должен выглядеть как естественная реплика Кеши
- Не повторяй температуру и описание погоды, они уже показаны выше
- Максимум два коротких предложения"""

    return await ask_ai(prompt, context)


async def send_weather(bot) -> None:
    weather = await get_weather()
    if not weather:
        return

    context = await get_recent_messages()
    weather_message = format_weather_message(weather)
    advice = await get_weather_advice(weather, context)

    if advice:
        full_message = f"{weather_message}\n\n🐱 {advice}"
    else:
        full_message = weather_message

    await safe_send_message(
        bot=bot,
        chat_id=config.CHAT_ID,
        text=full_message
    )
    logger.info("Weather sent to chat")


async def ai_auto_message(bot) -> None:
    if is_silent_hour():
        return

    now = datetime.now(ALMATY_TZ)

    if now.hour == 9 and now.minute < 5:
        await send_weather(bot)
        return

    prompt = """
Напиши одно короткое сообщение от имени Кеши.

Сообщение должно быть таким, будто обычный участник чата решил что-то написать.

Выбери только ОДНУ тему:

- спросить как проходит день;
- спросить кто что читает;
- рассказать короткую мысль;
- сказать что хочется чая;
- пошутить;
- вспомнить книгу;
- поговорить про котов;
- поговорить про уют.

Очень важно:

- только одна тема;
- не смешивать несколько мыслей;
- не придумывать истории;
- не выдумывать факты;
- не писать бессвязный текст;
- не использовать поток сознания;
- не делать сообщение специально странным.

Максимум два коротких предложения.
"""

    response = await ask_ai(prompt)

    if response:
        await safe_send_message(
            bot=bot,
            chat_id=config.CHAT_ID,
            text=response
        )
        logger.info("AI auto message sent")


async def handle_kesha_mention(message) -> bool:
    logger.info("handle_kesha_mention")
    bot = message.bot
    if not message.text or not is_kesha_mentioned(message.text):
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
            return True

    is_book_question = any(kw in message.text.lower() for kw in ["книг", "чита", "посоветуй", "почитать", "совет", "book"])

    book_prompt = ""
    if is_book_question and BOOKS:
        book = random.choice(BOOKS)
        book_prompt = f"У тебя есть список книг: {', '.join(BOOKS)}. Выбери одну книгу из списка и порекомендуй её. Если пользователь уже читал её или пишет об этом, выбери другую."

    prompt = f"""Тебя позвали по имени. Сообщение пользователя: {message.text}
{book_prompt}

Ответь как Кеша. Будь дружелюбным, коротким, живым. Если спрашивают про книги и есть список - используй его. Если список пуст - отвечай свободно."""

    response = await ask_ai(prompt, context)

    if response:
        await safe_send_message(
            bot=bot,
            chat_id=message.chat.id,
            text=response,
            reply_to_message_id=message.message_id
        )
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
        context = await get_recent_messages()

        book_prompt = ""
        if BOOKS:
            book = random.choice(BOOKS)
            book_prompt = f"У тебя есть список книг: {', '.join(BOOKS)}. Выбери одну книгу из списка и порекомендуй её. Если пользователь уже читал её или пишет об этом, выбери другую."

        prompt = f"Пользователь спросил про книги: {message.text}\n{book_prompt}\n\nОтветь коротко, тепло, по делу. Если есть список книг - используй его. Если список пуст - отвечай свободно."

        response = await ask_ai(prompt, context)

        if response:
            await safe_send_message(
                bot=bot,
                chat_id=message.chat.id,
                text=response,
                reply_to_message_id=message.message_id
            )
            return True

    return False


async def handle_video_announcement(message) -> bool:
    logger.info("handle_video_announcement")
    bot = message.bot
    if not message.sender_chat:
        return False

    if message.sender_chat.username != CHANNEL_USERNAME:
        return False

    if not message.reply_markup:
        return False

    has_youtube = False
    for row in message.reply_markup.inline_keyboard:
        for button in row:
            if button.url and ("youtube.com" in button.url or "youtu.be" in button.url):
                has_youtube = True
                break
        if has_youtube:
            break

    if not has_youtube:
        return False

    await asyncio.sleep(random.randint(18, 25))

    prompt = """
В чате появилось новое видео.

Напиши короткую естественную реакцию Кеши.

Выбери один вариант:

- пожелай приятного просмотра;
- скажи что сам сейчас посмотришь;
- попроси потом поделиться впечатлениями;
- легко пошути.

Очень важно:

- только одна мысль;
- максимум два предложения;
- не выдумывать истории;
- не менять тему;
- не использовать шаблоны;
- не упоминать ссылку;
- не упоминать YouTube напрямую;
- сообщение должно выглядеть как сообщение живого участника чата.
"""

    response = await ask_ai(prompt)

    if response:
        await safe_send_message(
            bot=bot,
            chat_id=message.chat.id,
            text=response
        )
        logger.info("Video reaction sent")
        return True

    return False


async def handle_all_messages(message: Message) -> bool:
    """Собирает историю сообщений для контекста ИИ"""
    if not message.text:
        return False

    if message.from_user.is_bot:
        return False

    username = message.from_user.first_name or "Пользователь"
    add_message_to_history(username, message.text)
    
    return False  # ← Это важно, чтобы другие обработчики тоже работали


async def ai_loop(bot):
    """Бесконечный цикл для автоматических сообщений"""
    while True:
        await ai_auto_message(bot)
        await asyncio.sleep(7200)  # 2 часа
import logging
from aiogram import Bot
from aiogram.types import LabeledPrice
from config import (
    STARS_1_MONTH, STARS_3_MONTH, STARS_6_MONTH,
    STARS_12_MONTH, STARS_LIFETIME,
    MONTH_DAYS, THREE_MONTHS_DAYS, SIX_MONTHS_DAYS,
    YEAR_DAYS, LIFETIME,
)
import database as db

logger = logging.getLogger(__name__)

PLANS = {
    "1_month":   {"label": "1 месяц",    "stars": STARS_1_MONTH,   "days": MONTH_DAYS},
    "3_months":  {"label": "3 месяца",   "stars": STARS_3_MONTH,   "days": THREE_MONTHS_DAYS},
    "6_months":  {"label": "6 месяцев",  "stars": STARS_6_MONTH,   "days": SIX_MONTHS_DAYS},
    "12_months": {"label": "12 месяцев", "stars": STARS_12_MONTH,  "days": YEAR_DAYS},
    "lifetime":  {"label": "Навсегда",   "stars": STARS_LIFETIME,  "days": LIFETIME},
}


async def send_stars_invoice(bot: Bot, chat_id: int, plan_key: str):
    plan = PLANS[plan_key]
    await bot.send_invoice(
        chat_id=chat_id,
        title=f"Подписка {plan['label']}",
        description=f"Премиум-подписка на VideoDownloaderBot ({plan['label']})",
        payload=f"sub_{plan_key}",
        currency="XTR",
        prices=[LabeledPrice(label=plan["label"], amount=plan["stars"])],
        provider_token="",
    )


async def process_successful_payment(user_id: int, payload: str) -> bool:
    if not payload.startswith("sub_"):
        return False
    plan_key = payload[4:]
    if plan_key not in PLANS:
        return False
    plan = PLANS[plan_key]
    db.add_subscription(user_id, plan_key, plan["days"])
    logger.info(f"Subscription activated: user={user_id} plan={plan_key} days={plan['days']}")
    return True
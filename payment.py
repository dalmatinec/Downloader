# payment.py
import logging
from aiogram.types import Message, PreCheckoutQuery, LabeledPrice
from aiogram import Bot

from config import (
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
    STARS_LIFETIME
)
from utils import get_subscription_type_text, get_subscription_price, get_subscription_stars

logger = logging.getLogger(__name__)


class PaymentManager:
    def __init__(self, bot: Bot, db):
        self.bot = bot
        self.db = db

    def get_days_by_type(self, sub_type: str) -> int:
        if sub_type == "1_month":
            return MONTH_DAYS
        elif sub_type == "3_months":
            return THREE_MONTHS_DAYS
        elif sub_type == "6_months":
            return SIX_MONTHS_DAYS
        elif sub_type == "12_months":
            return YEAR_DAYS
        elif sub_type == "lifetime":
            return LIFETIME
        return 0

    async def process_stars_payment(self, message: Message, user_id: int, days: int):
        try:
            stars = get_subscription_stars(days)
            sub_text = get_subscription_type_text(days)

            prices = [LabeledPrice(label=sub_text, amount=stars)]

            await self.bot.send_invoice(
                chat_id=user_id,
                title=f"Подписка - {sub_text}",
                description=f"Доступ к премиум функциям на {sub_text}",
                payload=f"sub_{days}_{user_id}",
                provider_token="",
                currency="XTR",
                prices=prices,
                start_parameter="subscription"
            )

            logger.info(f"Запрос оплаты Stars: user={user_id}, days={days}, stars={stars}")

        except Exception as e:
            logger.error(f"Ошибка создания платежа Stars: {e}")
            await message.answer("❌ Ошибка при создании платежа. Попробуйте позже.")

    async def process_pre_checkout(self, pre_checkout_query: PreCheckoutQuery):
        try:
            await self.bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
            logger.info(f"Pre-checkout успешен: {pre_checkout_query.from_user.id}")
        except Exception as e:
            logger.error(f"Ошибка pre-checkout: {e}")
            await self.bot.answer_pre_checkout_query(
                pre_checkout_query.id,
                ok=False,
                error_message="Произошла ошибка при оплате"
            )

    async def process_successful_payment(self, message: Message):
        try:
            payment = message.successful_payment
            payload = payment.invoice_payload
            user_id = message.from_user.id

            parts = payload.split("_")
            if len(parts) >= 2:
                days = int(parts[1])
                sub_type = get_subscription_type_text(days)

                self.db.set_premium(user_id, sub_type, days)
                self.db.log_payment(user_id, payment.total_amount, "stars", sub_type)

                await message.answer(
                    f"✅ Оплата прошла успешно!\n\nПодписка активирована:\n📅 Срок: {sub_type}\n\nСпасибо за поддержку проекта! ❤️",
                    parse_mode="HTML"
                )

                logger.info(f"Успешная оплата Stars: user={user_id}, days={days}, amount={payment.total_amount}")
            else:
                logger.error(f"Неверный формат payload: {payload}")
                await message.answer("❌ Ошибка при обработке платежа")

        except Exception as e:
            logger.error(f"Ошибка обработки успешного платежа: {e}")
            await message.answer("❌ Ошибка при активации подписки. Свяжитесь с поддержкой.")

    async def give_manual_subscription(self, user_id: int, days: int) -> bool:
        try:
            sub_type = get_subscription_type_text(days)
            self.db.set_premium(user_id, sub_type, days)
            self.db.log_payment(user_id, get_subscription_price(days), "manual", sub_type)
            logger.info(f"Ручная выдача подписки: user={user_id}, days={days}")
            return True
        except Exception as e:
            logger.error(f"Ошибка ручной выдачи подписки: {e}")
            return False

    def check_and_renew_expired(self):
        try:
            expired_count = self.db.check_premium_expired()
            if expired_count > 0:
                logger.info(f"Снято {expired_count} истекших подписок")
            return expired_count
        except Exception as e:
            logger.error(f"Ошибка проверки истекших подписок: {e}")
            return 0
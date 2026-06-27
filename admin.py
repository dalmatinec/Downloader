# admin.py
import asyncio
import logging
from datetime import datetime
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from utils import is_admin, format_size, get_subscription_type_text
from config import ADMIN_ID

logger = logging.getLogger(__name__)


# Состояния для админ-панели
class AdminStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_subscription_days = State()
    waiting_for_broadcast = State()
    waiting_for_user_info = State()


class AdminHandler:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db

    # ============================================
    # ГЛАВНАЯ АДМИН-ПАНЕЛЬ
    # ============================================

    async def show_admin_panel(self, message: Message, edit: bool = False):
        """Показать админ-панель"""
        user_id = message.from_user.id if hasattr(message, 'from_user') else message.chat.id

        if not is_admin(user_id):
            await message.answer("⛔ Нет доступа")
            return

        stats = self.db.get_stats()

        text = (
            f"🔐 Админ-панель\n\n"
            f"👥 Пользователей: {stats['total_users']}\n"
            f"❤️ Premium: {stats['premium_users']}\n"
            f"📥 Скачиваний: {stats['total_downloads']}\n"
            f"📅 За сутки: {stats['downloads_today']}\n\n"
            f"──────────────"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="❤️ Выдать подписку", callback_data="admin_give")],
            [InlineKeyboardButton(text="❌ Снять подписку", callback_data="admin_remove")],
            [InlineKeyboardButton(text="👤 Пользователь", callback_data="admin_user")],
            [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
        ])

        if edit:
            await message.edit_text(text, reply_markup=keyboard)
        else:
            await message.answer(text, reply_markup=keyboard)

    # ============================================
    # СТАТИСТИКА
    # ============================================

    async def show_stats(self, callback: CallbackQuery):
        """Показать развернутую статистику"""
        stats = self.db.get_stats()

        text = (
            f"📊 Статистика\n\n"
            f"👥 Всего пользователей: {stats['total_users']}\n"
            f"❤️ Активных подписчиков: {stats['premium_users']}\n"
            f"🆕 Новых за сутки: {stats['new_users_today']}\n\n"
            f"📥 Всего скачиваний: {stats['total_downloads']}\n"
            f"📥 За сутки: {stats['downloads_today']}\n\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard)

    # ============================================
    # ВЫДАТЬ ПОДПИСКУ
    # ============================================

    async def start_give_subscription(self, callback: CallbackQuery, state: FSMContext):
        """Начать выдачу подписки"""
        await state.set_state(AdminStates.waiting_for_user_id)
        await state.update_data(action="give")

        text = "❤️ Выдать подписку\n\nВведите Telegram ID пользователя:"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_panel")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard)

    async def process_user_id(self, message: Message, state: FSMContext):
        """Обработка введенного ID"""
        try:
            user_id = int(message.text.strip())
            user = self.db.get_user(user_id)

            if not user:
                await message.answer("❌ Пользователь не найден")
                return

            await state.update_data(target_user_id=user_id)
            await state.set_state(AdminStates.waiting_for_subscription_days)

            text = (
                f"👤 Пользователь найден: {user_id}\n\n"
                f"Выберите срок подписки:"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="1 месяц", callback_data="admin_sub_30")],
                [InlineKeyboardButton(text="3 месяца", callback_data="admin_sub_90")],
                [InlineKeyboardButton(text="6 месяцев", callback_data="admin_sub_180")],
                [InlineKeyboardButton(text="12 месяцев", callback_data="admin_sub_365")],
                [InlineKeyboardButton(text="Навсегда", callback_data="admin_sub_99999")],
                [InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_panel")]
            ])

            await message.answer(text, reply_markup=keyboard)

        except ValueError:
            await message.answer("❌ Введите корректный ID (только цифры)")

    async def process_give_subscription(self, callback: CallbackQuery, state: FSMContext):
        """Выдать подписку"""
        data = await state.get_data()
        user_id = data.get('target_user_id')
        days = int(callback.data.replace("admin_sub_", ""))

        if not user_id:
            await callback.message.edit_text("❌ Ошибка, попробуйте снова")
            await state.clear()
            return

        sub_type = get_subscription_type_text(days)

        # Выдаем подписку
        self.db.set_premium(user_id, sub_type, days)
        self.db.log_payment(user_id, 0, "admin_give", sub_type)

        await state.clear()

        text = (
            f"✅ Подписка выдана!\n\n"
            f"👤 Пользователь: {user_id}\n"
            f"📅 Срок: {sub_type}"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard)

        # Уведомление пользователю
        try:
            await self.bot.send_message(
                user_id,
                f"🌟 Вам выдана подписка: {sub_type}\nСпасибо за поддержку проекта! ❤️"
            )
        except:
            pass

    # ============================================
    # СНЯТЬ ПОДПИСКУ
    # ============================================

    async def start_remove_subscription(self, callback: CallbackQuery, state: FSMContext):
        """Начать снятие подписки"""
        await state.set_state(AdminStates.waiting_for_user_id)
        await state.update_data(action="remove")

        text = "❌ Снять подписку\n\nВведите Telegram ID пользователя:"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_panel")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard)

    async def process_remove_subscription(self, message: Message, state: FSMContext):
        """Снять подписку"""
        try:
            user_id = int(message.text.strip())
            user = self.db.get_user(user_id)

            if not user:
                await message.answer("❌ Пользователь не найден")
                return

            if not user[4]:  # is_premium
                await message.answer("❌ У пользователя нет активной подписки")
                return

            self.db.remove_premium(user_id)
            await state.clear()

            text = (
                f"✅ Подписка снята!\n\n"
                f"👤 Пользователь: {user_id}"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
            ])

            await message.answer(text, reply_markup=keyboard)

            # Уведомление пользователю
            try:
                await self.bot.send_message(
                    user_id,
                    "⏰ Ваша подписка отключена.\n\nЧтобы продолжить пользоваться преимуществами, оформите новую подписку в разделе '❤️ Поддержать проект'."
                )
            except:
                pass

        except ValueError:
            await message.answer("❌ Введите корректный ID (только цифры)")

    # ============================================
    # ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ
    # ============================================

    async def start_user_info(self, callback: CallbackQuery, state: FSMContext):
        """Начать поиск пользователя"""
        await state.set_state(AdminStates.waiting_for_user_info)

        text = "👤 Информация о пользователе\n\nВведите Telegram ID:"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_panel")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard)

    async def process_user_info(self, message: Message, state: FSMContext):
        """Показать информацию о пользователе"""
        try:
            user_id = int(message.text.strip())
            user = self.db.get_user(user_id)

            if not user:
                await message.answer("❌ Пользователь не найден")
                return

            await state.clear()

            # user: user_id, username, first_name, last_name, joined_date, is_premium, premium_until, subscription_type, total_downloads, is_active
            premium_status = "✅ Да" if user[5] else "❌ Нет"
            premium_until = user[6].strftime("%d.%m.%Y %H:%M") if user[6] else "—"
            subscription_type = user[7] or "—"
            username = f"@{user[1]}" if user[1] else "—"

            text = (
                f"👤 Информация о пользователе\n\n"
                f"🆔 ID: {user[0]}\n"
                f"👤 Имя: {user[2]} {user[3] or ''}\n"
                f"📱 Username: {username}\n"
                f"📅 Регистрация: {user[4].strftime('%d.%m.%Y %H:%M')}\n\n"
                f"❤️ Premium: {premium_status}\n"
                f"📅 До: {premium_until}\n"
                f"📋 Тип: {subscription_type}\n\n"
                f"📥 Скачиваний: {user[8]}"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
            ])

            await message.answer(text, reply_markup=keyboard)

        except ValueError:
            await message.answer("❌ Введите корректный ID (только цифры)")

    # ============================================
    # РАССЫЛКА
    # ============================================

    async def start_broadcast(self, callback: CallbackQuery, state: FSMContext):
        """Начать рассылку"""
        await state.set_state(AdminStates.waiting_for_broadcast)

        text = (
            "📢 Рассылка\n\n"
            "Перешлите сообщение, которое хотите отправить всем пользователям.\n\n"
            "⚠️ Сообщение будет отправлено как есть (Forward).\n"
            "💡 Премиум-пользователи получат уведомление, но без рекламы."
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_panel")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard)

    async def process_broadcast(self, message: Message, state: FSMContext):
        """Обработка рассылки"""
        # Проверяем что это пересланное сообщение
        if not message.forward_from and not message.forward_sender_name and not message.forward_from_chat:
            await message.answer("⚠️ Перешлите сообщение (Forward), а не копируйте текст")
            return

        await message.answer("⏳ Начинаю рассылку...")

        users = self.db.get_all_users()
        total = len(users)
        success = 0
        errors = 0

        for user in users:
            user_id = user[0]
            user_data = self.db.get_user(user_id)

            # Премиум-пользователи получают только уведомление (без рекламы в тексте)
            # Но мы отправляем всем одно и то же сообщение
            try:
                await message.forward(user_id)
                success += 1
            except Exception as e:
                errors += 1
                logger.error(f"Ошибка рассылки {user_id}: {e}")

            await asyncio.sleep(0.05)

        result_text = (
            f"✅ Рассылка завершена!\n\n"
            f"✅ Успешно: {success}\n"
            f"❌ Ошибок: {errors}\n"
            f"📤 Всего отправлено: {total}"
        )

        await message.answer(result_text)
        await state.clear()

    # ============================================
    # ОБРАБОТЧИК CALLBACK
    # ============================================

    async def handle_admin_callback(self, callback: CallbackQuery, state: FSMContext):
        """Обработка всех admin_* callback"""
        await callback.answer()

        action = callback.data

        if action == "admin_panel":
            await self.show_admin_panel(callback.message, edit=True)

        elif action == "admin_stats":
            await self.show_stats(callback)

        elif action == "admin_give":
            await self.start_give_subscription(callback, state)

        elif action == "admin_remove":
            await self.start_remove_subscription(callback, state)

        elif action == "admin_user":
            await self.start_user_info(callback, state)

        elif action == "admin_broadcast":
            await self.start_broadcast(callback, state)

        elif action.startswith("admin_sub_"):
            await self.process_give_subscription(callback, state)
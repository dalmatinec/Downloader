# admin.py - ЧАСТЬ 1
# ============================================
# АДМИН-ПАНЕЛЬ, СТАТИСТИКА, ВЫДАЧА ПОДПИСКИ
# ============================================

import logging
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from utils import is_admin, load_texts, get_subscription_type_text, get_subscription_price
from config import ADMIN_ID, MONTH_DAYS, THREE_MONTHS_DAYS, SIX_MONTHS_DAYS, YEAR_DAYS, LIFETIME

logger = logging.getLogger(__name__)


# Состояния для админ-панели
class AdminStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_subscription_type = State()
    waiting_for_broadcast = State()


class AdminHandler:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.texts = load_texts()

    async def show_admin_panel(self, message: Message):
        """Показать админ-панель"""
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            await message.answer(self.texts.get("admin_not_authorized", "⛔ Нет доступа"))
            return

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text="❤️ Выдать подписку", callback_data="admin_give_sub")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
        ])

        await message.answer(
            self.texts.get("admin_panel", "🔐 Админ-панель"),
            reply_markup=keyboard
        )

    async def show_stats(self, message: Message):
        """Показать статистику"""
        stats = self.db.get_stats()
        
        text = self.texts.get("admin_stats", "📊 Статистика").format(
            total_users=stats['total_users'],
            premium_users=stats['premium_users'],
            new_users=stats['new_users_today'],
            total_downloads=stats['total_downloads'],
            downloads_today=stats['downloads_today'],
            date=datetime.now().strftime("%d.%m.%Y")
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
        ])
        
        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

    async def start_give_subscription(self, message: Message, state: FSMContext):
        """Начать выдачу подписки"""
        await state.set_state(AdminStates.waiting_for_user_id)
        await message.answer(
            self.texts.get("admin_give_subscription", "Введите Telegram ID пользователя:"),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_panel")]
            ])
        )

    async def process_user_id(self, message: Message, state: FSMContext):
        """Обработка введенного ID"""
        try:
            user_id = int(message.text.strip())
            
            # Проверяем существует ли пользователь
            user = self.db.get_user(user_id)
            if not user:
                await message.answer(self.texts.get("admin_give_subscription_error", "❌ Пользователь не найден"))
                return
            
            # Сохраняем ID в состояние
            await state.update_data(user_id=user_id)
            await state.set_state(AdminStates.waiting_for_subscription_type)
            
            # Показываем выбор срока
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="1 месяц", callback_data="sub_give_30")],
                [InlineKeyboardButton(text="3 месяца", callback_data="sub_give_90")],
                [InlineKeyboardButton(text="6 месяцев", callback_data="sub_give_180")],
                [InlineKeyboardButton(text="12 месяцев", callback_data="sub_give_365")],
                [InlineKeyboardButton(text="Навсегда", callback_data="sub_give_99999")],
                [InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_panel")]
            ])
            
            await message.answer(
                self.texts.get("admin_give_subscription_type", "Выберите срок подписки:"),
                reply_markup=keyboard
            )
            
        except ValueError:
            await message.answer("❌ Введите корректный ID (только цифры)")

    async def process_give_subscription(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора срока подписки"""
        await callback.answer()
        
        data = await state.get_data()
        user_id = data.get('user_id')
        
        if not user_id:
            await callback.message.answer("❌ Ошибка, попробуйте снова")
            await state.clear()
            return
        
        # Получаем количество дней
        days = int(callback.data.replace("sub_give_", ""))
        sub_type = get_subscription_type_text(days)
        
        # Выдаем подписку
        self.db.set_premium(user_id, sub_type, days)
        self.db.log_payment(user_id, get_subscription_price(days), "manual", sub_type)
        
        # Отправляем сообщение админу
        await callback.message.edit_text(
            self.texts.get("admin_give_subscription_success", "✅ Подписка выдана!").format(
                user_id=user_id,
                subscription=sub_type
            ),
            parse_mode="HTML"
        )
        
        # Отправляем сообщение пользователю
        try:
            await self.bot.send_message(
                user_id,
                f"🌟 Вам выдана подписка: {sub_type}\nСпасибо за поддержку проекта! ❤️"
            )
        except:
            pass
        
        await state.clear()
# admin.py - ЧАСТЬ 2
# ============================================
# РАССЫЛКА + ОБРАБОТЧИКИ CALLBACK
# ============================================

    async def start_broadcast(self, message: Message, state: FSMContext):
        """Начать рассылку"""
        await state.set_state(AdminStates.waiting_for_broadcast)
        await message.answer(
            self.texts.get("admin_broadcast", "📢 Перешлите сообщение для рассылки:"),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_panel")]
            ])
        )

    async def process_broadcast(self, message: Message, state: FSMContext):
        """Обработка рассылки"""
        # Проверяем что это пересланное сообщение
        if not message.forward_from and not message.forward_sender_name:
            await message.answer("⚠️ Перешлите сообщение (Forward), а не копируйте текст")
            return
        
        await message.answer("⏳ Начинаю рассылку...")
        
        # Получаем всех пользователей
        users = self.db.get_all_users()
        total = len(users)
        
        success = 0
        errors = 0
        
        for user in users:
            user_id = user[0]
            
            # Проверяем - если премиум, пропускаем
            user_data = self.db.get_user(user_id)
            if user_data and user_data[4]:  # is_premium
                continue
                
            try:
                # Отправляем форвард (оригинал сообщения)
                await message.forward(user_id)
                success += 1
            except Exception as e:
                errors += 1
                logger.error(f"Ошибка рассылки {user_id}: {e}")
            
            # Небольшая задержка чтобы не получить бан
            await asyncio.sleep(0.05)
        
        # Отправляем результат
        result_text = self.texts.get("admin_broadcast_success", "✅ Рассылка завершена!").format(
            success=success,
            errors=errors,
            total=total
        )
        
        await message.answer(result_text, parse_mode="HTML")
        await state.clear()

    async def handle_admin_callback(self, callback: CallbackQuery, state: FSMContext):
        """Обработка callback кнопок админ-панели"""
        await callback.answer()
        
        action = callback.data
        
        if action == "admin_panel":
            await self.show_admin_panel(callback.message)
            
        elif action == "admin_stats":
            await self.show_stats(callback.message)
            
        elif action == "admin_broadcast":
            await self.start_broadcast(callback.message, state)
            
        elif action == "admin_give_sub":
            await self.start_give_subscription(callback.message, state)
            
        elif action.startswith("sub_give_"):
            await self.process_give_subscription(callback, state)

    async def cancel_admin_action(self, message: Message, state: FSMContext):
        """Отмена действия"""
        await state.clear()
        await self.show_admin_panel(message)
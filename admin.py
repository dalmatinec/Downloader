# admin.py
import logging
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import Bot

import database as db
from config import ADMIN_ID
from utils import format_subscription_type

logger = logging.getLogger(__name__)
router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


class AdminStates(StatesGroup):
    broadcast_text = State()
    add_sub_user = State()
    add_sub_days = State()
    del_sub_user = State()
    ban_user = State()
    unban_user = State()


def admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_broadcast"),
        ],
        [
            InlineKeyboardButton(text="⭐ Выдать подписку", callback_data="admin_add_sub"),
            InlineKeyboardButton(text="❌ Убрать подписку", callback_data="admin_del_sub"),
        ],
        [
            InlineKeyboardButton(text="🚫 Бан", callback_data="admin_ban"),
            InlineKeyboardButton(text="✅ Разбан", callback_data="admin_unban"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_start")],
    ])


def back_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]
    ])


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        return
    await message.answer("🛠 Панель администратора", reply_markup=admin_kb())


@router.callback_query(F.data == "admin_back")
async def admin_back(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа")
        return
    await state.clear()
    await call.message.edit_text("🛠 Панель администратора", reply_markup=admin_kb())


@router.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа")
        return
    stats = db.get_stats()
    text = (
        f"📊 Статистика\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"⭐ Премиум: {stats['premium_users']}\n"
        f"📥 Всего скачиваний: {stats['total_downloads']}"
    )
    await call.message.edit_text(text, reply_markup=back_admin_kb())


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа")
        return
    await state.set_state(AdminStates.broadcast_text)
    await call.message.edit_text(
        "📨 Введите текст рассылки (только обычным пользователям):\n\n"
        "Для отмены — /admin",
        reply_markup=back_admin_kb()
    )


@router.message(AdminStates.broadcast_text)
async def admin_broadcast_send(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    
    if not message.text:
        await message.answer("❌ Текст не может быть пустым")
        return
    
    await state.clear()
    users = db.get_regular_users()
    sent = 0
    failed = 0
    status_msg = await message.answer(f"⏳ Отправка рассылки {len(users)} пользователям...")
    
    for uid in users:
        try:
            await bot.send_message(uid, message.text)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    
    await status_msg.edit_text(
        f"✅ Рассылка завершена\n\n"
        f"✔️ Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}"
    )


@router.callback_query(F.data == "admin_add_sub")
async def admin_add_sub_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа")
        return
    await state.set_state(AdminStates.add_sub_user)
    await call.message.edit_text(
        "⭐ Введите user_id пользователя:",
        reply_markup=back_admin_kb()
    )


@router.message(AdminStates.add_sub_user)
async def admin_add_sub_user(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not message.text:
        await message.answer("❌ Введите ID")
        return
    
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный ID. Введите число.")
        return
    
    # Проверяем существование пользователя
    user = db.get_user(uid)
    if not user:
        await message.answer(f"❌ Пользователь с ID {uid} не найден в базе.")
        return
    
    await state.update_data(target_uid=uid)
    await state.set_state(AdminStates.add_sub_days)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1 месяц", callback_data="givesub_1_month"),
            InlineKeyboardButton(text="3 месяца", callback_data="givesub_3_months"),
        ],
        [
            InlineKeyboardButton(text="6 месяцев", callback_data="givesub_6_months"),
            InlineKeyboardButton(text="12 месяцев", callback_data="givesub_12_months"),
        ],
        [InlineKeyboardButton(text="Навсегда", callback_data="givesub_lifetime")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")],
    ])
    await message.answer(f"Выберите срок подписки для {uid}:", reply_markup=kb)


@router.callback_query(F.data.startswith("givesub_"))
async def admin_give_sub(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа")
        return
    
    from payment import PLANS
    plan_key = call.data.replace("givesub_", "")
    data = await state.get_data()
    uid = data.get("target_uid")
    
    if not uid:
        await call.answer("❌ Ошибка: пользователь не найден")
        return
    
    if plan_key not in PLANS:
        await call.answer("❌ Неверный план")
        return
    
    plan = PLANS[plan_key]
    db.add_subscription(uid, plan_key, plan["days"])
    await state.clear()
    
    await call.message.edit_text(
        f"✅ Подписка «{plan['label']}» выдана пользователю {uid}.",
        reply_markup=back_admin_kb()
    )


@router.callback_query(F.data == "admin_del_sub")
async def admin_del_sub_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа")
        return
    
    await state.update_data(action="del_sub")
    await state.set_state(AdminStates.del_sub_user)
    await call.message.edit_text(
        "❌ Введите user_id для снятия подписки:",
        reply_markup=back_admin_kb()
    )


@router.callback_query(F.data == "admin_ban")
async def admin_ban_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа")
        return
    await state.set_state(AdminStates.ban_user)
    await state.update_data(action="ban")
    await call.message.edit_text("🚫 Введите user_id для бана:", reply_markup=back_admin_kb())


@router.callback_query(F.data == "admin_unban")
async def admin_unban_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа")
        return
    await state.set_state(AdminStates.ban_user)
    await state.update_data(action="unban")
    await call.message.edit_text("✅ Введите user_id для разбана:", reply_markup=back_admin_kb())


@router.message(AdminStates.ban_user)
async def admin_action_ban(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not message.text:
        await message.answer("❌ Введите ID")
        return
    
    data = await state.get_data()
    action = data.get("action", "ban")
    
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный ID. Введите число.")
        return
    
    await state.clear()
    
    if action == "ban":
        db.ban_user(uid)
        await message.answer(f"🚫 Пользователь {uid} заблокирован.", reply_markup=back_admin_kb())
    elif action == "unban":
        db.unban_user(uid)
        await message.answer(f"✅ Пользователь {uid} разблокирован.", reply_markup=back_admin_kb())


@router.message(AdminStates.del_sub_user)
async def admin_action_del_sub(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not message.text:
        await message.answer("❌ Введите ID")
        return
    
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный ID. Введите число.")
        return
    
    await state.clear()
    
    # Проверяем есть ли подписка
    sub = db.get_subscription(uid)
    if not sub:
        await message.answer(f"❌ У пользователя {uid} нет активной подписки.", reply_markup=back_admin_kb())
        return
    
    db.remove_subscription(uid)
    await message.answer(f"❌ Подписка пользователя {uid} удалена.", reply_markup=back_admin_kb())
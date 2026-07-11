# setting_handlers.py
import json
import logging
import os
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
import texts
from admin_handlers import is_admin
from keyboards import (
    get_admin_settings_kb,
    get_admin_settings_payments_kb,
    get_admin_settings_maintenance_kb,
    get_back_kb,
    get_cancel_kb
)
from utils import safe_send_message, safe_edit_message, escape_html


logger = logging.getLogger(__name__)
router = Router()

SETTINGS_FILE = "settings.json"


# ============================================================
# РАБОТА С JSON
# ============================================================

def load_settings() -> dict:
    if not os.path.exists(SETTINGS_FILE):
        default = {
            "KASPI_VISA": config.KASPI_VISA,
            "FREEDOM_VISA": config.FREEDOM_VISA,
            "BCC_VISA": config.BCC_VISA,
            "RU_PHONE": config.RU_PHONE,
            "PAYPAL": config.PAYPAL,
            "MAINTENANCE_MODE": False,
            "MAINTENANCE_MESSAGE": "🔧 Ведутся технические работы. Бот временно недоступен. Загляните позже!"
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        return default
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_settings(settings: dict) -> None:
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
    for key, value in settings.items():
        if hasattr(config, key):
            setattr(config, key, value)


# ============================================================
# FSM
# ============================================================

class SettingsStates(StatesGroup):
    waiting_value = State()
    waiting_confirm = State()


# ============================================================
# КОМАНДА
# ============================================================

@router.message(Command("settings"))
async def settings_command(message: Message) -> None:
    if not await is_admin(message.from_user.id):
        return
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text="⚙️ <b>Настройки бота</b>\n\nВыберите раздел:",
        reply_markup=get_admin_settings_kb()
    )


@router.callback_query(F.data == "admin:settings")
async def admin_settings_callback(callback: CallbackQuery) -> None:
    if not await is_admin(callback.from_user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text="⚙️ <b>Настройки бота</b>\n\nВыберите раздел:",
        reply_markup=get_admin_settings_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "admin:settings:payments")
async def admin_settings_payments(callback: CallbackQuery) -> None:
    if not await is_admin(callback.from_user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text="💳 <b>Реквизиты</b>\n\nВыберите, что хотите изменить или посмотреть:",
        reply_markup=get_admin_settings_payments_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "admin:settings:maintenance")
async def admin_settings_maintenance(callback: CallbackQuery) -> None:
    if not await is_admin(callback.from_user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    settings = load_settings()
    mode = settings.get("MAINTENANCE_MODE", False)
    message = settings.get("MAINTENANCE_MESSAGE", "🔧 Ведутся технические работы.")
    text = f"🔧 <b>Технические работы</b>\n\n"
    text += f"Статус: {'🔴 Включены' if mode else '🟢 Выключены'}\n"
    text += f"Сообщение: {message}\n\n"
    text += "Выберите действие:"
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=text,
        reply_markup=get_admin_settings_maintenance_kb(mode)
    )
    await callback.answer()


@router.callback_query(F.data == "back:admin:settings")
async def back_to_admin_settings(callback: CallbackQuery) -> None:
    """Возврат в меню настроек из подразделов"""
    if not await is_admin(callback.from_user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text="⚙️ <b>Настройки бота</b>\n\nВыберите раздел:",
        reply_markup=get_admin_settings_kb()
    )
    await callback.answer()


# ============================================================
# ПРОСМОТР ВСЕХ ЗНАЧЕНИЙ
# ============================================================

@router.callback_query(F.data == "settings:payment:view_all")
async def view_all_payments(callback: CallbackQuery) -> None:
    if not await is_admin(callback.from_user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    settings = load_settings()
    text = "💳 <b>Все реквизиты</b>\n\n"
    text += f"🟢 Kaspi: {settings.get('KASPI_VISA') or 'не установлен'}\n"
    text += f"💳 Freedom: {settings.get('FREEDOM_VISA') or 'не установлен'}\n"
    text += f"🏦 BCC: {settings.get('BCC_VISA') or 'не установлен'}\n"
    text += f"📱 РФ номер: {settings.get('RU_PHONE') or 'не установлен'}\n"
    text += f"💙 PayPal: {settings.get('PAYPAL') or 'не установлен'}"
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=text,
        reply_markup=get_back_kb("back:admin:settings")
    )
    await callback.answer()


# ============================================================
# РЕДАКТИРОВАНИЕ
# ============================================================

async def start_edit(callback: CallbackQuery, state: FSMContext, key: str, prompt: str) -> None:
    if not await is_admin(callback.from_user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await state.update_data(edit_key=key)
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=f"✏️ {prompt}\n\nВведите новое значение:",
        reply_markup=get_cancel_kb()
    )
    await state.set_state(SettingsStates.waiting_value)
    await callback.answer()


@router.callback_query(F.data == "settings:payment:kaspi")
async def edit_kaspi(callback: CallbackQuery, state: FSMContext) -> None:
    await start_edit(callback, state, "KASPI_VISA", "🟢 Введите новый Kaspi")


@router.callback_query(F.data == "settings:payment:freedom")
async def edit_freedom(callback: CallbackQuery, state: FSMContext) -> None:
    await start_edit(callback, state, "FREEDOM_VISA", "💳 Введите новый Freedom")


@router.callback_query(F.data == "settings:payment:bcc")
async def edit_bcc(callback: CallbackQuery, state: FSMContext) -> None:
    await start_edit(callback, state, "BCC_VISA", "🏦 Введите новый Банк ЦентрКредит")


@router.callback_query(F.data == "settings:payment:ru_phone")
async def edit_ru_phone(callback: CallbackQuery, state: FSMContext) -> None:
    await start_edit(callback, state, "RU_PHONE", "📱 Введите новый РФ номер")


@router.callback_query(F.data == "settings:payment:paypal")
async def edit_paypal(callback: CallbackQuery, state: FSMContext) -> None:
    await start_edit(callback, state, "PAYPAL", "💙 Введите новый PayPal")


# ============================================================
# ПОДТВЕРЖДЕНИЕ
# ============================================================

@router.message(StateFilter(SettingsStates.waiting_value))
async def receive_value(message: Message, state: FSMContext) -> None:
    if not await is_admin(message.from_user.id):
        return
    data = await state.get_data()
    key = data.get("edit_key")
    value = message.text.strip()
    await state.update_data(edit_value=value)
    await safe_send_message(
        bot=message.bot,
        chat_id=message.chat.id,
        text=f"📝 Новое значение:\n\n{escape_html(value)}\n\nСохранить?",
        reply_markup=get_confirm_kb()
    )
    await state.set_state(SettingsStates.waiting_confirm)


@router.callback_query(F.data.startswith("settings:confirm"))
async def confirm_edit(callback: CallbackQuery, state: FSMContext) -> None:
    if not await is_admin(callback.from_user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    data = await state.get_data()
    key = data.get("edit_key")
    value = data.get("edit_value")
    if not key or not value:
        await callback.answer("❌ Ошибка: данные не найдены")
        return
    settings = load_settings()
    settings[key] = value
    save_settings(settings)
    logger.info(f"Settings updated: {key} by {callback.from_user.id}")
    await state.clear()
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text=f"✅ <b>{key}</b> успешно обновлён!\n\nНовое значение:\n{escape_html(value)}",
        reply_markup=get_back_kb("back:admin:settings")
    )
    await callback.answer()


@router.callback_query(F.data == "settings:cancel")
async def cancel_edit(callback: CallbackQuery, state: FSMContext) -> None:
    if not await is_admin(callback.from_user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await state.clear()
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text="❌ Действие отменено",
        reply_markup=get_back_kb("back:admin:settings")
    )
    await callback.answer()


# ============================================================
# ТЕХНИЧЕСКИЕ РАБОТЫ
# ============================================================

@router.callback_query(F.data == "settings:maintenance:toggle")
async def maintenance_toggle(callback: CallbackQuery) -> None:
    if not await is_admin(callback.from_user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    settings = load_settings()
    settings["MAINTENANCE_MODE"] = not settings.get("MAINTENANCE_MODE", False)
    save_settings(settings)
    await callback.answer(f"Технические работы {'включены' if settings['MAINTENANCE_MODE'] else 'выключены'}")
    await admin_settings_maintenance(callback)


@router.callback_query(F.data == "settings:maintenance:message")
async def maintenance_message_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await is_admin(callback.from_user.id):
        await callback.answer(texts.ACCESS_DENIED)
        return
    await state.update_data(edit_key="MAINTENANCE_MESSAGE")
    await safe_edit_message(
        bot=callback.bot,
        callback=callback,
        text="✏️ Введите текст сообщения о технических работах:",
        reply_markup=get_cancel_kb()
    )
    await state.set_state(SettingsStates.waiting_value)
    await callback.answer()


# ============================================================
# КЛАВИАТУРА ПОДТВЕРЖДЕНИЯ
# ============================================================

def get_confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✅ Да", callback_data="settings:confirm"),
        InlineKeyboardButton(text="❌ Нет", callback_data="settings:cancel")
    )
    builder.adjust(2)
    return builder.as_markup()
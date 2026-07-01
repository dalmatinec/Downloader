# callbacks.py - ЧАСТЬ 1 (Импорты, Навигация, Контент)
from aiogram import types
from aiogram.dispatcher import FSMContext
import logging
import uuid

from config import ADMIN_IDS
from admin import AdminPanel, AdminStates
from keyboards import KeyboardBuilder
from handlers import Handlers


logger = logging.getLogger(__name__)


class Callbacks:
    """Обработчики callback-запросов"""

    def __init__(self, dp, db):
        self.dp = dp
        self.db = db
        self.admin = AdminPanel(db)
        self.handlers = Handlers(dp, db)

    def register(self):
        """Регистрация всех callback-обработчиков"""

        # ============================================
        # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
        # ============================================

        def is_admin(user_id: int) -> bool:
            return user_id in ADMIN_IDS

        def get_community_id(message: types.Message) -> str:
            return self.admin.get_or_create_community(str(message.chat.id), message.chat.title)

        # ============================================
        # НАВИГАЦИЯ
        # ============================================

        @self.dp.callback_query_handler(lambda c: c.data == 'back_to_main', state="*")
        async def back_to_main_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            community_id = get_community_id(callback.message)
            await state.set_state(AdminStates.MAIN)
            
            menu = self.admin.get_admin_main_menu(community_id, callback.from_user.id)
            await callback.message.edit_text("Панель администратора", reply_markup=menu)

        @self.dp.callback_query_handler(lambda c: c.data == 'back_to_content', state="*")
        async def back_to_content_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            community_id = get_community_id(callback.message)
            await self.handlers._show_content_list(callback.message, state, community_id)

        # ============================================
        # КОНТЕНТ
        # ============================================

        @self.dp.callback_query_handler(lambda c: c.data.startswith('content_page_'), state="*")
        async def content_page_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            page = int(callback.data.split('_')[2])
            community_id = get_community_id(callback.message)
            
            text = self.admin.get_content_list_text(community_id, page)
            contents, total = self.admin.get_content_paginated(community_id, active_only=False, limit=10, offset=page*10)
            
            buttons = []
            if page > 0:
                buttons.append({"text": "⬅️", "callback_data": f"content_page_{page-1}"})
            
            total_pages = (total // 10) + (1 if total % 10 else 0)
            if page < total_pages - 1:
                buttons.append({"text": "➡️", "callback_data": f"content_page_{page+1}"})
            
            buttons.append({"text": "➕ Добавить", "callback_data": "content_create"})
            buttons.append({"text": "🔙 Назад", "callback_data": "back_to_main"})
            
            keyboard = KeyboardBuilder.build_inline(buttons, row_width=2)
            await callback.message.edit_text(text, reply_markup=keyboard)

        @self.dp.callback_query_handler(lambda c: c.data == 'content_create', state="*")
        async def content_create_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            content_types = self.admin.content.get_content_types()
            buttons = []
            for ct in content_types:
                buttons.append({"text": ct.get('name'), "callback_data": f"content_type_{ct['id']}"})
            buttons.append({"text": "❌ Отмена", "callback_data": "back_to_content"})
            
            keyboard = KeyboardBuilder.build_inline(buttons, row_width=2)
            await callback.message.edit_text("Выберите тип контента:", reply_markup=keyboard)
            await state.set_state(AdminStates.CONTENT_CREATE_TYPE)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('content_type_'), state=AdminStates.CONTENT_CREATE_TYPE)
        async def content_type_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            type_id = callback.data.split('_')[2]
            await state.update_data(content_type_id=type_id)
            await callback.message.edit_text("Введите название контента:")
            await state.set_state(AdminStates.CONTENT_CREATE_TITLE)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('content_edit_'), state="*")
        async def content_edit_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            content_id = callback.data.split('_')[2]
            await state.update_data(edit_content_id=content_id)
            
            content = self.admin.content.get(content_id)
            if not content:
                await callback.message.edit_text("Контент не найден")
                return
            
            text = f"✏️ Редактирование контента:\n\n"
            text += f"Название: {content.get('title')}\n"
            text += f"Описание: {content.get('description') or 'Нет'}\n"
            text += f"Тип: {content.get('type_name')}\n"
            text += f"Статус: {'✅ Активен' if content.get('is_active', 1) else '❌ Неактивен'}\n"
            
            buttons = [
                {"text": "📌 Название", "callback_data": f"content_edit_title_{content_id}"},
                {"text": "📝 Описание", "callback_data": f"content_edit_desc_{content_id}"},
                {"text": "📎 Файл", "callback_data": f"content_edit_file_{content_id}"},
                {"text": "🏷 Теги", "callback_data": f"content_edit_tags_{content_id}"},
                {"text": "🔄 Статус", "callback_data": f"content_toggle_{content_id}"},
                {"text": "🗑 Удалить", "callback_data": f"content_delete_{content_id}"},
                {"text": "🔙 Назад", "callback_data": "back_to_content"}
            ]
            keyboard = KeyboardBuilder.build_inline(buttons, row_width=2)
            await callback.message.edit_text(text, reply_markup=keyboard)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('content_toggle_'), state="*")
        async def content_toggle_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            content_id = callback.data.split('_')[2]
            content = self.admin.content.get(content_id)
            if not content:
                await callback.message.edit_text("Контент не найден")
                return
            
            new_status = 0 if content.get('is_active', 1) else 1
            self.admin.content.update(content_id, {'is_active': new_status})
            
            await callback.message.edit_text(f"✅ Статус изменен на {'активен' if new_status else 'неактивен'}")
            await state.update_data(edit_content_id=content_id)
            await self.content_edit_callback(callback, state)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('content_delete_'), state="*")
        async def content_delete_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            content_id = callback.data.split('_')[2]
            await state.update_data(delete_content_id=content_id)
            
            buttons = [
                {"text": "✅ Да, удалить", "callback_data": f"content_delete_confirm_{content_id}"},
                {"text": "❌ Отмена", "callback_data": f"content_edit_{content_id}"}
            ]
            keyboard = KeyboardBuilder.build_inline(buttons)
            await callback.message.edit_text("⚠️ Вы уверены, что хотите удалить этот контент?", reply_markup=keyboard)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('content_delete_confirm_'), state="*")
        async def content_delete_confirm_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            content_id = callback.data.split('_')[3]
            self.admin.content.delete(content_id, soft=False)
            
            community_id = get_community_id(callback.message)
            await callback.message.edit_text("✅ Контент удален")
            await self.handlers._show_content_list(callback.message, state, community_id)

# callbacks.py - ЧАСТЬ 2 (Меню, Кнопки, Настройки)
        # ============================================
        # МЕНЮ
        # ============================================

        @self.dp.callback_query_handler(lambda c: c.data == 'menu_create', state="*")
        async def menu_create_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            await callback.message.edit_text("Введите название меню:")
            await state.set_state(AdminStates.MENU_CREATE_NAME)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('menu_edit_'), state="*")
        async def menu_edit_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            menu_id = callback.data.split('_')[2]
            await state.update_data(edit_menu_id=menu_id)
            
            menu = self.admin.menu.get_menu(menu_id)
            if not menu:
                await callback.message.edit_text("Меню не найдено")
                return
            
            text = f"✏️ Редактирование меню:\n\n"
            text += f"Название: {menu.get('name')}\n"
            text += f"Статус: {'✅ Активно' if menu.get('is_active', 1) else '❌ Неактивно'}\n"
            text += f"Главное: {'⭐ Да' if menu.get('is_main', 0) else 'Нет'}\n"
            
            buttons = [
                {"text": "📌 Название", "callback_data": f"menu_edit_name_{menu_id}"},
                {"text": "🔄 Статус", "callback_data": f"menu_toggle_{menu_id}"},
                {"text": "🔘 Кнопки", "callback_data": f"menu_buttons_{menu_id}"},
                {"text": "🗑 Удалить", "callback_data": f"menu_delete_{menu_id}"},
                {"text": "🔙 Назад", "callback_data": "back_to_menu"}
            ]
            keyboard = KeyboardBuilder.build_inline(buttons, row_width=2)
            await callback.message.edit_text(text, reply_markup=keyboard)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('menu_toggle_'), state="*")
        async def menu_toggle_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            menu_id = callback.data.split('_')[2]
            menu = self.admin.menu.get_menu(menu_id)
            if not menu:
                await callback.message.edit_text("Меню не найдено")
                return
            
            new_status = 0 if menu.get('is_active', 1) else 1
            self.admin.menu.update_menu(menu_id, {'is_active': new_status})
            
            await callback.message.edit_text(f"✅ Статус изменен на {'активно' if new_status else 'неактивно'}")
            await self.menu_edit_callback(callback, state)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('menu_delete_'), state="*")
        async def menu_delete_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            menu_id = callback.data.split('_')[2]
            await state.update_data(delete_menu_id=menu_id)
            
            buttons = [
                {"text": "✅ Да, удалить", "callback_data": f"menu_delete_confirm_{menu_id}"},
                {"text": "❌ Отмена", "callback_data": f"menu_edit_{menu_id}"}
            ]
            keyboard = KeyboardBuilder.build_inline(buttons)
            await callback.message.edit_text("⚠️ Вы уверены, что хотите удалить это меню?", reply_markup=keyboard)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('menu_delete_confirm_'), state="*")
        async def menu_delete_confirm_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            menu_id = callback.data.split('_')[3]
            self.admin.menu.delete_menu(menu_id, soft=False)
            
            community_id = get_community_id(callback.message)
            await callback.message.edit_text("✅ Меню удалено")
            await self.handlers._show_menu_list(callback.message, state, community_id)

        @self.dp.callback_query_handler(lambda c: c.data == 'back_to_menu', state="*")
        async def back_to_menu_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            community_id = get_community_id(callback.message)
            await self.handlers._show_menu_list(callback.message, state, community_id)

        # ============================================
        # КНОПКИ
        # ============================================

        @self.dp.callback_query_handler(lambda c: c.data.startswith('menu_buttons_'), state="*")
        async def menu_buttons_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            menu_id = callback.data.split('_')[2]
            await state.update_data(current_menu_id=menu_id)
            
            buttons = self.admin.menu.get_all_menu_buttons(menu_id, active_only=False)
            
            if not buttons:
                text = "🔘 Кнопок нет"
            else:
                text = "🔘 Список кнопок:\n\n"
                for btn in buttons:
                    status = "✅" if btn.get('is_active', 1) else "❌"
                    action = btn.get('action_name', 'Неизвестно')
                    text += f"{status} {btn.get('text')} [{action}] ряд {btn.get('row_num', 0)}/{btn.get('order_num', 0)}\n"
            
            inline_buttons = [
                {"text": "➕ Добавить кнопку", "callback_data": f"button_create_{menu_id}"},
                {"text": "🔙 Назад", "callback_data": f"menu_edit_{menu_id}"}
            ]
            keyboard = KeyboardBuilder.build_inline(inline_buttons)
            await callback.message.edit_text(text, reply_markup=keyboard)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('button_create_'), state="*")
        async def button_create_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            menu_id = callback.data.split('_')[2]
            await state.update_data(button_menu_id=menu_id)
            await callback.message.edit_text("Введите текст кнопки:")
            await state.set_state(AdminStates.BUTTON_CREATE_TEXT)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('button_edit_'), state="*")
        async def button_edit_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            button_id = callback.data.split('_')[2]
            await state.update_data(edit_button_id=button_id)
            
            button = self.admin.menu.get_button(button_id)
            if not button:
                await callback.message.edit_text("Кнопка не найдена")
                return
            
            text = f"✏️ Редактирование кнопки:\n\n"
            text += f"Текст: {button.get('text')}\n"
            text += f"Действие: {button.get('action_name')}\n"
            text += f"Ряд: {button.get('row_num', 0)}\n"
            text += f"Порядок: {button.get('order_num', 0)}\n"
            text += f"Статус: {'✅ Активна' if button.get('is_active', 1) else '❌ Неактивна'}\n"
            
            buttons = [
                {"text": "📌 Текст", "callback_data": f"button_edit_text_{button_id}"},
                {"text": "⚡ Действие", "callback_data": f"button_edit_action_{button_id}"},
                {"text": "📏 Ряд", "callback_data": f"button_edit_row_{button_id}"},
                {"text": "🔢 Порядок", "callback_data": f"button_edit_order_{button_id}"},
                {"text": "🔄 Статус", "callback_data": f"button_toggle_{button_id}"},
                {"text": "🗑 Удалить", "callback_data": f"button_delete_{button_id}"},
                {"text": "🔙 Назад", "callback_data": "back_to_buttons"}
            ]
            keyboard = KeyboardBuilder.build_inline(buttons, row_width=2)
            await callback.message.edit_text(text, reply_markup=keyboard)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('button_toggle_'), state="*")
        async def button_toggle_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            button_id = callback.data.split('_')[2]
            button = self.admin.menu.get_button(button_id)
            if not button:
                await callback.message.edit_text("Кнопка не найдена")
                return
            
            new_status = 0 if button.get('is_active', 1) else 1
            self.admin.menu.update_button(button_id, {'is_active': new_status})
            
            await callback.message.edit_text(f"✅ Статус изменен на {'активна' if new_status else 'неактивна'}")
            await self.button_edit_callback(callback, state)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('button_delete_'), state="*")
        async def button_delete_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            button_id = callback.data.split('_')[2]
            await state.update_data(delete_button_id=button_id)
            
            buttons = [
                {"text": "✅ Да, удалить", "callback_data": f"button_delete_confirm_{button_id}"},
                {"text": "❌ Отмена", "callback_data": f"button_edit_{button_id}"}
            ]
            keyboard = KeyboardBuilder.build_inline(buttons)
            await callback.message.edit_text("⚠️ Вы уверены, что хотите удалить эту кнопку?", reply_markup=keyboard)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('button_delete_confirm_'), state="*")
        async def button_delete_confirm_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            button_id = callback.data.split('_')[3]
            self.admin.menu.delete_button(button_id, soft=False)
            
            await callback.message.edit_text("✅ Кнопка удалена")
            
            data = await state.get_data()
            menu_id = data.get('current_menu_id')
            if menu_id:
                await state.update_data(current_menu_id=menu_id)
                await self.menu_buttons_callback(callback, state)

        @self.dp.callback_query_handler(lambda c: c.data == 'back_to_buttons', state="*")
        async def back_to_buttons_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            data = await state.get_data()
            menu_id = data.get('current_menu_id')
            if menu_id:
                await state.update_data(current_menu_id=menu_id)
                await self.menu_buttons_callback(callback, state)

        # ============================================
        # НАСТРОЙКИ
        # ============================================

        @self.dp.callback_query_handler(lambda c: c.data.startswith('settings_category_'), state="*")
        async def settings_category_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            community_id = get_community_id(callback.message)
            category = callback.data.split('_')[2]
            
            text = self.admin.get_settings_text(community_id, category)
            buttons = [
                {"text": "🔙 Назад", "callback_data": "back_to_settings"}
            ]
            keyboard = KeyboardBuilder.build_inline(buttons)
            await callback.message.edit_text(text, reply_markup=keyboard)

        @self.dp.callback_query_handler(lambda c: c.data == 'back_to_settings', state="*")
        async def back_to_settings_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            community_id = get_community_id(callback.message)
            await self.handlers._show_settings_menu(callback.message, state, community_id)

        @self.dp.callback_query_handler(lambda c: c.data == 'settings_add', state="*")
        async def settings_add_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            await callback.message.edit_text("Введите категорию:")
            await state.set_state(AdminStates.SETTINGS_CREATE_CATEGORY)

# callbacks.py - ЧАСТЬ 3 (Пользователи, Модерация, Роли, Права, Статистика, Логи)
        # ============================================
        # ПОЛЬЗОВАТЕЛИ
        # ============================================

        @self.dp.callback_query_handler(lambda c: c.data.startswith('users_page_'), state="*")
        async def users_page_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            page = int(callback.data.split('_')[2])
            community_id = get_community_id(callback.message)
            await self.handlers._show_users_list(callback.message, state, community_id, page)

        @self.dp.callback_query_handler(lambda c: c.data == 'users_search', state="*")
        async def users_search_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            await callback.message.edit_text("Введите ID, username или имя для поиска:")
            await state.set_state(AdminStates.USERS_SEARCH)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('user_view_'), state="*")
        async def user_view_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            user_id = int(callback.data.split('_')[2])
            community_id = get_community_id(callback.message)
            chat_id = self.admin.get_chat_id_by_community(community_id)
            
            if not chat_id:
                await callback.message.edit_text("Чат не найден")
                return
            
            text = self.admin.get_user_info_text(chat_id, user_id)
            buttons = [
                {"text": "🔙 Назад", "callback_data": "back_to_users"}
            ]
            keyboard = KeyboardBuilder.build_inline(buttons)
            await callback.message.edit_text(text, reply_markup=keyboard)

        @self.dp.callback_query_handler(lambda c: c.data == 'back_to_users', state="*")
        async def back_to_users_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            community_id = get_community_id(callback.message)
            await self.handlers._show_users_list(callback.message, state, community_id)

        # ============================================
        # МОДЕРАЦИЯ
        # ============================================

        @self.dp.callback_query_handler(lambda c: c.data == 'moderation_add', state="*")
        async def moderation_add_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            await callback.message.edit_text("Введите ID пользователя:")
            await state.set_state(AdminStates.MODERATION_USER)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('moderation_action_'), state=AdminStates.MODERATION_ACTION)
        async def moderation_action_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            action = callback.data.split('_')[2]
            await state.update_data(moderation_action=action)
            await callback.message.edit_text("Введите причину наказания:")
            await state.set_state(AdminStates.MODERATION_REASON)

        @self.dp.callback_query_handler(lambda c: c.data == 'back_to_moderation', state="*")
        async def back_to_moderation_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            community_id = get_community_id(callback.message)
            await self.handlers._show_moderation_menu(callback.message, state, community_id)

        @self.dp.callback_query_handler(lambda c: c.data == 'moderation_list', state="*")
        async def moderation_list_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            community_id = get_community_id(callback.message)
            chat_id = self.admin.get_chat_id_by_community(community_id)
            
            if not chat_id:
                await callback.message.edit_text("Чат не найден")
                return
            
            text = self.admin.get_punishments_list_text(chat_id)
            buttons = [
                {"text": "🔙 Назад", "callback_data": "back_to_moderation"}
            ]
            keyboard = KeyboardBuilder.build_inline(buttons)
            await callback.message.edit_text(text, reply_markup=keyboard)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('punishment_revoke_'), state="*")
        async def punishment_revoke_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            punishment_id = int(callback.data.split('_')[2])
            self.admin.moderation.revoke_punishment(punishment_id, callback.from_user.id, "Отменено администратором")
            
            await callback.message.edit_text("✅ Наказание отменено")
            await self.moderation_list_callback(callback, state)

        # ============================================
        # РОЛИ
        # ============================================

        @self.dp.callback_query_handler(lambda c: c.data == 'role_create', state="*")
        async def role_create_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            await callback.message.edit_text("Введите название роли:")
            await state.set_state(AdminStates.ROLE_CREATE_NAME)

        @self.dp.callback_query_handler(lambda c: c.data == 'back_to_roles', state="*")
        async def back_to_roles_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            community_id = get_community_id(callback.message)
            await self.handlers._show_roles_list(callback.message, state, community_id)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('role_edit_'), state="*")
        async def role_edit_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            role_id = callback.data.split('_')[2]
            await state.update_data(edit_role_id=role_id)
            
            role = self.admin.moderation.get_role(role_id)
            if not role:
                await callback.message.edit_text("Роль не найдена")
                return
            
            text = f"✏️ Редактирование роли:\n\n"
            text += f"Название: {role.get('name')}\n"
            text += f"Описание: {role.get('description') or 'Нет'}\n"
            text += f"По умолчанию: {'⭐ Да' if role.get('is_default', 0) else 'Нет'}\n"
            
            buttons = [
                {"text": "📌 Название", "callback_data": f"role_edit_name_{role_id}"},
                {"text": "📝 Описание", "callback_data": f"role_edit_desc_{role_id}"},
                {"text": "⭐ По умолчанию", "callback_data": f"role_default_{role_id}"},
                {"text": "🔑 Права", "callback_data": f"role_permissions_{role_id}"},
                {"text": "🗑 Удалить", "callback_data": f"role_delete_{role_id}"},
                {"text": "🔙 Назад", "callback_data": "back_to_roles"}
            ]
            keyboard = KeyboardBuilder.build_inline(buttons, row_width=2)
            await callback.message.edit_text(text, reply_markup=keyboard)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('role_delete_'), state="*")
        async def role_delete_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            role_id = callback.data.split('_')[2]
            await state.update_data(delete_role_id=role_id)
            
            buttons = [
                {"text": "✅ Да, удалить", "callback_data": f"role_delete_confirm_{role_id}"},
                {"text": "❌ Отмена", "callback_data": f"role_edit_{role_id}"}
            ]
            keyboard = KeyboardBuilder.build_inline(buttons)
            await callback.message.edit_text("⚠️ Вы уверены, что хотите удалить эту роль?", reply_markup=keyboard)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('role_delete_confirm_'), state="*")
        async def role_delete_confirm_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            role_id = callback.data.split('_')[3]
            self.admin.moderation.delete_role(role_id)
            
            community_id = get_community_id(callback.message)
            await callback.message.edit_text("✅ Роль удалена")
            await self.handlers._show_roles_list(callback.message, state, community_id)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('role_default_'), state="*")
        async def role_default_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            role_id = callback.data.split('_')[2]
            
            # Снимаем is_default со всех ролей
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE roles SET is_default = 0')
                cursor.execute('UPDATE roles SET is_default = 1 WHERE id = ?', (role_id,))
                conn.commit()
            
            await callback.message.edit_text("✅ Роль установлена как роль по умолчанию")
            await self.role_edit_callback(callback, state)

        # ============================================
        # ПРАВА
        # ============================================

        @self.dp.callback_query_handler(lambda c: c.data == 'permission_list', state="*")
        async def permission_list_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            text = self.admin.get_permissions_list_text()
            buttons = [
                {"text": "➕ Создать", "callback_data": "permission_create"},
                {"text": "🔙 Назад", "callback_data": "back_to_roles"}
            ]
            keyboard = KeyboardBuilder.build_inline(buttons)
            await callback.message.edit_text(text, reply_markup=keyboard)

        @self.dp.callback_query_handler(lambda c: c.data == 'permission_create', state="*")
        async def permission_create_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            await callback.message.edit_text("Введите название права:")
            await state.set_state(AdminStates.PERMISSION_CREATE_NAME)

        # ============================================
        # СТАТИСТИКА
        # ============================================

        @self.dp.callback_query_handler(lambda c: c.data == 'stats_content', state="*")
        async def stats_content_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            community_id = get_community_id(callback.message)
            chat_id = self.admin.get_chat_id_by_community(community_id)
            
            if not chat_id:
                await callback.message.edit_text("Чат не найден")
                return
            
            text = self.admin.get_stats_content(chat_id)
            buttons = [{"text": "🔙 Назад", "callback_data": "back_to_stats"}]
            keyboard = KeyboardBuilder.build_inline(buttons)
            await callback.message.edit_text(text, reply_markup=keyboard)

        @self.dp.callback_query_handler(lambda c: c.data == 'stats_users', state="*")
        async def stats_users_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            community_id = get_community_id(callback.message)
            chat_id = self.admin.get_chat_id_by_community(community_id)
            
            if not chat_id:
                await callback.message.edit_text("Чат не найден")
                return
            
            text = self.admin.get_stats_users(chat_id)
            buttons = [{"text": "🔙 Назад", "callback_data": "back_to_stats"}]
            keyboard = KeyboardBuilder.build_inline(buttons)
            await callback.message.edit_text(text, reply_markup=keyboard)

        @self.dp.callback_query_handler(lambda c: c.data == 'back_to_stats', state="*")
        async def back_to_stats_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            community_id = get_community_id(callback.message)
            await self.handlers._show_stats(callback.message, state, community_id)

        # ============================================
        # ЛОГИ
        # ============================================

        @self.dp.callback_query_handler(lambda c: c.data.startswith('logs_page_'), state="*")
        async def logs_page_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            page = int(callback.data.split('_')[2])
            community_id = get_community_id(callback.message)
            await self.handlers._show_logs(callback.message, state, community_id, page)

        @self.dp.callback_query_handler(lambda c: c.data == 'logs_search', state="*")
        async def logs_search_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            await callback.message.edit_text("Введите текст для поиска в логах:")
            await state.set_state(AdminStates.LOGS_SEARCH)

        @self.dp.callback_query_handler(lambda c: c.data == 'back_to_logs', state="*")
        async def back_to_logs_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            if not is_admin(callback.from_user.id):
                return
            
            community_id = get_community_id(callback.message)
            await self.handlers._show_logs(callback.message, state, community_id)
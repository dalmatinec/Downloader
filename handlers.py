# handlers.py - ЧАСТЬ 1 (Импорты, команды, проверка прав)
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command, Text
import logging
import uuid

from config import ADMIN_IDS
from database import Database
from admin import AdminPanel, AdminStates
from keyboards import KeyboardBuilder


logger = logging.getLogger(__name__)


class Handlers:
    """Обработчики команд и сообщений"""

    def __init__(self, dp, db: Database):
        self.dp = dp
        self.db = db
        self.admin = AdminPanel(db)

    def _is_admin(self, chat_id: str, user_id: int) -> bool:
        """Единая проверка прав администратора"""
        if user_id not in ADMIN_IDS:
            return False
        return self.admin.is_admin(chat_id, user_id)

    def register(self):
        """Регистрация всех обработчиков"""

        # ============================================
        # КОМАНДА /start
        # ============================================

        @self.dp.message_handler(Command('start'))
        async def cmd_start(message: types.Message):
            user_id = message.from_user.id
            
            if user_id in ADMIN_IDS:
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                keyboard.add(types.KeyboardButton("🔑 Открыть панель"))
                await message.answer("Панель администратора", reply_markup=keyboard)
            else:
                return

        # ============================================
        # КОМАНДА /admin
        # ============================================

        @self.dp.message_handler(Command('admin'))
        async def cmd_admin(message: types.Message, state: FSMContext):
            user_id = message.from_user.id
            telegram_chat_id = str(message.chat.id)
            
            if not self._is_admin(telegram_chat_id, user_id):
                return
            
            # Получаем или создаем community_id
            community_id = self.admin.get_or_create_community(telegram_chat_id, message.chat.title)
            
            await state.set_state(AdminStates.MAIN)
            await self._show_admin_main_menu(message, community_id, user_id)

        # ============================================
        # КНОПКА "ОТКРЫТЬ ПАНЕЛЬ"
        # ============================================

        @self.dp.message_handler(Text(equals="🔑 Открыть панель"))
        async def open_admin_panel(message: types.Message, state: FSMContext):
            user_id = message.from_user.id
            telegram_chat_id = str(message.chat.id)
            
            if not self._is_admin(telegram_chat_id, user_id):
                return
            
            community_id = self.admin.get_or_create_community(telegram_chat_id, message.chat.title)
            
            await state.set_state(AdminStates.MAIN)
            await self._show_admin_main_menu(message, community_id, user_id)

        # ============================================
        # ГЛАВНОЕ МЕНЮ АДМИНА
        # ============================================

        @self.dp.message_handler(state=AdminStates.MAIN)
        async def admin_main_menu_handler(message: types.Message, state: FSMContext):
            user_id = message.from_user.id
            telegram_chat_id = str(message.chat.id)
            text = message.text
            
            if not self._is_admin(telegram_chat_id, user_id):
                return
            
            community_id = self.admin.get_or_create_community(telegram_chat_id, message.chat.title)
            
            # Выход
            if text == "🚪 Выход":
                await state.finish()
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                keyboard.add(types.KeyboardButton("🔑 Открыть панель"))
                await message.answer("Панель администратора", reply_markup=keyboard)
                return
            
            # Получаем меню из БД
            main_menu = self.admin.menu.get_main_menu(community_id)
            if not main_menu:
                return
            
            buttons = self.admin.menu.get_menu_buttons(main_menu['id'])
            
            for btn in buttons:
                if btn['text'] == text:
                    action_data = btn.get('action_data', {})
                    action_type = btn.get('action_type_id')
                    
                    if action_type == 'open_menu':
                        await self._show_submenu(message, state, community_id, user_id, action_data.get('menu_id'))
                    elif action_type == 'open_content':
                        content_id = action_data.get('content_id')
                        await self._show_content(message, state, community_id, content_id)
                    elif action_type == 'open_link':
                        await message.answer(action_data.get('url', '#'))
                    elif action_type == 'command':
                        command = action_data.get('command')
                        if command == 'content':
                            await self._show_content_list(message, state, community_id)
                        elif command == 'menu':
                            await self._show_menu_list(message, state, community_id)
                        elif command == 'users':
                            await self._show_users_list(message, state, community_id)
                        elif command == 'moderation':
                            await self._show_moderation_menu(message, state, community_id)
                        elif command == 'roles':
                            await self._show_roles_list(message, state, community_id)
                        elif command == 'stats':
                            await self._show_stats(message, state, community_id)
                        elif command == 'logs':
                            await self._show_logs(message, state, community_id)
                        elif command == 'settings':
                            await self._show_settings_menu(message, state, community_id)
                        elif command == 'info':
                            await self._show_community_info(message, state, community_id)
                    elif action_type == 'back':
                        await self._show_admin_main_menu(message, community_id, user_id)
                    return

# handlers.py - ЧАСТЬ 2 (Вспомогательные методы и списки)

    # ============================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ============================================

    async def _show_admin_main_menu(self, message: types.Message, community_id: str, user_id: int):
        """Показать главное меню админа из БД"""
        main_menu = self.admin.menu.get_main_menu(community_id)
        if not main_menu:
            return
        
        buttons = self.admin.menu.get_menu_buttons(main_menu['id'])
        if not buttons:
            return
        
        keyboard = KeyboardBuilder.build_reply(buttons)
        await message.answer("Панель администратора", reply_markup=keyboard)

    async def _show_submenu(self, message: types.Message, state: FSMContext, community_id: str, user_id: int, menu_id: str):
        """Показать подменю"""
        buttons = self.admin.menu.get_menu_buttons(menu_id)
        if not buttons:
            await message.answer("Меню пустое")
            return
        
        keyboard = KeyboardBuilder.build_reply(buttons)
        await message.answer("", reply_markup=keyboard)

    # ============================================
    # ПОКАЗ РАЗДЕЛОВ АДМИНКИ
    # ============================================

    async def _show_content_list(self, message: types.Message, state: FSMContext, community_id: str, page: int = 0):
        """Показать список контента"""
        contents, total = self.admin.content.get_paginated(community_id, active_only=False, limit=10, offset=page*10)
        
        if not contents and page == 0:
            await message.answer("Контент отсутствует")
            return
        
        text = "📁 Контент:\n\n"
        for i, content in enumerate(contents, start=1):
            status = "✅" if content.get('is_active', 1) else "❌"
            type_name = content.get('type_name', 'Неизвестно')
            text += f"{i}. {status} {content.get('title')} [{type_name}]\n"
        
        buttons = []
        if page > 0:
            buttons.append({"text": "⬅️", "callback_data": f"content_page_{page-1}"})
        
        total_pages = (total // 10) + (1 if total % 10 else 0)
        if page < total_pages - 1:
            buttons.append({"text": "➡️", "callback_data": f"content_page_{page+1}"})
        
        buttons.append({"text": "➕ Добавить", "callback_data": "content_create"})
        buttons.append({"text": "🔙 Назад", "callback_data": "back_to_main"})
        
        keyboard = KeyboardBuilder.build_inline(buttons, row_width=2)
        await state.set_state(AdminStates.CONTENT_LIST)
        await message.answer(text, reply_markup=keyboard)

    async def _show_menu_list(self, message: types.Message, state: FSMContext, community_id: str):
        """Показать список меню"""
        menus = self.admin.menu.get_menus(community_id, active_only=False)
        
        if not menus:
            await message.answer("Меню отсутствуют")
            return
        
        text = "📋 Меню:\n\n"
        for menu in menus:
            status = "✅" if menu.get('is_active', 1) else "❌"
            main = "⭐" if menu.get('is_main', 0) else "  "
            buttons_count = len(self.admin.menu.get_all_menu_buttons(menu['id'], active_only=False))
            text += f"{main} {status} {menu.get('name')} (кнопок: {buttons_count})\n"
        
        buttons = [
            {"text": "➕ Создать", "callback_data": "menu_create"},
            {"text": "🔙 Назад", "callback_data": "back_to_main"}
        ]
        keyboard = KeyboardBuilder.build_inline(buttons)
        await state.set_state(AdminStates.MENU_LIST)
        await message.answer(text, reply_markup=keyboard)

    async def _show_users_list(self, message: types.Message, state: FSMContext, community_id: str, page: int = 0):
        """Показать список пользователей"""
        chat_id = self.admin.get_chat_id_by_community(community_id)
        if not chat_id:
            await message.answer("Чат не найден")
            return
        
        members, total = self.admin.users.get_chat_members_paginated(chat_id, active_only=False, limit=10, offset=page*10)
        
        if not members and page == 0:
            await message.answer("Пользователи отсутствуют")
            return
        
        text = "👥 Пользователи:\n\n"
        for member in members:
            username = member.get('username') or 'без username'
            name = member.get('first_name') or 'Без имени'
            status = "✅" if member.get('is_active', 1) else "❌"
            messages = member.get('total_messages', 0)
            text += f"{status} {name} (@{username}) - {messages} сообщений\n"
        
        buttons = []
        if page > 0:
            buttons.append({"text": "⬅️", "callback_data": f"users_page_{page-1}"})
        
        total_pages = (total // 10) + (1 if total % 10 else 0)
        if page < total_pages - 1:
            buttons.append({"text": "➡️", "callback_data": f"users_page_{page+1}"})
        
        buttons.append({"text": "🔍 Поиск", "callback_data": "users_search"})
        buttons.append({"text": "🔙 Назад", "callback_data": "back_to_main"})
        
        keyboard = KeyboardBuilder.build_inline(buttons, row_width=2)
        await state.set_state(AdminStates.USERS_LIST)
        await message.answer(text, reply_markup=keyboard)

    async def _show_moderation_menu(self, message: types.Message, state: FSMContext, community_id: str):
        """Показать меню модерации"""
        buttons = [
            {"text": "📋 Наказания", "callback_data": "moderation_list"},
            {"text": "➕ Выдать", "callback_data": "moderation_add"},
            {"text": "🔙 Назад", "callback_data": "back_to_main"}
        ]
        keyboard = KeyboardBuilder.build_inline(buttons)
        await state.set_state(AdminStates.MODERATION_LIST)
        await message.answer("🔨 Модерация", reply_markup=keyboard)

    async def _show_roles_list(self, message: types.Message, state: FSMContext, community_id: str):
        """Показать список ролей"""
        roles = self.admin.moderation.get_all_roles()
        
        if not roles:
            await message.answer("Роли отсутствуют")
            return
        
        text = "👑 Роли:\n\n"
        for role in roles:
            status = "⭐" if role.get('is_default', 0) else "  "
            perms = len(self.admin.moderation.get_role_permissions(role['id']))
            text += f"{status} {role.get('name')} (прав: {perms})\n"
        
        buttons = [
            {"text": "➕ Создать роль", "callback_data": "role_create"},
            {"text": "🔑 Права", "callback_data": "permission_list"},
            {"text": "🔙 Назад", "callback_data": "back_to_main"}
        ]
        keyboard = KeyboardBuilder.build_inline(buttons)
        await state.set_state(AdminStates.ROLE_LIST)
        await message.answer(text, reply_markup=keyboard)

    async def _show_stats(self, message: types.Message, state: FSMContext, community_id: str):
        """Показать статистику"""
        chat_id = self.admin.get_chat_id_by_community(community_id)
        if not chat_id:
            await message.answer("Чат не найден")
            return
        
        members_count = self.admin.users.get_chat_members_count(chat_id)
        content_count = len(self.admin.content.get_all(community_id))
        punishments_active = self.admin.moderation.count_active_punishments()
        
        text = f"📊 Статистика:\n\n"
        text += f"👥 Пользователей: {members_count}\n"
        text += f"📁 Контента: {content_count}\n"
        text += f"🔨 Активных наказаний: {punishments_active}\n"
        
        buttons = [
            {"text": "📁 Контент", "callback_data": "stats_content"},
            {"text": "👥 Пользователи", "callback_data": "stats_users"},
            {"text": "🔙 Назад", "callback_data": "back_to_main"}
        ]
        keyboard = KeyboardBuilder.build_inline(buttons)
        await state.set_state(AdminStates.STATS_MAIN)
        await message.answer(text, reply_markup=keyboard)

    async def _show_logs(self, message: types.Message, state: FSMContext, community_id: str, page: int = 0):
        """Показать логи"""
        chat_id = self.admin.get_chat_id_by_community(community_id)
        if not chat_id:
            await message.answer("Чат не найден")
            return
        
        logs, total = self.admin.get_logs_paginated(chat_id, limit=50, offset=page*50)
        
        if not logs:
            await message.answer("Логи отсутствуют")
            return
        
        text = "📝 Логи:\n\n"
        for log in logs:
            level = log.get('level_name', 'info')
            action = log.get('action', '')
            username = log.get('username') or str(log.get('user_id')) or 'система'
            created = log.get('created_at', '')[:16]
            text += f"[{created}] {level.upper()} - {username}: {action}\n"
        
        buttons = []
        if page > 0:
            buttons.append({"text": "⬅️", "callback_data": f"logs_page_{page-1}"})
        
        total_pages = (total // 50) + (1 if total % 50 else 0)
        if page < total_pages - 1:
            buttons.append({"text": "➡️", "callback_data": f"logs_page_{page+1}"})
        
        buttons.append({"text": "🔍 Поиск", "callback_data": "logs_search"})
        buttons.append({"text": "🔙 Назад", "callback_data": "back_to_main"})
        
        keyboard = KeyboardBuilder.build_inline(buttons, row_width=2)
        await state.set_state(AdminStates.LOGS_MAIN)
        await message.answer(text, reply_markup=keyboard)

    async def _show_settings_menu(self, message: types.Message, state: FSMContext, community_id: str):
        """Показать меню настроек"""
        categories = self.admin.settings.get_categories(community_id)
        
        if not categories:
            await message.answer("Настройки отсутствуют")
            return
        
        text = "⚙️ Настройки:\n\n"
        for cat in categories:
            settings = self.admin.settings.get_by_category(community_id, cat)
            text += f"📂 {cat} ({len(settings)})\n"
        
        buttons = []
        for cat in categories:
            buttons.append({"text": f"📂 {cat}", "callback_data": f"settings_category_{cat}"})
        
        buttons.append({"text": "➕ Добавить", "callback_data": "settings_add"})
        buttons.append({"text": "🔙 Назад", "callback_data": "back_to_main"})
        
        keyboard = KeyboardBuilder.build_inline(buttons, row_width=2)
        await state.set_state(AdminStates.SETTINGS_CATEGORY)
        await message.answer(text, reply_markup=keyboard)

    async def _show_community_info(self, message: types.Message, state: FSMContext, community_id: str):
        """Показать информацию о сообществе"""
        text = self.admin.get_community_info(community_id)
        
        buttons = [
            {"text": "✏️ Редактировать", "callback_data": "community_edit"},
            {"text": "🔙 Назад", "callback_data": "back_to_main"}
        ]
        keyboard = KeyboardBuilder.build_inline(buttons)
        await message.answer(text, reply_markup=keyboard)

# handlers.py - ЧАСТЬ 3 (Callback-запросы)
        # ============================================
        # CALLBACK-ЗАПРОСЫ
        # ============================================

        @self.dp.callback_query_handler(lambda c: c.data == 'back_to_main', state="*")
        async def back_to_main_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            telegram_chat_id = str(callback.message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, callback.message.chat.title)
            user_id = callback.from_user.id
            await state.set_state(AdminStates.MAIN)
            await self._show_admin_main_menu(callback.message, community_id, user_id)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('content_page_'), state="*")
        async def content_page_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            page = int(callback.data.split('_')[2])
            telegram_chat_id = str(callback.message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, callback.message.chat.title)
            await self._show_content_list(callback.message, state, community_id, page)

        @self.dp.callback_query_handler(lambda c: c.data == 'content_create', state="*")
        async def content_create_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            content_types = self.admin.content.get_content_types()
            buttons = []
            for ct in content_types:
                buttons.append({"text": ct.get('name'), "callback_data": f"content_type_{ct['id']}"})
            buttons.append({"text": "❌ Отмена", "callback_data": "back_to_content"})
            keyboard = KeyboardBuilder.build_inline(buttons, row_width=2)
            await callback.message.edit_text("Выберите тип контента:", reply_markup=keyboard)
            await state.set_state(AdminStates.CONTENT_CREATE_TYPE)

        @self.dp.callback_query_handler(lambda c: c.data == 'back_to_content', state="*")
        async def back_to_content_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            telegram_chat_id = str(callback.message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, callback.message.chat.title)
            await self._show_content_list(callback.message, state, community_id)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('content_type_'), state=AdminStates.CONTENT_CREATE_TYPE)
        async def content_type_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            type_id = callback.data.split('_')[2]
            await state.update_data(content_type_id=type_id)
            await callback.message.edit_text("Введите название контента:")
            await state.set_state(AdminStates.CONTENT_CREATE_TITLE)

        @self.dp.message_handler(state=AdminStates.CONTENT_CREATE_TITLE)
        async def content_create_title(message: types.Message, state: FSMContext):
            await state.update_data(content_title=message.text.strip())
            await message.answer("Введите описание (или '-' для пропуска):")
            await state.set_state(AdminStates.CONTENT_CREATE_DESCRIPTION)

        @self.dp.message_handler(state=AdminStates.CONTENT_CREATE_DESCRIPTION)
        async def content_create_description(message: types.Message, state: FSMContext):
            desc = message.text.strip()
            if desc == '-':
                desc = ''
            await state.update_data(content_description=desc)
            await message.answer("Отправьте файл или текст:")
            await state.set_state(AdminStates.CONTENT_CREATE_FILE)

        @self.dp.message_handler(state=AdminStates.CONTENT_CREATE_FILE, content_types=['photo', 'document', 'video', 'audio', 'text'])
        async def content_create_file(message: types.Message, state: FSMContext):
            file_id = None
            if message.photo:
                file_id = message.photo[-1].file_id
            elif message.document:
                file_id = message.document.file_id
            elif message.video:
                file_id = message.video.file_id
            elif message.audio:
                file_id = message.audio.file_id
            elif message.text:
                await state.update_data(content_text=message.text.strip())
            if file_id:
                await state.update_data(content_file_id=file_id)
            await message.answer("Введите теги через запятую (или '-'):")
            await state.set_state(AdminStates.CONTENT_CREATE_TAGS)

        @self.dp.message_handler(state=AdminStates.CONTENT_CREATE_TAGS)
        async def content_create_tags(message: types.Message, state: FSMContext):
            tags = []
            if message.text.strip() != '-':
                tags = [t.strip() for t in message.text.split(',') if t.strip()]
            await state.update_data(content_tags=tags)
            
            data = await state.get_data()
            telegram_chat_id = str(message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, message.chat.title)
            
            content_id = self.admin.content.create({
                'community_id': community_id,
                'title': data.get('content_title'),
                'description': data.get('content_description'),
                'content_type_id': data.get('content_type_id'),
                'file_id': data.get('content_file_id'),
                'text_content': data.get('content_text'),
                'tags': data.get('content_tags')
            })
            
            await message.answer("✅ Контент создан")
            await state.set_state(AdminStates.MAIN)
            await self._show_admin_main_menu(message, community_id, message.from_user.id)

        @self.dp.callback_query_handler(lambda c: c.data == 'menu_create', state="*")
        async def menu_create_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            await callback.message.edit_text("Введите название меню:")
            await state.set_state(AdminStates.MENU_CREATE_NAME)

        @self.dp.message_handler(state=AdminStates.MENU_CREATE_NAME)
        async def menu_create_name(message: types.Message, state: FSMContext):
            telegram_chat_id = str(message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, message.chat.title)
            
            menu_id = self.admin.menu.create_menu({
                'community_id': community_id,
                'name': message.text.strip(),
                'is_main': 0
            })
            await message.answer("✅ Меню создано")
            await state.set_state(AdminStates.MAIN)
            await self._show_admin_main_menu(message, community_id, message.from_user.id)

        @self.dp.callback_query_handler(lambda c: c.data == 'role_create', state="*")
        async def role_create_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            await callback.message.edit_text("Введите название роли:")
            await state.set_state(AdminStates.ROLE_CREATE_NAME)

        @self.dp.message_handler(state=AdminStates.ROLE_CREATE_NAME)
        async def role_create_name(message: types.Message, state: FSMContext):
            self.admin.moderation.create_role({
                'name': message.text.strip(),
                'description': '',
                'is_default': 0
            })
            await message.answer("✅ Роль создана")
            await state.set_state(AdminStates.MAIN)
            telegram_chat_id = str(message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, message.chat.title)
            await self._show_admin_main_menu(message, community_id, message.from_user.id)

        @self.dp.callback_query_handler(lambda c: c.data == 'permission_list', state="*")
        async def permission_list_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            permissions = self.admin.moderation.get_all_permissions()
            text = "🔑 Права:\n\n"
            for p in permissions:
                text += f"• {p.get('name')}\n"
            buttons = [
                {"text": "➕ Создать", "callback_data": "permission_create"},
                {"text": "🔙 Назад", "callback_data": "back_to_roles"}
            ]
            keyboard = KeyboardBuilder.build_inline(buttons)
            await callback.message.edit_text(text, reply_markup=keyboard)

        @self.dp.callback_query_handler(lambda c: c.data == 'back_to_roles', state="*")
        async def back_to_roles_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            telegram_chat_id = str(callback.message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, callback.message.chat.title)
            await self._show_roles_list(callback.message, state, community_id)

        @self.dp.callback_query_handler(lambda c: c.data == 'permission_create', state="*")
        async def permission_create_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            await callback.message.edit_text("Введите название права:")
            await state.set_state(AdminStates.PERMISSION_CREATE_NAME)

        @self.dp.message_handler(state=AdminStates.PERMISSION_CREATE_NAME)
        async def permission_create_name(message: types.Message, state: FSMContext):
            self.admin.moderation.create_permission({
                'name': message.text.strip(),
                'description': ''
            })
            await message.answer("✅ Право создано")
            await state.set_state(AdminStates.MAIN)
            telegram_chat_id = str(message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, message.chat.title)
            await self._show_admin_main_menu(message, community_id, message.from_user.id)

        @self.dp.callback_query_handler(lambda c: c.data == 'community_edit', state="*")
        async def community_edit_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            buttons = [
                {"text": "Название", "callback_data": "community_edit_name"},
                {"text": "Описание", "callback_data": "community_edit_description"},
                {"text": "Аватар", "callback_data": "community_edit_avatar"},
                {"text": "Логотип", "callback_data": "community_edit_logo"},
                {"text": "🔙 Назад", "callback_data": "back_to_main"}
            ]
            keyboard = KeyboardBuilder.build_inline(buttons, row_width=2)
            await callback.message.edit_text("✏️ Редактирование сообщества:", reply_markup=keyboard)

        @self.dp.callback_query_handler(lambda c: c.data == 'community_edit_name', state="*")
        async def community_edit_name_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            await callback.message.edit_text("Введите название сообщества:")
            await state.set_state(AdminStates.SETTINGS_EDIT_NAME)

        @self.dp.callback_query_handler(lambda c: c.data == 'community_edit_description', state="*")
        async def community_edit_description_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            await callback.message.edit_text("Введите описание сообщества:")
            await state.set_state(AdminStates.SETTINGS_EDIT_DESCRIPTION)

        @self.dp.callback_query_handler(lambda c: c.data == 'community_edit_avatar', state="*")
        async def community_edit_avatar_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            await callback.message.edit_text("Отправьте фото для аватара:")
            await state.set_state(AdminStates.SETTINGS_EDIT_AVATAR)

        @self.dp.callback_query_handler(lambda c: c.data == 'community_edit_logo', state="*")
        async def community_edit_logo_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            await callback.message.edit_text("Отправьте фото для логотипа:")
            await state.set_state(AdminStates.SETTINGS_EDIT_LOGO)

# handlers.py - ЧАСТЬ 4 (Модерация, настройки, логи)
        @self.dp.message_handler(state=AdminStates.SETTINGS_EDIT_NAME)
        async def settings_edit_name(message: types.Message, state: FSMContext):
            telegram_chat_id = str(message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, message.chat.title)
            self.admin.update_community_name(community_id, message.text.strip())
            await message.answer("✅ Обновлено")
            await state.set_state(AdminStates.MAIN)
            await self._show_admin_main_menu(message, community_id, message.from_user.id)

        @self.dp.message_handler(state=AdminStates.SETTINGS_EDIT_DESCRIPTION)
        async def settings_edit_description(message: types.Message, state: FSMContext):
            telegram_chat_id = str(message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, message.chat.title)
            self.admin.update_community_description(community_id, message.text.strip())
            await message.answer("✅ Обновлено")
            await state.set_state(AdminStates.MAIN)
            await self._show_admin_main_menu(message, community_id, message.from_user.id)

        @self.dp.message_handler(state=AdminStates.SETTINGS_EDIT_AVATAR, content_types=['photo'])
        async def settings_edit_avatar(message: types.Message, state: FSMContext):
            telegram_chat_id = str(message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, message.chat.title)
            photo_id = message.photo[-1].file_id
            self.admin.update_community_avatar(community_id, photo_id)
            await message.answer("✅ Обновлено")
            await state.set_state(AdminStates.MAIN)
            await self._show_admin_main_menu(message, community_id, message.from_user.id)

        @self.dp.message_handler(state=AdminStates.SETTINGS_EDIT_LOGO, content_types=['photo'])
        async def settings_edit_logo(message: types.Message, state: FSMContext):
            telegram_chat_id = str(message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, message.chat.title)
            photo_id = message.photo[-1].file_id
            self.admin.update_community_logo(community_id, photo_id)
            await message.answer("✅ Обновлено")
            await state.set_state(AdminStates.MAIN)
            await self._show_admin_main_menu(message, community_id, message.from_user.id)

        @self.dp.callback_query_handler(lambda c: c.data == 'users_search', state="*")
        async def users_search_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            await callback.message.edit_text("Введите ID, username или имя для поиска:")
            await state.set_state(AdminStates.USERS_SEARCH)

        @self.dp.message_handler(state=AdminStates.USERS_SEARCH)
        async def users_search(message: types.Message, state: FSMContext):
            chat_id = str(message.chat.id)
            users = self.admin.users.search(message.text.strip())
            if not users:
                await message.answer("Не найдено")
                return
            text = "Результаты поиска:\n\n"
            for u in users[:10]:
                name = u.get('first_name') or 'Без имени'
                username = u.get('username') or 'без username'
                text += f"• {name} (@{username}) - ID: {u.get('user_id')}\n"
            await message.answer(text)
            await state.set_state(AdminStates.USERS_LIST)

        @self.dp.callback_query_handler(lambda c: c.data == 'moderation_add', state="*")
        async def moderation_add_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            await callback.message.edit_text("Введите ID пользователя:")
            await state.set_state(AdminStates.MODERATION_USER)

        @self.dp.message_handler(state=AdminStates.MODERATION_USER)
        async def moderation_user(message: types.Message, state: FSMContext):
            try:
                user_id = int(message.text.strip())
                await state.update_data(moderation_user_id=user_id)
                buttons = [
                    {"text": "⛔ Бан", "callback_data": "moderation_action_ban"},
                    {"text": "🔇 Мут", "callback_data": "moderation_action_mute"},
                    {"text": "⚠️ Варн", "callback_data": "moderation_action_warn"},
                    {"text": "❌ Отмена", "callback_data": "back_to_moderation"}
                ]
                keyboard = KeyboardBuilder.build_inline(buttons, row_width=2)
                await message.answer("Выберите действие:", reply_markup=keyboard)
                await state.set_state(AdminStates.MODERATION_ACTION)
            except ValueError:
                await message.answer("Введите корректный ID (число):")

        @self.dp.callback_query_handler(lambda c: c.data.startswith('moderation_action_'), state=AdminStates.MODERATION_ACTION)
        async def moderation_action(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            action = callback.data.split('_')[2]
            await state.update_data(moderation_action=action)
            await callback.message.edit_text("Введите причину наказания:")
            await state.set_state(AdminStates.MODERATION_REASON)

        @self.dp.message_handler(state=AdminStates.MODERATION_REASON)
        async def moderation_reason(message: types.Message, state: FSMContext):
            await state.update_data(moderation_reason=message.text.strip())
            await message.answer("Введите длительность в секундах (0 - бессрочно):")
            await state.set_state(AdminStates.MODERATION_DURATION)

        @self.dp.message_handler(state=AdminStates.MODERATION_DURATION)
        async def moderation_duration(message: types.Message, state: FSMContext):
            try:
                duration = int(message.text.strip())
                data = await state.get_data()
                user_id = data.get('moderation_user_id')
                action = data.get('moderation_action')
                reason = data.get('moderation_reason')
                telegram_chat_id = str(message.chat.id)
                community_id = self.admin.get_or_create_community(telegram_chat_id, message.chat.title)
                chat_id = self.admin.get_chat_id_by_community(community_id)
                
                if not chat_id:
                    await message.answer("Чат не найден")
                    return
                
                member = self.admin.users.get_chat_member(chat_id, user_id)
                if not member or 'id' not in member:
                    await message.answer("Пользователь не найден в этом чате")
                    return
                
                type_map = {'ban': 'ban', 'mute': 'mute', 'warn': 'warn'}
                type_name = type_map.get(action, 'warn')
                
                punishment_types = self.admin.moderation.get_all_punishment_types()
                punishment_type = None
                for pt in punishment_types:
                    if pt['name'].lower() == type_name:
                        punishment_type = pt
                        break
                
                if not punishment_type:
                    type_id = str(uuid.uuid4())
                    self.admin.moderation.create_punishment_type({
                        'id': type_id,
                        'name': type_name,
                        'description': f'{type_name} punishment'
                    })
                    punishment_type = {'id': type_id}
                
                self.admin.moderation.create_punishment({
                    'chat_member_id': member['id'],
                    'punishment_type_id': punishment_type['id'],
                    'reason': reason,
                    'duration': duration if duration > 0 else None,
                    'issued_by': message.from_user.id
                })
                
                await message.answer("✅ Наказание выдано")
                await state.set_state(AdminStates.MAIN)
                await self._show_admin_main_menu(message, community_id, message.from_user.id)
            except ValueError:
                await message.answer("Введите корректное число:")

        @self.dp.callback_query_handler(lambda c: c.data == 'back_to_moderation', state="*")
        async def back_to_moderation_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            telegram_chat_id = str(callback.message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, callback.message.chat.title)
            await self._show_moderation_menu(callback.message, state, community_id)

        @self.dp.callback_query_handler(lambda c: c.data == 'moderation_list', state="*")
        async def moderation_list_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            punishments = self.admin.moderation.get_all_punishments(active_only=False, limit=50)
            if not punishments:
                await callback.message.edit_text("Наказаний нет")
                return
            text = "🔨 Наказания:\n\n"
            for p in punishments:
                is_active = p.get('is_active', 1)
                status = "✅" if is_active else "❌"
                type_name = p.get('type_name', 'Неизвестно')
                text += f"{status} {type_name}: {p.get('reason', 'Без причины')}\n"
            buttons = [{"text": "🔙 Назад", "callback_data": "back_to_moderation"}]
            keyboard = KeyboardBuilder.build_inline(buttons)
            await callback.message.edit_text(text, reply_markup=keyboard)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('settings_category_'), state="*")
        async def settings_category_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            telegram_chat_id = str(callback.message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, callback.message.chat.title)
            category = callback.data.split('_')[2]
            settings = self.admin.settings.get_by_category(community_id, category)
            text = f"⚙️ {category}:\n\n"
            for s in settings:
                text += f"{s.get('key')} = {s.get('value')}\n"
            buttons = [{"text": "🔙 Назад", "callback_data": "back_to_settings"}]
            keyboard = KeyboardBuilder.build_inline(buttons)
            await callback.message.edit_text(text, reply_markup=keyboard)

        @self.dp.callback_query_handler(lambda c: c.data == 'back_to_settings', state="*")
        async def back_to_settings_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            telegram_chat_id = str(callback.message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, callback.message.chat.title)
            await self._show_settings_menu(callback.message, state, community_id)

        @self.dp.callback_query_handler(lambda c: c.data == 'settings_add', state="*")
        async def settings_add_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            await callback.message.edit_text("Введите категорию:")
            await state.set_state(AdminStates.SETTINGS_CREATE_CATEGORY)

        @self.dp.message_handler(state=AdminStates.SETTINGS_CREATE_CATEGORY)
        async def settings_create_category(message: types.Message, state: FSMContext):
            await state.update_data(setting_category=message.text.strip())
            await message.answer("Введите ключ:")
            await state.set_state(AdminStates.SETTINGS_CREATE_KEY)

        @self.dp.message_handler(state=AdminStates.SETTINGS_CREATE_KEY)
        async def settings_create_key(message: types.Message, state: FSMContext):
            await state.update_data(setting_key=message.text.strip())
            await message.answer("Введите значение:")
            await state.set_state(AdminStates.SETTINGS_CREATE_VALUE)

        @self.dp.message_handler(state=AdminStates.SETTINGS_CREATE_VALUE)
        async def settings_create_value(message: types.Message, state: FSMContext):
            await state.update_data(setting_value=message.text.strip())
            await message.answer("Введите тип (string/integer/boolean/json/list/float):")
            await state.set_state(AdminStates.SETTINGS_CREATE_TYPE)

        @self.dp.message_handler(state=AdminStates.SETTINGS_CREATE_TYPE)
        async def settings_create_type(message: types.Message, state: FSMContext):
            value_type = message.text.strip().lower()
            valid_types = ['string', 'integer', 'boolean', 'json', 'list', 'float']
            if value_type not in valid_types:
                await message.answer(f"Доступные типы: {', '.join(valid_types)}")
                return
            
            data = await state.get_data()
            telegram_chat_id = str(message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, message.chat.title)
            
            self.admin.settings.create({
                'community_id': community_id,
                'category': data.get('setting_category'),
                'key': data.get('setting_key'),
                'value': data.get('setting_value'),
                'value_type': value_type
            })
            
            await message.answer("✅ Настройка создана")
            await state.set_state(AdminStates.MAIN)
            await self._show_admin_main_menu(message, community_id, message.from_user.id)

        @self.dp.callback_query_handler(lambda c: c.data == 'stats_content', state="*")
        async def stats_content_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            telegram_chat_id = str(callback.message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, callback.message.chat.title)
            contents = self.admin.content.get_all(community_id, active_only=True, limit=20)
            text = "📁 Статистика контента:\n\n"
            if not contents:
                text += "Контент отсутствует"
            else:
                for content in contents:
                    text += f"• {content.get('title')} - 👁{content.get('views', 0)} ⬇{content.get('downloads', 0)}\n"
            buttons = [{"text": "🔙 Назад", "callback_data": "back_to_stats"}]
            keyboard = KeyboardBuilder.build_inline(buttons)
            await callback.message.edit_text(text, reply_markup=keyboard)

        @self.dp.callback_query_handler(lambda c: c.data == 'stats_users', state="*")
        async def stats_users_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            telegram_chat_id = str(callback.message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, callback.message.chat.title)
            chat_id = self.admin.get_chat_id_by_community(community_id)
            if not chat_id:
                await callback.message.edit_text("Чат не найден")
                return
            members = self.admin.users.get_chat_members(chat_id, active_only=True, limit=10)
            text = "👥 Статистика пользователей:\n\n"
            if not members:
                text += "Пользователи отсутствуют"
            else:
                text += "Топ по сообщениям:\n"
                for i, member in enumerate(members[:10], 1):
                    name = member.get('username') or member.get('first_name') or 'Неизвестно'
                    text += f"{i}. {name} - {member.get('total_messages', 0)} сообщений\n"
            buttons = [{"text": "🔙 Назад", "callback_data": "back_to_stats"}]
            keyboard = KeyboardBuilder.build_inline(buttons)
            await callback.message.edit_text(text, reply_markup=keyboard)

        @self.dp.callback_query_handler(lambda c: c.data == 'back_to_stats', state="*")
        async def back_to_stats_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            telegram_chat_id = str(callback.message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, callback.message.chat.title)
            await self._show_stats(callback.message, state, community_id)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('logs_page_'), state="*")
        async def logs_page_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            page = int(callback.data.split('_')[2])
            telegram_chat_id = str(callback.message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, callback.message.chat.title)
            await self._show_logs(callback.message, state, community_id, page)

        @self.dp.callback_query_handler(lambda c: c.data == 'logs_search', state="*")
        async def logs_search_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            await callback.message.edit_text("Введите текст для поиска в логах:")
            await state.set_state(AdminStates.LOGS_SEARCH)

        @self.dp.message_handler(state=AdminStates.LOGS_SEARCH)
        async def logs_search_handler(message: types.Message, state: FSMContext):
            telegram_chat_id = str(message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, message.chat.title)
            chat_id = self.admin.get_chat_id_by_community(community_id)
            if not chat_id:
                await message.answer("Чат не найден")
                return
            query = message.text.strip()
            logs, total = self.admin.get_logs_paginated(chat_id, search=query, limit=50)
            if not logs:
                await message.answer("Ничего не найдено")
                return
            text = "📝 Результаты поиска:\n\n"
            for log in logs:
                level = log.get('level_name', 'info')
                action = log.get('action', '')
                username = log.get('username') or str(log.get('user_id')) or 'система'
                created = log.get('created_at', '')[:16]
                text += f"[{created}] {level.upper()} - {username}: {action}\n"
            buttons = [{"text": "🔙 Назад", "callback_data": "back_to_logs"}]
            keyboard = KeyboardBuilder.build_inline(buttons)
            await message.answer(text, reply_markup=keyboard)
            await state.set_state(AdminStates.LOGS_MAIN)

        @self.dp.callback_query_handler(lambda c: c.data == 'back_to_logs', state="*")
        async def back_to_logs_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            telegram_chat_id = str(callback.message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, callback.message.chat.title)
            await self._show_logs(callback.message, state, community_id)

        @self.dp.callback_query_handler(lambda c: c.data.startswith('users_page_'), state="*")
        async def users_page_callback(callback: types.CallbackQuery, state: FSMContext):
            await callback.answer()
            page = int(callback.data.split('_')[2])
            telegram_chat_id = str(callback.message.chat.id)
            community_id = self.admin.get_or_create_community(telegram_chat_id, callback.message.chat.title)
            await self._show_users_list(callback.message, state, community_id, page)
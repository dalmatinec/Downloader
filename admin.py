# admin.py - ЧАСТЬ 1 (Импорты, состояния, инициализация, проверки прав)
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from typing import Optional, Dict, Any, List
import logging
import sqlite3
import uuid
from datetime import datetime

from config import ADMIN_IDS
from keyboards import KeyboardBuilder
from contents import ContentManager
from menus import MenuManager
from settings import SettingsManager
from users import UserManager
from moderation import ModerationManager
from database import Database


class AdminStates(StatesGroup):
    """Состояния админ-панели"""
    MAIN = State()
    
    # Настройки сообщества
    SETTINGS_EDIT_NAME = State()
    SETTINGS_EDIT_DESCRIPTION = State()
    SETTINGS_EDIT_AVATAR = State()
    SETTINGS_EDIT_LOGO = State()
    
    # Контент
    CONTENT_LIST = State()
    CONTENT_CREATE_TITLE = State()
    CONTENT_CREATE_DESCRIPTION = State()
    CONTENT_CREATE_TYPE = State()
    CONTENT_CREATE_FILE = State()
    CONTENT_CREATE_URL = State()
    CONTENT_CREATE_TEXT = State()
    CONTENT_CREATE_TAGS = State()
    CONTENT_EDIT = State()
    CONTENT_EDIT_TITLE = State()
    CONTENT_EDIT_DESCRIPTION = State()
    CONTENT_EDIT_FILE = State()
    CONTENT_EDIT_URL = State()
    CONTENT_EDIT_TEXT = State()
    CONTENT_EDIT_TAGS = State()
    CONTENT_CONFIRM_DELETE = State()
    
    # Меню
    MENU_LIST = State()
    MENU_CREATE_NAME = State()
    MENU_CREATE_IS_MAIN = State()
    MENU_EDIT = State()
    MENU_EDIT_NAME = State()
    MENU_CONFIRM_DELETE = State()
    
    # Кнопки
    BUTTON_LIST = State()
    BUTTON_CREATE_TEXT = State()
    BUTTON_CREATE_ACTION_TYPE = State()
    BUTTON_CREATE_ACTION_DATA = State()
    BUTTON_CREATE_ROW = State()
    BUTTON_CREATE_ORDER = State()
    BUTTON_EDIT = State()
    BUTTON_EDIT_TEXT = State()
    BUTTON_EDIT_ACTION_TYPE = State()
    BUTTON_EDIT_ACTION_DATA = State()
    BUTTON_EDIT_ROW = State()
    BUTTON_EDIT_ORDER = State()
    BUTTON_CONFIRM_DELETE = State()
    
    # Пользователи
    USERS_LIST = State()
    USERS_SEARCH = State()
    USER_VIEW = State()
    USER_EDIT_ROLES = State()
    USER_CONFIRM_DELETE = State()
    
    # Модерация
    MODERATION_USER = State()
    MODERATION_ACTION = State()
    MODERATION_REASON = State()
    MODERATION_DURATION = State()
    MODERATION_CONFIRM = State()
    MODERATION_LIST = State()
    
    # Наказания
    PUNISHMENT_LIST = State()
    PUNISHMENT_VIEW = State()
    PUNISHMENT_REVOKE_CONFIRM = State()
    
    # Роли
    ROLE_LIST = State()
    ROLE_CREATE_NAME = State()
    ROLE_CREATE_DESCRIPTION = State()
    ROLE_CREATE_IS_DEFAULT = State()
    ROLE_EDIT = State()
    ROLE_EDIT_NAME = State()
    ROLE_EDIT_DESCRIPTION = State()
    ROLE_EDIT_IS_DEFAULT = State()
    ROLE_EDIT_PERMISSIONS = State()
    ROLE_CONFIRM_DELETE = State()
    
    # Права
    PERMISSION_LIST = State()
    PERMISSION_CREATE_NAME = State()
    PERMISSION_CREATE_DESCRIPTION = State()
    PERMISSION_EDIT = State()
    PERMISSION_EDIT_NAME = State()
    PERMISSION_EDIT_DESCRIPTION = State()
    PERMISSION_CONFIRM_DELETE = State()
    
    # Статистика
    STATS_MAIN = State()
    STATS_CONTENT = State()
    STATS_USERS = State()
    
    # Логи
    LOGS_MAIN = State()
    LOGS_SEARCH = State()
    
    # Настройки
    SETTINGS_CATEGORY = State()
    SETTINGS_CREATE_CATEGORY = State()
    SETTINGS_CREATE_KEY = State()
    SETTINGS_CREATE_VALUE = State()
    SETTINGS_CREATE_TYPE = State()
    SETTINGS_EDIT_KEY = State()
    SETTINGS_EDIT_VALUE = State()
    SETTINGS_EDIT_TYPE = State()
    SETTINGS_EDIT_DESCRIPTION = State()
    SETTINGS_CONFIRM_DELETE = State()
    
    # Общие
    BACK = State()
    CONFIRM = State()


class AdminPanel:
    """Админ-панель"""

    def __init__(self, db: Database):
        self.db = db
        self.content = ContentManager(db)
        self.menu = MenuManager(db)
        self.settings = SettingsManager(db)
        self.users = UserManager(db)
        self.moderation = ModerationManager(db)
        self.logger = logging.getLogger(__name__)

    # ============================================
    # РАБОТА С COMMUNITY И CHAT
    # ============================================

    def get_or_create_community(self, telegram_chat_id: str, chat_title: str = None) -> str:
        """Получить или создать community_id по telegram_chat_id"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM chats WHERE chat_id = ?', (telegram_chat_id,))
            chat = cursor.fetchone()
            
            if chat:
                return chat['community_id']
            
            community_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO communities (id, name, description, is_active)
                VALUES (?, ?, ?, ?)
            ''', (community_id, chat_title or f'Community {telegram_chat_id}', '', 1))
            
            chat_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO chats (id, community_id, chat_id, chat_type, title, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (chat_id, community_id, telegram_chat_id, 'private', chat_title or '', 1))
            
            conn.commit()
            return community_id

    def get_chat_id_by_community(self, community_id: str) -> Optional[str]:
        """Получить chat_id (telegram) по community_id"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT chat_id FROM chats WHERE community_id = ? LIMIT 1', (community_id,))
            row = cursor.fetchone()
            return row['chat_id'] if row else None

    def update_community_name(self, community_id: str, name: str) -> bool:
        """Обновить название сообщества"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE communities SET name = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (name, community_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_community_description(self, community_id: str, description: str) -> bool:
        """Обновить описание сообщества"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE communities SET description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (description, community_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_community_avatar(self, community_id: str, file_id: str) -> bool:
        """Обновить аватар сообщества"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE communities SET avatar_file_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (file_id, community_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_community_logo(self, community_id: str, file_id: str) -> bool:
        """Обновить логотип сообщества"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE communities SET logo_file_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (file_id, community_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_community_info(self, community_id: str) -> str:
        """Получить информацию о сообществе"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM communities WHERE id = ?', (community_id,))
            row = cursor.fetchone()
            
            if not row:
                return "🏠 Сообщество не найдено"
            
            community = dict(row)
            text = "🏠 Информация о сообществе:\n\n"
            text += f"📌 Название: {community.get('name', 'Не задано')}\n"
            text += f"📝 Описание: {community.get('description', 'Не задано')}\n"
            text += f"🆔 ID: {community.get('id')}\n"
            text += f"📅 Создано: {community.get('created_at', '')[:16]}\n"
            text += f"📅 Обновлено: {community.get('updated_at', '')[:16]}\n"
            text += f"📊 Статус: {'✅ Активно' if community.get('is_active', 1) else '❌ Неактивно'}\n"
            
            menus = self.menu.get_menus(community_id)
            text += f"📋 Меню: {len(menus)}\n"
            
            content = self.content.get_all(community_id)
            text += f"📁 Контент: {len(content)}\n"
            
            chat_id = self.get_chat_id_by_community(community_id)
            if chat_id:
                members_count = self.users.get_chat_members_count(chat_id)
                text += f"👥 Пользователей: {members_count}\n"
            
            return text

    # ============================================
    # ПРОВЕРКИ ПРАВ
    # ============================================

    def is_owner(self, user_id: int) -> bool:
        """Проверка владельца из конфига"""
        return user_id in ADMIN_IDS

    def is_admin(self, community_id: str, user_id: int) -> bool:
        """
        Проверка прав администратора
        1. Сначала проверяем владельца из конфига
        2. Затем проверяем права через роли
        """
        if self.is_owner(user_id):
            return True
        
        return self.moderation.has_user_permission(community_id, user_id, 'admin_panel_access')

    def can_manage_content(self, community_id: str, user_id: int) -> bool:
        """Проверка права управления контентом"""
        if self.is_owner(user_id):
            return True
        return self.moderation.has_user_permission(community_id, user_id, 'manage_content')

    def can_manage_users(self, community_id: str, user_id: int) -> bool:
        """Проверка права управления пользователями"""
        if self.is_owner(user_id):
            return True
        return self.moderation.has_user_permission(community_id, user_id, 'manage_users')

    def can_manage_roles(self, community_id: str, user_id: int) -> bool:
        """Проверка права управления ролями"""
        if self.is_owner(user_id):
            return True
        return self.moderation.has_user_permission(community_id, user_id, 'manage_roles')

    def can_manage_settings(self, community_id: str, user_id: int) -> bool:
        """Проверка права управления настройками"""
        if self.is_owner(user_id):
            return True
        return self.moderation.has_user_permission(community_id, user_id, 'manage_settings')

    def can_moderate(self, community_id: str, user_id: int) -> bool:
        """Проверка права модерации"""
        if self.is_owner(user_id):
            return True
        return self.moderation.has_user_permission(community_id, user_id, 'moderate_users')

    def can_view_stats(self, community_id: str, user_id: int) -> bool:
        """Проверка права просмотра статистики"""
        if self.is_owner(user_id):
            return True
        return self.moderation.has_user_permission(community_id, user_id, 'view_stats')

    def can_view_logs(self, community_id: str, user_id: int) -> bool:
        """Проверка права просмотра логов"""
        if self.is_owner(user_id):
            return True
        return self.moderation.has_user_permission(community_id, user_id, 'view_logs')

# admin.py - ЧАСТЬ 2 (Работа с контентом, меню, пользователями, наказаниями)
    # ============================================
    # КОНТЕНТ
    # ============================================

    def get_content_list_text(self, community_id: str, page: int = 0, per_page: int = 10) -> str:
        """Текст списка контента"""
        contents, total = self.content.get_paginated(community_id, active_only=False, limit=per_page, offset=page*per_page)
        
        if not contents:
            return "📁 Контент отсутствует.\n\nНажмите '➕ Добавить', чтобы создать первый контент."
        
        text = "📁 Список контента:\n\n"
        for i, content in enumerate(contents, start=1):
            status = "✅" if content.get('is_active', 1) else "❌"
            type_name = content.get('type_name', 'Неизвестно')
            views = content.get('views', 0)
            downloads = content.get('downloads', 0)
            text += f"{i}. {status} {content.get('title')} [{type_name}] 👁{views} ⬇{downloads}\n"
        
        total_pages = (total // per_page) + (1 if total % per_page else 0)
        text += f"\nСтраница {page + 1} из {total_pages} | Всего: {total}"
        return text

    # ============================================
    # МЕНЮ
    # ============================================

    def get_menu_list_text(self, community_id: str) -> str:
        """Текст списка меню"""
        menus = self.menu.get_menus(community_id, active_only=False)
        if not menus:
            return "📋 Меню отсутствуют.\n\nНажмите '➕ Создать', чтобы создать первое меню."
        
        text = "📋 Список меню:\n\n"
        for menu in menus:
            status = "✅" if menu.get('is_active', 1) else "❌"
            main = "⭐" if menu.get('is_main', 0) else "  "
            buttons_count = len(self.menu.get_all_menu_buttons(menu['id'], active_only=False))
            text += f"{main} {status} {menu.get('name')} (кнопок: {buttons_count})\n"
        
        return text

    # ============================================
    # ПОЛЬЗОВАТЕЛИ
    # ============================================

    def get_users_list_text(self, chat_id: str, page: int = 0, per_page: int = 10) -> str:
        """Текст списка пользователей"""
        members, total = self.users.get_chat_members_paginated(chat_id, active_only=False, limit=per_page, offset=page*per_page)
        
        if not members:
            return "👥 Пользователи отсутствуют."
        
        text = "👥 Список пользователей:\n\n"
        for member in members:
            username = member.get('username') or 'без username'
            name = member.get('first_name') or 'Без имени'
            status = "✅" if member.get('is_active', 1) else "❌"
            messages = member.get('total_messages', 0)
            
            punishments = self.moderation.get_user_active_punishments(chat_id, member['user_id'])
            pun_text = ""
            if punishments:
                pun_types = [p.get('type_name', '') for p in punishments]
                pun_text = f" ⚠️{','.join(pun_types)}"
            
            text += f"{status} {name} (@{username}) - {messages} сообщений{pun_text}\n"
        
        total_pages = (total // per_page) + (1 if total % per_page else 0)
        text += f"\nСтраница {page + 1} из {total_pages} | Всего: {total}"
        return text

    # ============================================
    # НАКАЗАНИЯ
    # ============================================

    def get_punishments_list_text(self, chat_id: str, chat_member_id: int = None, page: int = 0, per_page: int = 10) -> str:
        """Текст списка наказаний"""
        if chat_member_id:
            punishments = self.moderation.get_punishments_by_chat_member(chat_member_id, active_only=False, limit=per_page)
        else:
            punishments = self.moderation.get_all_punishments(active_only=False, limit=per_page, offset=page*per_page)
        
        if not punishments:
            return "🔨 Наказания отсутствуют."
        
        text = "🔨 Список наказаний:\n\n"
        for p in punishments:
            is_active = p.get('is_active', 1) and (not p.get('expires_at') or p.get('expires_at') > datetime.now().isoformat())
            status = "✅" if is_active else "❌"
            type_name = p.get('type_name', 'Неизвестно')
            duration = p.get('duration')
            duration_text = f" ({duration}с)" if duration else " (бессрочно)"
            text += f"{status} {type_name}{duration_text}: {p.get('reason', 'Без причины')}\n"
        
        return text

    # ============================================
    # РОЛИ
    # ============================================

    def get_roles_list_text(self) -> str:
        """Текст списка ролей"""
        roles = self.moderation.get_all_roles()
        if not roles:
            return "👑 Роли отсутствуют.\n\nНажмите '➕ Создать роль', чтобы создать первую роль."
        
        text = "👑 Список ролей:\n\n"
        for role in roles:
            status = "⭐" if role.get('is_default', 0) else "  "
            perms = len(self.moderation.get_role_permissions(role['id']))
            text += f"{status} {role.get('name')} (прав: {perms})"
            if role.get('description'):
                text += f"\n   {role.get('description')}"
            text += "\n"
        
        return text

    # ============================================
    # ПРАВА
    # ============================================

    def get_permissions_list_text(self) -> str:
        """Текст списка прав"""
        permissions = self.moderation.get_all_permissions()
        if not permissions:
            return "🔑 Права отсутствуют.\n\nНажмите '➕ Создать', чтобы создать первое право."
        
        text = "🔑 Список прав:\n\n"
        for perm in permissions:
            text += f"• {perm.get('name')}"
            if perm.get('description'):
                text += f" - {perm.get('description')}"
            text += "\n"
        
        return text

    # ============================================
    # СТАТИСТИКА
    # ============================================

    def get_stats_text(self, chat_id: str) -> str:
        """Текст общей статистики"""
        members_count = self.users.get_chat_members_count(chat_id)
        content_count = len(self.content.get_all(community_id=None))
        punishments_active = self.moderation.count_active_punishments()
        
        text = "📊 Статистика сообщества:\n\n"
        text += f"👥 Пользователей: {members_count}\n"
        text += f"📁 Контента: {content_count}\n"
        text += f"🔨 Активных наказаний: {punishments_active}\n"
        
        return text

    def get_stats_content(self, chat_id: str) -> str:
        """Статистика контента"""
        contents = self.content.get_all(community_id=None, active_only=True, limit=20)
        text = "📁 Статистика контента:\n\n"
        if not contents:
            text += "Контент отсутствует"
        else:
            for content in contents:
                text += f"• {content.get('title')} - 👁{content.get('views', 0)} ⬇{content.get('downloads', 0)}\n"
        return text

    def get_stats_users(self, chat_id: str) -> str:
        """Статистика пользователей"""
        members = self.users.get_chat_members(chat_id, active_only=True, limit=10)
        text = "👥 Статистика пользователей:\n\n"
        if not members:
            text += "Пользователи отсутствуют"
        else:
            text += "Топ по сообщениям:\n"
            for i, member in enumerate(members[:10], 1):
                name = member.get('username') or member.get('first_name') or 'Неизвестно'
                text += f"{i}. {name} - {member.get('total_messages', 0)} сообщений\n"
        return text

    # ============================================
    # ЛОГИ
    # ============================================

    def get_logs_paginated(self, chat_id: str, search: str = None, limit: int = 50, offset: int = 0) -> tuple:
        """Получить логи с пагинацией"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = '''
                SELECT l.*, lvl.name as level_name,
                       u.username as user_username
                FROM logs l
                LEFT JOIN log_levels lvl ON lvl.id = l.log_level_id
                LEFT JOIN users u ON u.user_id = l.user_id
                WHERE l.chat_id = ?
            '''
            params = [chat_id]
            
            if search:
                query += ' AND (l.action LIKE ? OR l.details LIKE ?)'
                params.append(f'%{search}%')
                params.append(f'%{search}%')
            
            # Считаем общее количество
            count_query = f'SELECT COUNT(*) FROM ({query})'
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            
            query += ' ORDER BY l.created_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            logs = []
            for row in rows:
                row = dict(row)
                logs.append({
                    'id': row.get('id'),
                    'level_name': row.get('level_name', 'info'),
                    'action': row.get('action', ''),
                    'user_id': row.get('user_id'),
                    'username': row.get('user_username'),
                    'target_id': row.get('target_id'),
                    'details': row.get('details', ''),
                    'created_at': row.get('created_at', '')
                })
            
            return logs, total

    def get_logs_text(self, chat_id: str, search: str = None, page: int = 0, per_page: int = 50) -> str:
        """Текст логов"""
        logs, total = self.get_logs_paginated(chat_id, search=search, limit=per_page, offset=page*per_page)
        
        if not logs:
            return "📝 Логи отсутствуют."
        
        text = "📝 Последние логи:\n\n"
        for log in logs:
            level = log.get('level_name', 'info')
            action = log.get('action', '')
            username = log.get('username') or str(log.get('user_id')) or 'система'
            created = log.get('created_at', '')[:16]
            text += f"[{created}] {level.upper()} - {username}: {action}\n"
        
        total_pages = (total // per_page) + (1 if total % per_page else 0)
        text += f"\nСтраница {page + 1} из {total_pages} | Всего: {total}"
        return text

    # ============================================
    # НАСТРОЙКИ
    # ============================================

    def get_settings_text(self, community_id: str, category: str = None) -> str:
        """Текст настроек"""
        if category:
            settings = self.settings.get_by_category(community_id, category)
            text = f"⚙️ Настройки [{category}]:\n\n"
        else:
            settings = self.settings.get_all(community_id)
            text = "⚙️ Все настройки:\n\n"
        
        if not settings:
            return "Настройки отсутствуют.\n\nНажмите '➕ Добавить', чтобы создать первую настройку."
        
        for setting in settings:
            value = setting.get('value')
            if isinstance(value, (dict, list)):
                value = str(value)[:50] + ("..." if len(str(value)) > 50 else "")
            text += f"• {setting.get('key')} = {value} [{setting.get('value_type')}]\n"
        
        return text

# admin.py - ЧАСТЬ 3 (Главное меню, CRUD для content, menu, buttons)
    # ============================================
    # ГЛАВНОЕ МЕНЮ АДМИНА
    # ============================================

    def get_admin_main_menu(self, community_id: str, user_id: int) -> types.ReplyKeyboardMarkup:
        """
        Главное меню админа строится из БД
        Меню с is_main = 1 для админ-панели
        """
        main_menu = self.menu.get_main_menu(community_id)
        if not main_menu:
            return self._get_default_admin_menu()
        
        buttons = self.menu.get_menu_buttons(main_menu['id'])
        
        filtered_buttons = []
        for btn in buttons:
            action_data = btn.get('action_data', {})
            required_permission = action_data.get('required_permission')
            if required_permission:
                if not self.moderation.has_user_permission(community_id, user_id, required_permission):
                    continue
            filtered_buttons.append(btn)
        
        return KeyboardBuilder.build_reply(filtered_buttons)

    def _get_default_admin_menu(self) -> types.ReplyKeyboardMarkup:
        """Базовое меню админа (если не настроено в БД)"""
        buttons = [
            {'text': '📁 Контент', 'row_num': 0},
            {'text': '📋 Меню', 'row_num': 0},
            {'text': '👥 Пользователи', 'row_num': 1},
            {'text': '🔨 Модерация', 'row_num': 1},
            {'text': '👑 Роли', 'row_num': 2},
            {'text': '📊 Статистика', 'row_num': 2},
            {'text': '📝 Логи', 'row_num': 3},
            {'text': '⚙️ Настройки', 'row_num': 3},
            {'text': '🚪 Выход', 'row_num': 4}
        ]
        return KeyboardBuilder.build_reply(buttons)

    # ============================================
    # CRUD ДЛЯ КОНТЕНТА (дополнительные методы)
    # ============================================

    def get_content_paginated(self, community_id: str, active_only: bool = True, limit: int = 10, offset: int = 0) -> tuple:
        """Получить контент с пагинацией"""
        return self.content.get_paginated(community_id, active_only, limit, offset)

    # ============================================
    # CRUD ДЛЯ МЕНЮ (дополнительные методы)
    # ============================================

    def get_menu_with_buttons(self, menu_id: str) -> Dict[str, Any]:
        """Получить меню с кнопками"""
        menu = self.menu.get_menu(menu_id)
        if not menu:
            return {}
        
        buttons = self.menu.get_all_menu_buttons(menu_id, active_only=False)
        menu['buttons'] = buttons
        return menu

    # ============================================
    # CRUD ДЛЯ КНОПОК (дополнительные методы)
    # ============================================

    def get_button_with_children(self, button_id: str) -> Dict[str, Any]:
        """Получить кнопку с дочерними"""
        button = self.menu.get_button(button_id)
        if not button:
            return {}
        
        children = self.menu.get_button_children(button_id, active_only=False)
        button['children'] = children
        return button

    # ============================================
    # ПОЛЬЗОВАТЕЛИ (дополнительные методы)
    # ============================================

    def get_user_info_text(self, chat_id: str, user_id: int) -> str:
        """Текст информации о пользователе"""
        user = self.users.get(user_id)
        if not user:
            return "👤 Пользователь не найден."
        
        member = self.users.get_chat_member(chat_id, user_id)
        if not member:
            return "👤 Пользователь не найден в этом чате."
        
        text = "👤 Информация о пользователе:\n\n"
        text += f"📌 Имя: {user.get('first_name', 'Неизвестно')}"
        if user.get('last_name'):
            text += f" {user.get('last_name')}"
        text += "\n"
        text += f"🆔 ID: {user.get('user_id')}\n"
        text += f"👤 Username: @{user.get('username') or 'не задан'}\n"
        text += f"📊 Сообщений: {member.get('total_messages', 0)}\n"
        text += f"📅 Вступил: {member.get('joined_at', '')[:16]}\n"
        text += f"📅 Последнее сообщение: {member.get('last_message_at', '')[:16] or 'никогда'}\n"
        text += f"📅 Последний раз: {member.get('last_seen', '')[:16]}\n"
        text += f"✅ Статус: {'Активен' if member.get('is_active', 1) else 'Покинул чат'}\n"
        
        roles = self.moderation.get_user_roles(chat_id, user_id)
        if roles:
            text += f"\n👑 Роли: {', '.join([r.get('name') for r in roles])}\n"
        
        punishments = self.moderation.get_user_active_punishments(chat_id, user_id)
        if punishments:
            text += f"\n🔨 Активные наказания:\n"
            for p in punishments:
                text += f"• {p.get('type_name')}: {p.get('reason', 'Без причины')}\n"
        
        return text

    # ============================================
    # МОДЕРАЦИЯ (дополнительные методы)
    # ============================================

    def get_punishment_info(self, punishment_id: int) -> Optional[Dict[str, Any]]:
        """Получить информацию о наказании"""
        return self.moderation.get_punishment(punishment_id)

    # ============================================
    # РОЛИ (дополнительные методы)
    # ============================================

    def get_role_with_permissions(self, role_id: str) -> Dict[str, Any]:
        """Получить роль с правами"""
        role = self.moderation.get_role(role_id)
        if not role:
            return {}
        
        permissions = self.moderation.get_role_permissions(role_id)
        role['permissions'] = permissions
        return role

    # ============================================
    # ПРАВА (дополнительные методы)
    # ============================================

    def get_permission_with_roles(self, permission_id: str) -> Dict[str, Any]:
        """Получить право с ролями"""
        permission = self.moderation.get_permission(permission_id)
        if not permission:
            return {}
        
        # Получаем роли у которых есть это право
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.* FROM roles r
                JOIN role_permissions rp ON rp.role_id = r.id
                WHERE rp.permission_id = ?
            ''', (permission_id,))
            roles = [dict(row) for row in cursor.fetchall()]
        
        permission['roles'] = roles
        return permission
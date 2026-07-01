# admin.py - ЧАСТЬ 1 (Импорты, состояния, класс AdminPanel, проверки прав, главное меню)
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from typing import Optional, Dict, Any, List
import logging
import sqlite3
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
    LOGS_FILTER = State()
    
    # Настройки
    SETTINGS_CATEGORY = State()
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
    # ПРОВЕРКИ ПРАВ
    # ============================================

    def is_owner(self, user_id: int) -> bool:
        """Проверка владельца из конфига"""
        return user_id in ADMIN_IDS

    def is_admin(self, chat_id: str, user_id: int) -> bool:
        """
        Проверка прав администратора
        1. Сначала проверяем владельца из конфига
        2. Затем проверяем права через роли
        """
        if self.is_owner(user_id):
            return True
        
        return self.moderation.has_user_permission(chat_id, user_id, 'admin_panel_access')

    def can_manage_content(self, chat_id: str, user_id: int) -> bool:
        """Проверка права управления контентом"""
        if self.is_owner(user_id):
            return True
        return self.moderation.has_user_permission(chat_id, user_id, 'manage_content')

    def can_manage_users(self, chat_id: str, user_id: int) -> bool:
        """Проверка права управления пользователями"""
        if self.is_owner(user_id):
            return True
        return self.moderation.has_user_permission(chat_id, user_id, 'manage_users')

    def can_manage_roles(self, chat_id: str, user_id: int) -> bool:
        """Проверка права управления ролями"""
        if self.is_owner(user_id):
            return True
        return self.moderation.has_user_permission(chat_id, user_id, 'manage_roles')

    def can_manage_settings(self, chat_id: str, user_id: int) -> bool:
        """Проверка права управления настройками"""
        if self.is_owner(user_id):
            return True
        return self.moderation.has_user_permission(chat_id, user_id, 'manage_settings')

    def can_moderate(self, chat_id: str, user_id: int) -> bool:
        """Проверка права модерации"""
        if self.is_owner(user_id):
            return True
        return self.moderation.has_user_permission(chat_id, user_id, 'moderate_users')

    def can_view_stats(self, chat_id: str, user_id: int) -> bool:
        """Проверка права просмотра статистики"""
        if self.is_owner(user_id):
            return True
        return self.moderation.has_user_permission(chat_id, user_id, 'view_stats')

    def can_view_logs(self, chat_id: str, user_id: int) -> bool:
        """Проверка права просмотра логов"""
        if self.is_owner(user_id):
            return True
        return self.moderation.has_user_permission(chat_id, user_id, 'view_logs')

    # ============================================
    # ГЛАВНОЕ МЕНЮ АДМИНА (строится из БД)
    # ============================================

    def get_admin_main_menu(self, chat_id: str, user_id: int) -> types.ReplyKeyboardMarkup:
        """
        Главное меню админа строится из БД
        Меню с is_main = 1 для админ-панели
        """
        main_menu = self.menu.get_main_menu(chat_id)
        if not main_menu:
            return self._get_default_admin_menu()
        
        buttons = self.menu.get_menu_buttons(main_menu['id'])
        
        filtered_buttons = []
        for btn in buttons:
            action_data = btn.get('action_data', {})
            required_permission = action_data.get('required_permission')
            if required_permission:
                if not self.moderation.has_user_permission(chat_id, user_id, required_permission):
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
# admin.py - ЧАСТЬ 2 (Методы получения данных из БД)
    # ============================================
    # ПОЛУЧЕНИЕ ДАННЫХ ИЗ БД
    # ============================================

    def get_content_list_text(self, page: int = 0, per_page: int = 10) -> str:
        """Текст списка контента из БД"""
        contents = self.content.get_all(active_only=False, limit=per_page, offset=page * per_page)
        total = len(self.content.get_all(active_only=False))
        
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

    def get_menu_list_text(self, community_id: str) -> str:
        """Текст списка меню из БД"""
        menus = self.menu.get_menus(community_id, active_only=False)
        if not menus:
            return "📋 Меню отсутствуют.\n\nНажмите '➕ Добавить', чтобы создать первое меню."
        
        text = "📋 Список меню:\n\n"
        for menu in menus:
            status = "✅" if menu.get('is_active', 1) else "❌"
            main = "⭐" if menu.get('is_main', 0) else "  "
            buttons_count = len(self.menu.get_all_menu_buttons(menu['id'], active_only=False))
            text += f"{main} {status} {menu.get('name')} (кнопок: {buttons_count})\n"
        
        return text

    def get_buttons_list_text(self, menu_id: str) -> str:
        """Текст списка кнопок меню из БД"""
        buttons = self.menu.get_all_menu_buttons(menu_id, active_only=False)
        if not buttons:
            return "🔘 Кнопки отсутствуют.\n\nНажмите '➕ Добавить', чтобы создать первую кнопку."
        
        text = "🔘 Список кнопок:\n\n"
        for btn in buttons:
            status = "✅" if btn.get('is_active', 1) else "❌"
            action = btn.get('action_name', 'Неизвестно')
            children = len(self.menu.get_button_children(btn['id'], active_only=False))
            child_text = f" (🔽{children})" if children else ""
            text += f"{status} {btn.get('text')} [{action}] ряд {btn.get('row_num', 0)}/{btn.get('order_num', 0)}{child_text}\n"
        
        return text

    def get_users_list_text(self, chat_id: str, page: int = 0, per_page: int = 10) -> str:
        """Текст списка пользователей из БД"""
        members = self.users.get_chat_members(chat_id, active_only=False, limit=per_page, offset=page * per_page)
        total = self.users.get_chat_members_count(chat_id, active_only=False)
        
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

    def get_punishments_list_text(self, chat_id: str, chat_member_id: int = None, page: int = 0, per_page: int = 10) -> str:
        """Текст списка наказаний из БД"""
        if chat_member_id:
            punishments = self.moderation.get_punishments_by_chat_member(chat_member_id, active_only=False, limit=per_page)
        else:
            punishments = self.moderation.get_all_punishments(active_only=False, limit=per_page, offset=page * per_page)
        
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

    def get_roles_list_text(self) -> str:
        """Текст списка ролей из БД"""
        roles = self.moderation.get_all_roles()
        if not roles:
            return "👑 Роли отсутствуют.\n\nНажмите '➕ Добавить', чтобы создать первую роль."
        
        text = "👑 Список ролей:\n\n"
        for role in roles:
            status = "⭐" if role.get('is_default', 0) else "  "
            perms = len(self.moderation.get_role_permissions(role['id']))
            text += f"{status} {role.get('name')} (прав: {perms})"
            if role.get('description'):
                text += f"\n   {role.get('description')}"
            text += "\n"
        
        return text

    def get_permissions_list_text(self) -> str:
        """Текст списка прав из БД"""
        permissions = self.moderation.get_all_permissions()
        if not permissions:
            return "🔑 Права отсутствуют.\n\nНажмите '➕ Добавить', чтобы создать первое право."
        
        text = "🔑 Список прав:\n\n"
        for perm in permissions:
            text += f"• {perm.get('name')}"
            if perm.get('description'):
                text += f" - {perm.get('description')}"
            text += "\n"
        
        return text

    def get_logs_text(self, chat_id: str, filters: Dict[str, Any] = None, page: int = 0, per_page: int = 50) -> str:
        """Текст логов из БД"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = '''
                SELECT l.*, lvl.name as level_name,
                       u.username as user_username,
                       u2.username as target_username
                FROM logs l
                LEFT JOIN log_levels lvl ON lvl.id = l.log_level_id
                LEFT JOIN users u ON u.user_id = l.user_id
                LEFT JOIN users u2 ON u2.user_id = l.target_id
                WHERE l.chat_id = ?
            '''
            params = [chat_id]
            
            if filters:
                if filters.get('level'):
                    query += ' AND l.log_level_id = ?'
                    params.append(filters['level'])
                if filters.get('action'):
                    query += ' AND l.action LIKE ?'
                    params.append(f'%{filters["action"]}%')
                if filters.get('user_id'):
                    query += ' AND l.user_id = ?'
                    params.append(filters['user_id'])
            
            query += ' ORDER BY l.created_at DESC LIMIT ? OFFSET ?'
            params.extend([per_page, page * per_page])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            if not rows:
                return "📝 Логи отсутствуют."
            
            text = "📝 Последние логи:\n\n"
            for row in rows:
                row = dict(row)
                level = row.get('level_name', 'info')
                action = row.get('action', '')
                username = row.get('user_username') or str(row.get('user_id')) or 'система'
                created = row.get('created_at', '')[:16]
                text += f"[{created}] {level.upper()} - {username}: {action}\n"
            
            text += f"\nСтраница {page + 1}"
            return text

    def get_stats_text(self, chat_id: str) -> str:
        """Текст статистики из БД"""
        members_count = self.users.get_chat_members_count(chat_id)
        content_count = len(self.content.get_all())
        punishments_active = self.moderation.count_active_punishments()
        
        text = "📊 Статистика сообщества:\n\n"
        text += f"👥 Пользователей: {members_count}\n"
        text += f"📁 Контента: {content_count}\n"
        text += f"🔨 Активных наказаний: {punishments_active}\n"
        
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT cm.user_id, u.username, u.first_name, cm.total_messages
                FROM chat_members cm
                JOIN users u ON u.user_id = cm.user_id
                WHERE cm.chat_id = ? AND cm.is_active = 1
                ORDER BY cm.total_messages DESC
                LIMIT 5
            ''', (chat_id,))
            
            top_users = cursor.fetchall()
            if top_users:
                text += "\n🏆 Топ пользователей:\n"
                for i, user in enumerate(top_users, 1):
                    user = dict(user)
                    name = user.get('username') or user.get('first_name') or 'Неизвестно'
                    text += f"{i}. {name} - {user.get('total_messages', 0)} сообщений\n"
        
        popular = self.content.get_all(active_only=True, limit=5)
        if popular:
            text += "\n🔥 Популярный контент:\n"
            for content in popular:
                text += f"• {content.get('title')} 👁{content.get('views', 0)} ⬇{content.get('downloads', 0)}\n"
        
        return text

    def get_settings_text(self, community_id: str, category: str = None) -> str:
        """Текст настроек из БД"""
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

    def get_community_info_text(self, community_id: str) -> str:
        """Текст информации о сообществе из БД"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM communities WHERE id = ?', (community_id,))
            row = cursor.fetchone()
            
            if not row:
                return "🏠 Сообщество не найдено."
            
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
            
            content = self.content.get_all()
            text += f"📁 Контент: {len(content)}\n"
            
            return text

    def get_user_info_text(self, chat_id: str, user_id: int) -> str:
        """Текст информации о пользователе из БД"""
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
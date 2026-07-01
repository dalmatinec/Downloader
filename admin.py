# admin.py
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from typing import Optional, Dict, Any, List
import logging

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
        # Получаем главное меню из БД
        main_menu = self.menu.get_main_menu(chat_id)
        if not main_menu:
            # Если меню не настроено - показываем базовое
            return self._get_default_admin_menu()
        
        # Получаем кнопки из БД
        buttons = self.menu.get_menu_buttons(main_menu['id'])
        
        # Фильтруем по правам
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

    # ============================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ============================================

    def get_content_list_text(self, page: int = 0, per_page: int = 10) -> str:
        """Текст списка контента из БД"""
        contents = self.content.get_all(active_only=False, limit=per_page, offset=page * per_page)
        if not contents:
            return "📁 Контент отсутствует.\n\nНажмите '➕ Добавить', чтобы создать первый контент."
        
        text = "📁 Список контента:\n\n"
        for i, content in enumerate(contents, start=1):
            status = "✅" if content.get('is_active', 1) else "❌"
            type_name = content.get('type_name', 'Неизвестно')
            text += f"{i}. {status} {content.get('title')} [{type_name}]\n"
        
        text += f"\nСтраница {page + 1}"
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
            text += f"{main} {status} {menu.get('name')}\n"
        
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
            text += f"{status} {btn.get('text')} [{action}] (ряд {btn.get('row_num', 0)}, порядок {btn.get('order_num', 0)})\n"
        
        return text

    def get_users_list_text(self, chat_id: str, page: int = 0, per_page: int = 10) -> str:
        """Текст списка пользователей из БД"""
        members = self.users.get_chat_members(chat_id, active_only=False, limit=per_page, offset=page * per_page)
        if not members:
            return "👥 Пользователи отсутствуют."
        
        text = "👥 Список пользователей:\n\n"
        for member in members:
            username = member.get('username') or 'без username'
            name = member.get('first_name') or 'Без имени'
            status = "✅" if member.get('is_active', 1) else "❌"
            messages = member.get('total_messages', 0)
            text += f"{status} {name} (@{username}) - {messages} сообщений\n"
        
        text += f"\nСтраница {page + 1}"
        return text

    def get_punishments_list_text(self, chat_member_id: int = None, page: int = 0, per_page: int = 10) -> str:
        """Текст списка наказаний из БД"""
        if chat_member_id:
            punishments = self.moderation.get_punishments_by_chat_member(chat_member_id, active_only=False, limit=per_page)
        else:
            punishments = self.moderation.get_all_punishments(active_only=False, limit=per_page, offset=page * per_page)
        
        if not punishments:
            return "🔨 Наказания отсутствуют."
        
        text = "🔨 Список наказаний:\n\n"
        for p in punishments:
            status = "✅" if p.get('is_active', 1) and (not p.get('expires_at') or p.get('expires_at') > str(datetime.now())) else "❌"
            type_name = p.get('type_name', 'Неизвестно')
            text += f"{status} {type_name}: {p.get('reason', 'Без причины')}\n"
        
        return text

    def get_roles_list_text(self) -> str:
        """Текст списка ролей из БД"""
        roles = self.moderation.get_all_roles()
        if not roles:
            return "👑 Роли отсутствуют.\n\nНажмите '➕ Добавить', чтобы создать первую роль."
        
        text = "👑 Список ролей:\n\n"
        for role in roles:
            status = "⭐" if role.get('is_default', 0) else "  "
            text += f"{status} {role.get('name')}\n"
            if role.get('description'):
                text += f"   {role.get('description')}\n"
        
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

    def get_logs_text(self, filters: Dict[str, Any] = None, page: int = 0, per_page: int = 50) -> str:
        """Текст логов из БД"""
        # TODO: Реализовать получение логов из БД
        return "📝 Логи\n\nФункция в разработке."

    def get_stats_text(self, chat_id: str) -> str:
        """Текст статистики из БД"""
        # TODO: Реализовать статистику из БД
        return "📊 Статистика\n\nФункция в разработке."

    def get_settings_text(self, community_id: str, category: str = None) -> str:
        """Текст настроек из БД"""
        if category:
            settings = self.settings.get_by_category(community_id, category)
            text = f"⚙️ Настройки [{category}]:\n\n"
        else:
            settings = self.settings.get_all(community_id)
            text = "⚙️ Все настройки:\n\n"
        
        if not settings:
            return "Настройки отсутствуют."
        
        for setting in settings:
            value = setting.get('value')
            if isinstance(value, (dict, list)):
                value = str(value)[:50] + "..."
            text += f"• {setting.get('key')} = {value}\n"
        
        return text

    def get_community_info_text(self, community_id: str) -> str:
        """Текст информации о сообществе из БД"""
        # TODO: Получить сообщество из БД
        return "🏠 Информация о сообществе\n\nФункция в разработке."
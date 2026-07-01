# moderation.py - ЧАСТЬ 1 (Импорты, Типы наказаний)
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from db import Database


# Единый способ работы со временем
def now():
    return datetime.now(timezone.utc)


class ModerationManager:
    """Управление модерацией"""

    def __init__(self, db: Database):
        self.db = db

    # ============================================
    # ТИПЫ НАКАЗАНИЙ (CRUD)
    # ============================================

    def create_punishment_type(self, data: Dict[str, Any]) -> str:
        """
        Создание типа наказания
        data: {
            id, name, description, is_active
        }
        """
        type_id = data.get('id', str(uuid.uuid4()))

        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR IGNORE INTO punishment_types (id, name, description, is_active)
                VALUES (?, ?, ?, ?)
            ''', (
                type_id,
                data.get('name'),
                data.get('description', ''),
                data.get('is_active', 1)
            ))

            conn.commit()
            return type_id

    def get_punishment_type(self, type_id: str) -> Optional[Dict[str, Any]]:
        """Получение типа наказания по ID"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM punishment_types WHERE id = ?', (type_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_punishment_type_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Получение типа наказания по имени"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM punishment_types WHERE name = ?', (name,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_punishment_types(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Получение всех типов наказаний"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = 'SELECT * FROM punishment_types'
            params = []

            if active_only:
                query += ' WHERE is_active = 1'

            query += ' ORDER BY name'

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def update_punishment_type(self, type_id: str, data: Dict[str, Any]) -> bool:
        """Обновление типа наказания"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            updates = []
            params = []

            fields = ['name', 'description', 'is_active']
            for field in fields:
                if field in data:
                    updates.append(f"{field} = ?")
                    params.append(data[field])

            if not updates:
                return False

            params.append(type_id)

            cursor.execute(f'''
                UPDATE punishment_types SET {', '.join(updates)} WHERE id = ?
            ''', params)

            conn.commit()
            return cursor.rowcount > 0

    def delete_punishment_type(self, type_id: str, soft: bool = True) -> bool:
        """
        Удаление типа наказания
        soft=True - отключает is_active
        soft=False - удаляет полностью
        """
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if soft:
                cursor.execute('''
                    UPDATE punishment_types SET is_active = 0 WHERE id = ?
                ''', (type_id,))
            else:
                cursor.execute('DELETE FROM punishment_types WHERE id = ?', (type_id,))

            conn.commit()
            return cursor.rowcount > 0

    def count_punishment_types(self, active_only: bool = True) -> int:
        """Количество типов наказаний"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = 'SELECT COUNT(*) FROM punishment_types'
            params = []

            if active_only:
                query += ' WHERE is_active = 1'

            cursor.execute(query, params)
            return cursor.fetchone()[0]

# moderation.py - ЧАСТЬ 2 (Наказания)

    # ============================================
    # НАКАЗАНИЯ (полный CRUD)
    # ============================================

    def create_punishment(self, data: Dict[str, Any]) -> int:
        """
        Создание наказания
        data: {
            chat_member_id, punishment_type_id, reason, duration, issued_by
        }
        """
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            expires_at = None
            if data.get('duration'):
                expires_at = now() + timedelta(seconds=data['duration'])

            cursor.execute('''
                INSERT INTO punishments (
                    chat_member_id, punishment_type_id, reason, duration,
                    issued_by, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data.get('chat_member_id'),
                data.get('punishment_type_id'),
                data.get('reason', ''),
                data.get('duration'),
                data.get('issued_by'),
                expires_at
            ))

            conn.commit()
            return cursor.lastrowid

    def get_punishment(self, punishment_id: int) -> Optional[Dict[str, Any]]:
        """Получение наказания по ID"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT p.*, pt.name as type_name,
                       issuer.username as issued_by_username,
                       revoker.username as revoked_by_username
                FROM punishments p
                LEFT JOIN punishment_types pt ON pt.id = p.punishment_type_id
                LEFT JOIN users issuer ON issuer.user_id = p.issued_by
                LEFT JOIN users revoker ON revoker.user_id = p.revoked_by
                WHERE p.id = ?
            ''', (punishment_id,))

            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_punishments(self, active_only: bool = False, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Получение всех наказаний"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = '''
                SELECT p.*, pt.name as type_name,
                       issuer.username as issued_by_username
                FROM punishments p
                LEFT JOIN punishment_types pt ON pt.id = p.punishment_type_id
                LEFT JOIN users issuer ON issuer.user_id = p.issued_by
                WHERE 1=1
            '''
            params = []

            if active_only:
                query += ' AND p.is_active = 1'
                query += ' AND (p.expires_at IS NULL OR p.expires_at > CURRENT_TIMESTAMP)'

            query += ' ORDER BY p.issued_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_punishments_by_chat_member(self, chat_member_id: int, active_only: bool = False, limit: int = 100) -> List[Dict[str, Any]]:
        """Получение наказаний участника"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = '''
                SELECT p.*, pt.name as type_name,
                       issuer.username as issued_by_username,
                       revoker.username as revoked_by_username
                FROM punishments p
                LEFT JOIN punishment_types pt ON pt.id = p.punishment_type_id
                LEFT JOIN users issuer ON issuer.user_id = p.issued_by
                LEFT JOIN users revoker ON revoker.user_id = p.revoked_by
                WHERE p.chat_member_id = ?
            '''
            params = [chat_member_id]

            if active_only:
                query += ' AND p.is_active = 1'
                query += ' AND (p.expires_at IS NULL OR p.expires_at > CURRENT_TIMESTAMP)'

            query += ' ORDER BY p.issued_at DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_punishments_by_user(self, chat_id: str, user_id: int, active_only: bool = False, limit: int = 100) -> List[Dict[str, Any]]:
        """Получение наказаний пользователя в чате"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = '''
                SELECT p.*, pt.name as type_name,
                       issuer.username as issued_by_username,
                       revoker.username as revoked_by_username
                FROM punishments p
                JOIN chat_members cm ON cm.id = p.chat_member_id
                LEFT JOIN punishment_types pt ON pt.id = p.punishment_type_id
                LEFT JOIN users issuer ON issuer.user_id = p.issued_by
                LEFT JOIN users revoker ON revoker.user_id = p.revoked_by
                WHERE cm.chat_id = ? AND cm.user_id = ?
            '''
            params = [chat_id, user_id]

            if active_only:
                query += ' AND p.is_active = 1'
                query += ' AND (p.expires_at IS NULL OR p.expires_at > CURRENT_TIMESTAMP)'

            query += ' ORDER BY p.issued_at DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_active_punishments(self, chat_member_id: int = None) -> List[Dict[str, Any]]:
        """Получение активных наказаний"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = '''
                SELECT p.*, pt.name as type_name,
                       issuer.username as issued_by_username
                FROM punishments p
                LEFT JOIN punishment_types pt ON pt.id = p.punishment_type_id
                LEFT JOIN users issuer ON issuer.user_id = p.issued_by
                WHERE p.is_active = 1
                    AND (p.expires_at IS NULL OR p.expires_at > CURRENT_TIMESTAMP)
            '''
            params = []

            if chat_member_id:
                query += ' AND p.chat_member_id = ?'
                params.append(chat_member_id)

            query += ' ORDER BY p.issued_at DESC'

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_expired_punishments(self) -> List[Dict[str, Any]]:
        """Получение просроченных наказаний"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT p.*, pt.name as type_name
                FROM punishments p
                LEFT JOIN punishment_types pt ON pt.id = p.punishment_type_id
                WHERE p.is_active = 1
                    AND p.expires_at IS NOT NULL
                    AND p.expires_at <= CURRENT_TIMESTAMP
                ORDER BY p.issued_at DESC
            ''')

            return [dict(row) for row in cursor.fetchall()]

    def expire_punishments(self) -> int:
        """Автоматическое отключение просроченных наказаний"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE punishments
                SET is_active = 0, revoked_at = CURRENT_TIMESTAMP, revoked_reason = 'expired'
                WHERE is_active = 1
                    AND expires_at IS NOT NULL
                    AND expires_at <= CURRENT_TIMESTAMP
            ''')

            conn.commit()
            return cursor.rowcount

    def update_punishment(self, punishment_id: int, data: Dict[str, Any]) -> bool:
        """Обновление наказания"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            updates = []
            params = []

            fields = ['punishment_type_id', 'reason', 'is_active']
            for field in fields:
                if field in data:
                    updates.append(f"{field} = ?")
                    params.append(data[field])

            if 'duration' in data:
                if data['duration']:
                    updates.append("duration = ?")
                    params.append(data['duration'])
                    updates.append("expires_at = ?")
                    params.append(now() + timedelta(seconds=data['duration']))
                else:
                    updates.append("duration = NULL")
                    updates.append("expires_at = NULL")

            if not updates:
                return False

            params.append(punishment_id)

            cursor.execute(f'''
                UPDATE punishments SET {', '.join(updates)} WHERE id = ?
            ''', params)

            conn.commit()
            return cursor.rowcount > 0

    def revoke_punishment(self, punishment_id: int, revoked_by: int, reason: str = '') -> bool:
        """Отмена наказания"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE punishments
                SET is_active = 0, revoked_at = CURRENT_TIMESTAMP,
                    revoked_by = ?, revoked_reason = ?
                WHERE id = ? AND is_active = 1
            ''', (revoked_by, reason, punishment_id))

            conn.commit()
            return cursor.rowcount > 0

    def revoke_all_punishments(self, chat_member_id: int, revoked_by: int, reason: str = '', punishment_type_id: str = None) -> int:
        """
        Отмена всех наказаний участника
        punishment_type_id - только определенный тип
        """
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = '''
                UPDATE punishments
                SET is_active = 0, revoked_at = CURRENT_TIMESTAMP,
                    revoked_by = ?, revoked_reason = ?
                WHERE chat_member_id = ? AND is_active = 1
            '''
            params = [revoked_by, reason, chat_member_id]

            if punishment_type_id:
                query += ' AND punishment_type_id = ?'
                params.append(punishment_type_id)

            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount

    def delete_punishment(self, punishment_id: int) -> bool:
        """Полное удаление наказания"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('DELETE FROM punishments WHERE id = ?', (punishment_id,))
            conn.commit()
            return cursor.rowcount > 0

    def count_active_punishments(self, chat_member_id: int = None) -> int:
        """Количество активных наказаний"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = '''
                SELECT COUNT(*) FROM punishments
                WHERE is_active = 1
                    AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            '''
            params = []

            if chat_member_id:
                query += ' AND chat_member_id = ?'
                params.append(chat_member_id)

            cursor.execute(query, params)
            return cursor.fetchone()[0]

    def is_user_punished(self, chat_id: str, user_id: int, punishment_type_id: str = None) -> bool:
        """Проверка, наказан ли пользователь"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = '''
                SELECT COUNT(*) FROM punishments p
                JOIN chat_members cm ON cm.id = p.chat_member_id
                WHERE cm.chat_id = ? AND cm.user_id = ?
                    AND p.is_active = 1
                    AND (p.expires_at IS NULL OR p.expires_at > CURRENT_TIMESTAMP)
            '''
            params = [chat_id, user_id]

            if punishment_type_id:
                query += ' AND p.punishment_type_id = ?'
                params.append(punishment_type_id)

            cursor.execute(query, params)
            return cursor.fetchone()[0] > 0

    def search_punishments(self, filters: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """
        Поиск наказаний по фильтрам
        filters: {
            chat_member_id, punishment_type_id, issued_by, revoked_by,
            user_id, chat_id, from_date, to_date, is_active, reason
        }
        """
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = '''
                SELECT p.*, pt.name as type_name,
                       issuer.username as issued_by_username,
                       revoker.username as revoked_by_username,
                       cm.user_id, cm.chat_id
                FROM punishments p
                LEFT JOIN punishment_types pt ON pt.id = p.punishment_type_id
                LEFT JOIN users issuer ON issuer.user_id = p.issued_by
                LEFT JOIN users revoker ON revoker.user_id = p.revoked_by
                JOIN chat_members cm ON cm.id = p.chat_member_id
                WHERE 1=1
            '''
            params = []

            if 'chat_member_id' in filters:
                query += ' AND p.chat_member_id = ?'
                params.append(filters['chat_member_id'])

            if 'punishment_type_id' in filters:
                query += ' AND p.punishment_type_id = ?'
                params.append(filters['punishment_type_id'])

            if 'issued_by' in filters:
                query += ' AND p.issued_by = ?'
                params.append(filters['issued_by'])

            if 'revoked_by' in filters:
                query += ' AND p.revoked_by = ?'
                params.append(filters['revoked_by'])

            if 'user_id' in filters:
                query += ' AND cm.user_id = ?'
                params.append(filters['user_id'])

            if 'chat_id' in filters:
                query += ' AND cm.chat_id = ?'
                params.append(filters['chat_id'])

            if 'from_date' in filters:
                query += ' AND p.issued_at >= ?'
                params.append(filters['from_date'])

            if 'to_date' in filters:
                query += ' AND p.issued_at <= ?'
                params.append(filters['to_date'])

            if 'reason' in filters:
                query += ' AND p.reason LIKE ?'
                params.append(f'%{filters["reason"]}%')

            if 'is_active' in filters:
                if filters['is_active']:
                    query += ' AND p.is_active = 1'
                    query += ' AND (p.expires_at IS NULL OR p.expires_at > CURRENT_TIMESTAMP)'
                else:
                    query += ' AND p.is_active = 0'

            query += ' ORDER BY p.issued_at DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

# moderation.py - ЧАСТЬ 3 (Роли, Права, Роли участников)

    # ============================================
    # РОЛИ (полный CRUD)
    # ============================================

    def create_role(self, data: Dict[str, Any]) -> str:
        """
        Создание роли
        data: {
            id, name, description, is_default
        }
        """
        role_id = data.get('id', str(uuid.uuid4()))

        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR IGNORE INTO roles (id, name, description, is_default)
                VALUES (?, ?, ?, ?)
            ''', (
                role_id,
                data.get('name'),
                data.get('description', ''),
                data.get('is_default', 0)
            ))

            conn.commit()
            return role_id

    def get_role(self, role_id: str) -> Optional[Dict[str, Any]]:
        """Получение роли по ID"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM roles WHERE id = ?', (role_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_role_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Получение роли по имени"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM roles WHERE name = ?', (name,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_default_role(self) -> Optional[Dict[str, Any]]:
        """Получение роли по умолчанию"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM roles WHERE is_default = 1 LIMIT 1')
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_roles(self, with_permissions: bool = False) -> List[Dict[str, Any]]:
        """Получение всех ролей"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM roles ORDER BY is_default DESC, name')
            roles = [dict(row) for row in cursor.fetchall()]

            if with_permissions:
                for role in roles:
                    role['permissions'] = self.get_role_permissions(role['id'])

            return roles

    def update_role(self, role_id: str, data: Dict[str, Any]) -> bool:
        """Обновление роли"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            updates = []
            params = []

            fields = ['name', 'description', 'is_default']
            for field in fields:
                if field in data:
                    updates.append(f"{field} = ?")
                    params.append(data[field])

            if not updates:
                return False

            params.append(role_id)

            cursor.execute(f'''
                UPDATE roles SET {', '.join(updates)} WHERE id = ?
            ''', params)

            conn.commit()
            return cursor.rowcount > 0

    def delete_role(self, role_id: str) -> bool:
        """Полное удаление роли"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('DELETE FROM role_permissions WHERE role_id = ?', (role_id,))
            cursor.execute('DELETE FROM member_roles WHERE role_id = ?', (role_id,))
            cursor.execute('DELETE FROM roles WHERE id = ?', (role_id,))

            conn.commit()
            return cursor.rowcount > 0

    def count_roles(self) -> int:
        """Количество ролей"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM roles')
            return cursor.fetchone()[0]

    def role_exists(self, role_id: str) -> bool:
        """Проверка существования роли"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM roles WHERE id = ?', (role_id,))
            return cursor.fetchone() is not None

    # ============================================
    # ПРАВА (полный CRUD)
    # ============================================

    def create_permission(self, data: Dict[str, Any]) -> str:
        """
        Создание права
        data: {
            id, name, description
        }
        """
        perm_id = data.get('id', str(uuid.uuid4()))

        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR IGNORE INTO permissions (id, name, description)
                VALUES (?, ?, ?)
            ''', (
                perm_id,
                data.get('name'),
                data.get('description', '')
            ))

            conn.commit()
            return perm_id

    def get_permission(self, permission_id: str) -> Optional[Dict[str, Any]]:
        """Получение права по ID"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM permissions WHERE id = ?', (permission_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_permission_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Получение права по имени"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM permissions WHERE name = ?', (name,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_permissions(self) -> List[Dict[str, Any]]:
        """Получение всех прав"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM permissions ORDER BY name')
            return [dict(row) for row in cursor.fetchall()]

    def update_permission(self, permission_id: str, data: Dict[str, Any]) -> bool:
        """Обновление права"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            updates = []
            params = []

            fields = ['name', 'description']
            for field in fields:
                if field in data:
                    updates.append(f"{field} = ?")
                    params.append(data[field])

            if not updates:
                return False

            params.append(permission_id)

            cursor.execute(f'''
                UPDATE permissions SET {', '.join(updates)} WHERE id = ?
            ''', params)

            conn.commit()
            return cursor.rowcount > 0

    def delete_permission(self, permission_id: str) -> bool:
        """Полное удаление права"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('DELETE FROM role_permissions WHERE permission_id = ?', (permission_id,))
            cursor.execute('DELETE FROM permissions WHERE id = ?', (permission_id,))

            conn.commit()
            return cursor.rowcount > 0

    def count_permissions(self) -> int:
        """Количество прав"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM permissions')
            return cursor.fetchone()[0]

    def permission_exists(self, permission_id: str) -> bool:
        """Проверка существования права"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM permissions WHERE id = ?', (permission_id,))
            return cursor.fetchone() is not None

    # ============================================
    # ПРАВА РОЛЕЙ
    # ============================================

    def assign_permission_to_role(self, role_id: str, permission_id: str) -> bool:
        """Назначение права роли"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                VALUES (?, ?)
            ''', (role_id, permission_id))

            conn.commit()
            return cursor.rowcount > 0

    def remove_permission_from_role(self, role_id: str, permission_id: str) -> bool:
        """Удаление права у роли"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                DELETE FROM role_permissions
                WHERE role_id = ? AND permission_id = ?
            ''', (role_id, permission_id))

            conn.commit()
            return cursor.rowcount > 0

    def get_role_permissions(self, role_id: str) -> List[Dict[str, Any]]:
        """Получение прав роли"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT p.* FROM permissions p
                JOIN role_permissions rp ON rp.permission_id = p.id
                WHERE rp.role_id = ?
                ORDER BY p.name
            ''', (role_id,))

            return [dict(row) for row in cursor.fetchall()]

    def has_permission(self, role_id: str, permission_name: str) -> bool:
        """Проверка наличия права у роли"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT COUNT(*) FROM role_permissions rp
                JOIN permissions p ON p.id = rp.permission_id
                WHERE rp.role_id = ? AND p.name = ?
            ''', (role_id, permission_name))

            return cursor.fetchone()[0] > 0

    def clear_role_permissions(self, role_id: str) -> bool:
        """Очистка всех прав роли"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('DELETE FROM role_permissions WHERE role_id = ?', (role_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_user_permissions(self, chat_id: str, user_id: int) -> List[str]:
        """Получение всех прав пользователя через его роли"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT DISTINCT p.name
                FROM permissions p
                JOIN role_permissions rp ON rp.permission_id = p.id
                JOIN roles r ON r.id = rp.role_id
                JOIN member_roles mr ON mr.role_id = r.id
                JOIN chat_members cm ON cm.id = mr.chat_member_id
                WHERE cm.chat_id = ? AND cm.user_id = ?
                ORDER BY p.name
            ''', (chat_id, user_id))

            return [row[0] for row in cursor.fetchall()]

    def has_user_permission(self, chat_id: str, user_id: int, permission_name: str) -> bool:
        """Проверка наличия права у пользователя"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT COUNT(*) FROM role_permissions rp
                JOIN permissions p ON p.id = rp.permission_id
                JOIN roles r ON r.id = rp.role_id
                JOIN member_roles mr ON mr.role_id = r.id
                JOIN chat_members cm ON cm.id = mr.chat_member_id
                WHERE cm.chat_id = ? AND cm.user_id = ? AND p.name = ?
            ''', (chat_id, user_id, permission_name))

            return cursor.fetchone()[0] > 0

    # ============================================
    # РОЛИ УЧАСТНИКОВ
    # ============================================

    def assign_role_to_member(self, chat_member_id: int, role_id: str, assigned_by: int = None) -> bool:
        """Назначение роли участнику"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR IGNORE INTO member_roles (chat_member_id, role_id, assigned_by)
                VALUES (?, ?, ?)
            ''', (chat_member_id, role_id, assigned_by))

            conn.commit()
            return cursor.rowcount > 0

    def remove_role_from_member(self, chat_member_id: int, role_id: str) -> bool:
        """Удаление роли у участника"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                DELETE FROM member_roles
                WHERE chat_member_id = ? AND role_id = ?
            ''', (chat_member_id, role_id))

            conn.commit()
            return cursor.rowcount > 0

    def get_member_roles(self, chat_member_id: int) -> List[Dict[str, Any]]:
        """Получение ролей участника"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT r.*, mr.assigned_at, mr.assigned_by
                FROM roles r
                JOIN member_roles mr ON mr.role_id = r.id
                WHERE mr.chat_member_id = ?
                ORDER BY r.is_default DESC, r.name
            ''', (chat_member_id,))

            return [dict(row) for row in cursor.fetchall()]

    def get_user_roles(self, chat_id: str, user_id: int) -> List[Dict[str, Any]]:
        """Получение ролей пользователя в чате"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT r.*, mr.assigned_at, mr.assigned_by
                FROM roles r
                JOIN member_roles mr ON mr.role_id = r.id
                JOIN chat_members cm ON cm.id = mr.chat_member_id
                WHERE cm.chat_id = ? AND cm.user_id = ?
                ORDER BY r.is_default DESC, r.name
            ''', (chat_id, user_id))

            return [dict(row) for row in cursor.fetchall()]

    def get_members_with_role(self, role_id: str, chat_id: str = None) -> List[Dict[str, Any]]:
        """Получение участников с ролью"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = '''
                SELECT cm.*, u.username, u.first_name, u.last_name
                FROM member_roles mr
                JOIN chat_members cm ON cm.id = mr.chat_member_id
                JOIN users u ON u.user_id = cm.user_id
                WHERE mr.role_id = ?
            '''
            params = [role_id]

            if chat_id:
                query += ' AND cm.chat_id = ?'
                params.append(chat_id)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def clear_member_roles(self, chat_member_id: int) -> bool:
        """Очистка всех ролей участника"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('DELETE FROM member_roles WHERE chat_member_id = ?', (chat_member_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_member_default_role(self, chat_member_id: int) -> Optional[Dict[str, Any]]:
        """Получение роли по умолчанию участника"""
        roles = self.get_member_roles(chat_member_id)
        for role in roles:
            if role.get('is_default', 0) == 1:
                return role
        return None
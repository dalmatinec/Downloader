# users.py
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from db import Database


class UserManager:
    """Управление пользователями"""

    def __init__(self, db: Database):
        self.db = db

    # ============================================
    # ПОЛЬЗОВАТЕЛИ
    # ============================================

    def create(self, data: Dict[str, Any]) -> int:
        """
        Создание пользователя
        data: {
            user_id, username, first_name, last_name, language_code, is_bot
        }
        """
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, language_code, is_bot)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data.get('user_id'),
                data.get('username'),
                data.get('first_name', ''),
                data.get('last_name'),
                data.get('language_code'),
                data.get('is_bot', 0)
            ))

            conn.commit()
            return data.get('user_id')

    def get(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение пользователя по user_id"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Получение пользователя по username"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            username = username.lstrip('@')
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Получение всех пользователей"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM users
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))

            return [dict(row) for row in cursor.fetchall()]

    def update(self, user_id: int, data: Dict[str, Any]) -> bool:
        """
        Обновление пользователя
        data: {
            username, first_name, last_name, language_code, is_bot
        }
        """
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            updates = []
            params = []

            fields = ['username', 'first_name', 'last_name', 'language_code', 'is_bot']
            for field in fields:
                if field in data:
                    updates.append(f"{field} = ?")
                    params.append(data[field])

            if not updates:
                return False

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(user_id)

            cursor.execute(f'''
                UPDATE users SET {', '.join(updates)} WHERE user_id = ?
            ''', params)

            conn.commit()
            return cursor.rowcount > 0

    def delete(self, user_id: int) -> bool:
        """Полное удаление пользователя"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('DELETE FROM chat_members WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM user_actions WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM downloads WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))

            conn.commit()
            return True

    def get_or_create(self, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Получить или создать пользователя"""
        user = self.get(user_id)
        if user:
            return user

        self.create({
            'user_id': user_id,
            'username': data.get('username'),
            'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name'),
            'language_code': data.get('language_code'),
            'is_bot': data.get('is_bot', 0)
        })

        return self.get(user_id)

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Поиск пользователей по user_id, username, first_name, last_name"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if query.isdigit():
                cursor.execute('''
                    SELECT * FROM users
                    WHERE user_id = ? OR username LIKE ? OR first_name LIKE ? OR last_name LIKE ?
                    LIMIT ?
                ''', (int(query), f'%{query}%', f'%{query}%', f'%{query}%', limit))
            else:
                cursor.execute('''
                    SELECT * FROM users
                    WHERE username LIKE ? OR first_name LIKE ? OR last_name LIKE ?
                    LIMIT ?
                ''', (f'%{query}%', f'%{query}%', f'%{query}%', limit))

            return [dict(row) for row in cursor.fetchall()]

    def count(self) -> int:
        """Общее количество пользователей"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM users')
            return cursor.fetchone()[0]

    # ============================================
    # УЧАСТНИКИ ЧАТОВ
    # ============================================

    def get_chat_members(self, chat_id: str, active_only: bool = True, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Получение участников чата"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = '''
                SELECT cm.*, u.username, u.first_name, u.last_name, u.is_bot
                FROM chat_members cm
                JOIN users u ON u.user_id = cm.user_id
                WHERE cm.chat_id = ?
            '''
            params = [chat_id]

            if active_only:
                query += ' AND cm.is_active = 1'

            query += ' ORDER BY cm.joined_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_chat_member(self, chat_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение участника чата"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT cm.*, u.username, u.first_name, u.last_name, u.is_bot
                FROM chat_members cm
                JOIN users u ON u.user_id = cm.user_id
                WHERE cm.chat_id = ? AND cm.user_id = ?
            ''', (chat_id, user_id))

            row = cursor.fetchone()
            return dict(row) if row else None

    def add_chat_member(self, chat_id: str, user_id: int) -> bool:
        """Добавление участника в чат"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR IGNORE INTO chat_members (chat_id, user_id)
                VALUES (?, ?)
            ''', (chat_id, user_id))

            conn.commit()
            return cursor.rowcount > 0

    def update_chat_member_last_seen(self, chat_id: str, user_id: int) -> bool:
        """Обновление last_seen участника"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE chat_members SET last_seen = CURRENT_TIMESTAMP
                WHERE chat_id = ? AND user_id = ?
            ''', (chat_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_chat_member_last_message(self, chat_id: str, user_id: int) -> bool:
        """Обновление last_message_at и увеличение total_messages"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE chat_members 
                SET last_message_at = CURRENT_TIMESTAMP,
                    total_messages = total_messages + 1
                WHERE chat_id = ? AND user_id = ?
            ''', (chat_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def remove_chat_member(self, chat_id: str, user_id: int, soft: bool = True) -> bool:
        """
        Удаление участника из чата
        soft=True - просто отключает is_active
        soft=False - удаляет полностью
        """
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            if soft:
                cursor.execute('''
                    UPDATE chat_members 
                    SET is_active = 0, left_at = CURRENT_TIMESTAMP
                    WHERE chat_id = ? AND user_id = ?
                ''', (chat_id, user_id))
            else:
                cursor.execute('''
                    DELETE FROM chat_members WHERE chat_id = ? AND user_id = ?
                ''', (chat_id, user_id))

            conn.commit()
            return cursor.rowcount > 0

    def get_chat_members_count(self, chat_id: str, active_only: bool = True) -> int:
        """Количество участников чата"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            query = 'SELECT COUNT(*) FROM chat_members WHERE chat_id = ?'
            params = [chat_id]

            if active_only:
                query += ' AND is_active = 1'

            cursor.execute(query, params)
            return cursor.fetchone()[0]
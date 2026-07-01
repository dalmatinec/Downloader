# settings.py
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from db import Database


class SettingsManager:
    """Управление настройками"""

    def __init__(self, db: Database):
        self.db = db

    def create(self, data: Dict[str, Any]) -> int:
        """
        Создание настройки
        data: {
            community_id, category, key, value, value_type, description
        }
        """
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO settings (community_id, category, key, value, value_type, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data.get('community_id'),
                data.get('category', 'general'),
                data.get('key'),
                data.get('value', ''),
                data.get('value_type', 'string'),
                data.get('description', '')
            ))

            conn.commit()
            return cursor.lastrowid

    def get(self, setting_id: int) -> Optional[Dict[str, Any]]:
        """Получение настройки по ID"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM settings WHERE id = ?', (setting_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return self._parse_value(dict(row))

    def get_by_key(self, community_id: str, category: str, key: str, active_only: bool = True) -> Optional[Dict[str, Any]]:
        """Получение настройки по community_id, category и key"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = 'SELECT * FROM settings WHERE community_id = ? AND category = ? AND key = ?'
            params = [community_id, category, key]

            if active_only:
                query += ' AND is_active = 1'

            cursor.execute(query, params)
            row = cursor.fetchone()

            if not row:
                return None

            return self._parse_value(dict(row))

    def get_by_category(self, community_id: str, category: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """Получение всех настроек категории"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = 'SELECT * FROM settings WHERE community_id = ? AND category = ?'
            params = [community_id, category]

            if active_only:
                query += ' AND is_active = 1'

            query += ' ORDER BY key ASC'

            cursor.execute(query, params)
            return [self._parse_value(dict(row)) for row in cursor.fetchall()]

    def get_all(self, community_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """Получение всех настроек сообщества"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = 'SELECT * FROM settings WHERE community_id = ?'
            params = [community_id]

            if active_only:
                query += ' AND is_active = 1'

            query += ' ORDER BY category ASC, key ASC'

            cursor.execute(query, params)
            return [self._parse_value(dict(row)) for row in cursor.fetchall()]

    def get_categories(self, community_id: str, active_only: bool = True) -> List[str]:
        """Получение всех категорий настроек"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            query = 'SELECT DISTINCT category FROM settings WHERE community_id = ?'
            params = [community_id]

            if active_only:
                query += ' AND is_active = 1'

            query += ' ORDER BY category ASC'

            cursor.execute(query, params)
            return [row[0] for row in cursor.fetchall()]

    def update(self, setting_id: int, data: Dict[str, Any]) -> bool:
        """Обновление настройки"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            updates = []
            params = []

            fields = ['category', 'key', 'value', 'value_type', 'description', 'is_active']
            for field in fields:
                if field in data:
                    updates.append(f"{field} = ?")
                    params.append(data[field])

            if not updates:
                return False

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(setting_id)

            cursor.execute(f'''
                UPDATE settings SET {', '.join(updates)} WHERE id = ?
            ''', params)

            conn.commit()
            return True

    def update_by_key(self, community_id: str, category: str, key: str, data: Dict[str, Any]) -> bool:
        """Обновление настройки по community_id, category и key"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            updates = []
            params = []

            fields = ['value', 'value_type', 'description', 'is_active']
            for field in fields:
                if field in data:
                    updates.append(f"{field} = ?")
                    params.append(data[field])

            if not updates:
                return False

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(community_id)
            params.append(category)
            params.append(key)

            cursor.execute(f'''
                UPDATE settings SET {', '.join(updates)} 
                WHERE community_id = ? AND category = ? AND key = ?
            ''', params)

            conn.commit()
            return cursor.rowcount > 0

    def delete(self, setting_id: int, soft: bool = True) -> bool:
        """
        Удаление настройки
        soft=True - просто отключает is_active
        soft=False - удаляет полностью
        """
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            if soft:
                cursor.execute('''
                    UPDATE settings SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (setting_id,))
            else:
                cursor.execute('DELETE FROM settings WHERE id = ?', (setting_id,))

            conn.commit()
            return True

    def delete_by_key(self, community_id: str, category: str, key: str, soft: bool = True) -> bool:
        """
        Удаление настройки по community_id, category и key
        soft=True - просто отключает is_active
        soft=False - удаляет полностью
        """
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            if soft:
                cursor.execute('''
                    UPDATE settings SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE community_id = ? AND category = ? AND key = ?
                ''', (community_id, category, key))
            else:
                cursor.execute('''
                    DELETE FROM settings WHERE community_id = ? AND category = ? AND key = ?
                ''', (community_id, category, key))

            conn.commit()
            return True

    def get_value(self, community_id: str, category: str, key: str, default: Any = None) -> Any:
        """Удобный метод получения значения настройки с преобразованием типа"""
        setting = self.get_by_key(community_id, category, key)
        if not setting:
            return default
        return setting.get('value')

    def set_value(self, community_id: str, category: str, key: str, value: Any, value_type: str = None) -> bool:
        """
        Удобный метод установки значения настройки
        Автоматически определяет value_type если не указан
        """
        if value_type is None:
            value_type = self._detect_type(value)

        str_value = self._serialize_value(value, value_type)

        existing = self.get_by_key(community_id, category, key, active_only=False)
        if existing:
            return self.update_by_key(community_id, category, key, {
                'value': str_value,
                'value_type': value_type
            })
        else:
            self.create({
                'community_id': community_id,
                'category': category,
                'key': key,
                'value': str_value,
                'value_type': value_type
            })
            return True

    def _parse_value(self, setting: Dict[str, Any]) -> Dict[str, Any]:
        """Преобразование значения из БД в нужный тип"""
        value_type = setting.get('value_type', 'string')
        value = setting.get('value', '')

        if value_type == 'integer':
            setting['value'] = int(value) if value else 0
        elif value_type == 'float':
            setting['value'] = float(value) if value else 0.0
        elif value_type == 'boolean':
            setting['value'] = value.lower() in ('true', '1', 'yes') if value else False
        elif value_type == 'json':
            setting['value'] = json.loads(value) if value else {}
        elif value_type == 'list':
            setting['value'] = json.loads(value) if value else []
        else:
            setting['value'] = value

        return setting

    def _detect_type(self, value: Any) -> str:
        """Определение типа значения"""
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'integer'
        elif isinstance(value, float):
            return 'float'
        elif isinstance(value, dict):
            return 'json'
        elif isinstance(value, list):
            return 'list'
        else:
            return 'string'

    def _serialize_value(self, value: Any, value_type: str) -> str:
        """Преобразование значения в строку для хранения"""
        if value_type == 'json' or value_type == 'list':
            return json.dumps(value)
        elif value_type == 'boolean':
            return str(value).lower()
        else:
            return str(value)
# contents.py
import sqlite3
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from db import Database


class ContentManager:
    """Управление контентом"""

    def __init__(self, db: Database):
        self.db = db

    def create(self, data: Dict[str, Any]) -> str:
        """Создание контента"""
        content_id = str(uuid.uuid4())

        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO content (
                    id, title, description, content_type_id, file_id,
                    url, text_content, order_num, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                content_id,
                data.get('title', ''),
                data.get('description', ''),
                data.get('content_type_id'),
                data.get('file_id'),
                data.get('url'),
                data.get('text_content'),
                data.get('order_num', 0),
                json.dumps(data.get('metadata', {}))
            ))

            # Добавляем теги если есть
            tags = data.get('tags', [])
            for tag_name in tags:
                tag_id = self._get_or_create_tag(cursor, tag_name)
                cursor.execute('''
                    INSERT OR IGNORE INTO content_tag_relations (content_id, tag_id)
                    VALUES (?, ?)
                ''', (content_id, tag_id))

            conn.commit()
            return content_id

    def get(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Получение контента по ID"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT c.*, ct.name as type_name, f.telegram_file_id, f.file_name, f.mime_type, f.file_size
                FROM content c
                LEFT JOIN content_types ct ON c.content_type_id = ct.id
                LEFT JOIN files f ON c.file_id = f.id
                WHERE c.id = ?
            ''', (content_id,))

            row = cursor.fetchone()
            if not row:
                return None

            result = dict(row)
            result['metadata'] = json.loads(result['metadata'])

            cursor.execute('''
                SELECT t.name FROM content_tags t
                JOIN content_tag_relations r ON r.tag_id = t.id
                WHERE r.content_id = ?
            ''', (content_id,))
            result['tags'] = [row[0] for row in cursor.fetchall()]

            return result

    def get_all(self, active_only: bool = True, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Получение всех контентов с сортировкой по order_num"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = '''
                SELECT c.*, ct.name as type_name, f.telegram_file_id, f.file_name, f.mime_type, f.file_size
                FROM content c
                LEFT JOIN content_types ct ON c.content_type_id = ct.id
                LEFT JOIN files f ON c.file_id = f.id
            '''

            params = []
            if active_only:
                query += ' WHERE c.is_active = 1'

            query += ' ORDER BY c.order_num ASC, c.created_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])

            cursor.execute(query, params)
            results = []

            for row in cursor.fetchall():
                result = dict(row)
                result['metadata'] = json.loads(result['metadata'])

                cursor.execute('''
                    SELECT t.name FROM content_tags t
                    JOIN content_tag_relations r ON r.tag_id = t.id
                    WHERE r.content_id = ?
                ''', (result['id'],))
                result['tags'] = [r[0] for r in cursor.fetchall()]

                results.append(result)

            return results

    def update(self, content_id: str, data: Dict[str, Any]) -> bool:
        """Обновление контента"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            updates = []
            params = []

            fields = ['title', 'description', 'content_type_id', 'file_id', 'url', 'text_content', 'order_num', 'is_active']
            for field in fields:
                if field in data:
                    updates.append(f"{field} = ?")
                    params.append(data[field])

            if 'metadata' in data:
                updates.append("metadata = ?")
                params.append(json.dumps(data['metadata']))

            if not updates:
                return False

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(content_id)

            cursor.execute(f'''
                UPDATE content SET {', '.join(updates)} WHERE id = ?
            ''', params)

            # Обновляем теги
            if 'tags' in data:
                cursor.execute('DELETE FROM content_tag_relations WHERE content_id = ?', (content_id,))
                for tag_name in data['tags']:
                    tag_id = self._get_or_create_tag(cursor, tag_name)
                    cursor.execute('''
                        INSERT OR IGNORE INTO content_tag_relations (content_id, tag_id)
                        VALUES (?, ?)
                    ''', (content_id, tag_id))

            conn.commit()
            return True

    def delete(self, content_id: str, soft: bool = True) -> bool:
        """Удаление контента"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            if soft:
                cursor.execute('''
                    UPDATE content SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (content_id,))
            else:
                cursor.execute('DELETE FROM content_tag_relations WHERE content_id = ?', (content_id,))
                cursor.execute('DELETE FROM downloads WHERE content_id = ?', (content_id,))
                cursor.execute('DELETE FROM content WHERE id = ?', (content_id,))

            conn.commit()
            return True

    def view(self, content_id: str) -> bool:
        """Увеличение просмотров"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE content SET views = views + 1
                WHERE id = ? AND is_active = 1
            ''', (content_id,))
            conn.commit()
            return cursor.rowcount > 0

    def download(self, content_id: str, user_id: int, chat_id: str) -> bool:
        """Скачивание контента"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT is_active FROM content WHERE id = ?', (content_id,))
            row = cursor.fetchone()
            if not row or row[0] != 1:
                return False

            cursor.execute('''
                UPDATE content SET downloads = downloads + 1
                WHERE id = ?
            ''', (content_id,))

            cursor.execute('''
                INSERT INTO downloads (content_id, user_id, chat_id)
                VALUES (?, ?, ?)
            ''', (content_id, user_id, chat_id))

            conn.commit()
            return True

    def get_by_type(self, content_type_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """Получение контента по типу"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = '''
                SELECT c.*, ct.name as type_name, f.telegram_file_id, f.file_name, f.mime_type, f.file_size
                FROM content c
                LEFT JOIN content_types ct ON c.content_type_id = ct.id
                LEFT JOIN files f ON c.file_id = f.id
                WHERE c.content_type_id = ?
            '''

            params = [content_type_id]
            if active_only:
                query += ' AND c.is_active = 1'

            query += ' ORDER BY c.order_num ASC'

            cursor.execute(query, params)
            results = []

            for row in cursor.fetchall():
                result = dict(row)
                result['metadata'] = json.loads(result['metadata'])
                results.append(result)

            return results

    def get_by_tag(self, tag_name: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """Получение контента по тегу"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = '''
                SELECT c.*, ct.name as type_name, f.telegram_file_id, f.file_name, f.mime_type, f.file_size
                FROM content c
                LEFT JOIN content_types ct ON c.content_type_id = ct.id
                LEFT JOIN files f ON c.file_id = f.id
                JOIN content_tag_relations r ON r.content_id = c.id
                JOIN content_tags t ON t.id = r.tag_id
                WHERE t.name = ?
            '''

            params = [tag_name]
            if active_only:
                query += ' AND c.is_active = 1'

            query += ' ORDER BY c.order_num ASC'

            cursor.execute(query, params)
            results = []

            for row in cursor.fetchall():
                result = dict(row)
                result['metadata'] = json.loads(result['metadata'])
                results.append(result)

            return results

    def get_downloads_stats(self, content_id: str) -> int:
        """Количество скачиваний контента"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT downloads FROM content WHERE id = ?', (content_id,))
            row = cursor.fetchone()
            return row[0] if row else 0

    def get_download_history(self, content_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """История скачиваний контента"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT d.*, u.username, u.first_name, u.last_name
                FROM downloads d
                JOIN users u ON u.user_id = d.user_id
                WHERE d.content_id = ?
                ORDER BY d.downloaded_at DESC
                LIMIT ?
            ''', (content_id, limit))
            return [dict(row) for row in cursor.fetchall()]

    def _get_or_create_tag(self, cursor: sqlite3.Cursor, tag_name: str) -> str:
        """Получить или создать тег (внутри текущей транзакции)"""
        cursor.execute('SELECT id FROM content_tags WHERE name = ?', (tag_name,))
        row = cursor.fetchone()
        if row:
            return row[0]

        tag_id = str(uuid.uuid4())
        cursor.execute('INSERT INTO content_tags (id, name) VALUES (?, ?)', (tag_id, tag_name))
        return tag_id

    def get_content_types(self) -> List[Dict[str, Any]]:
        """Получение всех типов контента"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM content_types ORDER BY name')
            return [dict(row) for row in cursor.fetchall()]

    def get_type_by_id(self, type_id: str) -> Optional[Dict[str, Any]]:
        """Получение типа контента по ID"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM content_types WHERE id = ?', (type_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
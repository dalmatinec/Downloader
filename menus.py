# menus.py
import sqlite3
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from db import Database


class MenuManager:
    """Управление меню и кнопками"""

    def __init__(self, db: Database):
        self.db = db

    # ============================================
    # МЕНЮ
    # ============================================

    def create_menu(self, data: Dict[str, Any]) -> str:
        """
        Создание меню
        data: {
            community_id, name, is_main, order_num
        }
        """
        menu_id = str(uuid.uuid4())

        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO menus (id, community_id, name, is_main, order_num)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                menu_id,
                data.get('community_id'),
                data.get('name', ''),
                data.get('is_main', 0),
                data.get('order_num', 0)
            ))

            conn.commit()
            return menu_id

    def get_menu(self, menu_id: str) -> Optional[Dict[str, Any]]:
        """Получение меню по ID"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM menus WHERE id = ?
            ''', (menu_id,))

            row = cursor.fetchone()
            return dict(row) if row else None

    def get_menus(self, community_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """Получение всех меню сообщества"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = 'SELECT * FROM menus WHERE community_id = ?'
            params = [community_id]

            if active_only:
                query += ' AND is_active = 1'

            query += ' ORDER BY is_main DESC, order_num ASC'

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_main_menu(self, community_id: str) -> Optional[Dict[str, Any]]:
        """Получение главного меню сообщества"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM menus
                WHERE community_id = ? AND is_main = 1 AND is_active = 1
                LIMIT 1
            ''', (community_id,))

            row = cursor.fetchone()
            return dict(row) if row else None

    def update_menu(self, menu_id: str, data: Dict[str, Any]) -> bool:
        """Обновление меню"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            updates = []
            params = []

            fields = ['name', 'is_main', 'order_num', 'is_active']
            for field in fields:
                if field in data:
                    updates.append(f"{field} = ?")
                    params.append(data[field])

            if not updates:
                return False

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(menu_id)

            cursor.execute(f'''
                UPDATE menus SET {', '.join(updates)} WHERE id = ?
            ''', params)

            conn.commit()
            return True

    def delete_menu(self, menu_id: str, soft: bool = True) -> bool:
        """
        Удаление меню
        soft=True - просто отключает is_active
        soft=False - удаляет полностью с кнопками
        """
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            if soft:
                cursor.execute('''
                    UPDATE menus SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (menu_id,))
            else:
                cursor.execute('DELETE FROM buttons WHERE menu_id = ?', (menu_id,))
                cursor.execute('DELETE FROM menus WHERE id = ?', (menu_id,))

            conn.commit()
            return True

    # ============================================
    # КНОПКИ
    # ============================================

    def create_button(self, data: Dict[str, Any]) -> str:
        """
        Создание кнопки
        data: {
            menu_id, parent_button_id, text, action_type_id,
            action_data, order_num, row_num
        }
        """
        button_id = str(uuid.uuid4())

        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO buttons (
                    id, menu_id, parent_button_id, text,
                    action_type_id, action_data, order_num, row_num
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                button_id,
                data.get('menu_id'),
                data.get('parent_button_id'),
                data.get('text', ''),
                data.get('action_type_id'),
                json.dumps(data.get('action_data', {})),
                data.get('order_num', 0),
                data.get('row_num', 0)
            ))

            conn.commit()
            return button_id

    def get_button(self, button_id: str) -> Optional[Dict[str, Any]]:
        """Получение кнопки по ID"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT b.*, ba.name as action_name, ba.description as action_description
                FROM buttons b
                LEFT JOIN button_actions ba ON b.action_type_id = ba.id
                WHERE b.id = ?
            ''', (button_id,))

            row = cursor.fetchone()
            if not row:
                return None

            result = dict(row)
            result['action_data'] = json.loads(result['action_data'])
            return result

    def get_menu_buttons(self, menu_id: str, active_only: bool = True, parent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Получение кнопок меню
        parent_id=None - корневые кнопки
        parent_id='...' - дочерние кнопки
        """
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = '''
                SELECT b.*, ba.name as action_name
                FROM buttons b
                LEFT JOIN button_actions ba ON b.action_type_id = ba.id
                WHERE b.menu_id = ?
            '''
            params = [menu_id]

            if parent_id is None:
                query += ' AND b.parent_button_id IS NULL'
            else:
                query += ' AND b.parent_button_id = ?'
                params.append(parent_id)

            if active_only:
                query += ' AND b.is_active = 1'

            query += ' ORDER BY b.row_num ASC, b.order_num ASC'

            cursor.execute(query, params)

            results = []
            for row in cursor.fetchall():
                result = dict(row)
                result['action_data'] = json.loads(result['action_data'])
                results.append(result)

            return results

    def get_all_menu_buttons(self, menu_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """Получение всех кнопок меню (всех уровней)"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = '''
                SELECT b.*, ba.name as action_name
                FROM buttons b
                LEFT JOIN button_actions ba ON b.action_type_id = ba.id
                WHERE b.menu_id = ?
            '''
            params = [menu_id]

            if active_only:
                query += ' AND b.is_active = 1'

            query += ' ORDER BY b.row_num ASC, b.order_num ASC'

            cursor.execute(query, params)

            results = []
            for row in cursor.fetchall():
                result = dict(row)
                result['action_data'] = json.loads(result['action_data'])
                results.append(result)

            return results

    def get_button_children(self, parent_button_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """Получение дочерних кнопок"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = '''
                SELECT b.*, ba.name as action_name
                FROM buttons b
                LEFT JOIN button_actions ba ON b.action_type_id = ba.id
                WHERE b.parent_button_id = ?
            '''
            params = [parent_button_id]

            if active_only:
                query += ' AND b.is_active = 1'

            query += ' ORDER BY b.row_num ASC, b.order_num ASC'

            cursor.execute(query, params)

            results = []
            for row in cursor.fetchall():
                result = dict(row)
                result['action_data'] = json.loads(result['action_data'])
                results.append(result)

            return results

    def update_button(self, button_id: str, data: Dict[str, Any]) -> bool:
        """Обновление кнопки"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            updates = []
            params = []

            fields = ['text', 'action_type_id', 'order_num', 'row_num', 'is_active', 'parent_button_id']
            for field in fields:
                if field in data:
                    updates.append(f"{field} = ?")
                    params.append(data[field])

            if 'action_data' in data:
                updates.append("action_data = ?")
                params.append(json.dumps(data['action_data']))

            if not updates:
                return False

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(button_id)

            cursor.execute(f'''
                UPDATE buttons SET {', '.join(updates)} WHERE id = ?
            ''', params)

            conn.commit()
            return True

    def delete_button(self, button_id: str, soft: bool = True, cascade: bool = False) -> bool:
        """
        Удаление кнопки
        soft=True - просто отключает is_active
        soft=False - удаляет полностью
        cascade=True - удаляет дочерние кнопки
        """
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            if soft:
                cursor.execute('''
                    UPDATE buttons SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (button_id,))
            else:
                if cascade:
                    cursor.execute('DELETE FROM buttons WHERE parent_button_id = ?', (button_id,))
                else:
                    cursor.execute('SELECT COUNT(*) FROM buttons WHERE parent_button_id = ?', (button_id,))
                    count = cursor.fetchone()[0]
                    if count > 0:
                        conn.commit()
                        return False

                cursor.execute('DELETE FROM buttons WHERE id = ?', (button_id,))

            conn.commit()
            return True

    def reorder_buttons(self, button_ids: List[str]) -> bool:
        """
        Обновление порядка кнопок (меняет только order_num)
        button_ids - список ID кнопок в нужном порядке
        """
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            for index, button_id in enumerate(button_ids):
                cursor.execute('''
                    UPDATE buttons SET order_num = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (index, button_id))

            conn.commit()
            return True

    def update_button_row(self, button_id: str, row_num: int) -> bool:
        """Обновление ряда кнопки"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE buttons SET row_num = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (row_num, button_id))
            conn.commit()
            return True

    # ============================================
    # ТИПЫ ДЕЙСТВИЙ
    # ============================================

    def get_action_types(self) -> List[Dict[str, Any]]:
        """Получение всех типов действий"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM button_actions ORDER BY name')
            return [dict(row) for row in cursor.fetchall()]

    def get_action_type(self, action_type_id: str) -> Optional[Dict[str, Any]]:
        """Получение типа действия по ID"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM button_actions WHERE id = ?', (action_type_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_action_type(self, data: Dict[str, Any]) -> str:
        """Создание типа действия"""
        action_id = str(uuid.uuid4())

        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO button_actions (id, name, description)
                VALUES (?, ?, ?)
            ''', (
                action_id,
                data.get('name', ''),
                data.get('description', '')
            ))

            conn.commit()
            return action_id
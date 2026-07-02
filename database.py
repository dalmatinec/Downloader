import aiosqlite
from typing import Optional, List, Dict, Any

import config


class Database:
    def __init__(self):
        self.db_name = config.DB_NAME

    async def init_db(self):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("PRAGMA foreign_keys = ON")

            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER DEFAULT 0,
                    book_downloads INTEGER DEFAULT 0,
                    is_banned INTEGER DEFAULT 0,
                    is_muted INTEGER DEFAULT 0,
                    warn_count INTEGER DEFAULT 0
                )
            ''')

            await db.execute('''
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    description TEXT,
                    poster_file_id TEXT,
                    book_file_id TEXT,
                    file_type TEXT,
                    downloads INTEGER DEFAULT 0
                )
            ''')

            await db.execute('''
                CREATE TABLE IF NOT EXISTS book_downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    book_id INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE
                )
            ''')

            await db.execute('''
                CREATE TABLE IF NOT EXISTS triggers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keywords TEXT NOT NULL,
                    action TEXT NOT NULL,
                    value TEXT
                )
            ''')

            await db.execute('''
                CREATE TABLE IF NOT EXISTS punishments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    reason TEXT,
                    issued_by INTEGER,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')

            await db.execute('''
                CREATE TABLE IF NOT EXISTS donators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    username TEXT,
                    comment TEXT
                )
            ''')

            await db.execute('''
                CREATE TABLE IF NOT EXISTS broadcasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    title TEXT,
                    text TEXT,
                    button_text TEXT,
                    button_url TEXT,
                    image_file_id TEXT,
                    forward_message_id INTEGER,
                    forward_chat_id INTEGER,
                    sent_count INTEGER NOT NULL DEFAULT 0,
                    failed_count INTEGER NOT NULL DEFAULT 0,
                    created_by INTEGER
                )
            ''')

            await db.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')

            await db.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL
                )
            ''')

            await db.commit()

    ####################################################################
    # ПОЛЬЗОВАТЕЛИ
    ####################################################################

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE telegram_id = ?",
                (telegram_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def add_user(self, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None) -> Optional[int]:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                """INSERT OR IGNORE INTO users (telegram_id, username, first_name, last_name)
                   VALUES (?, ?, ?, ?)""",
                (telegram_id, username, first_name, last_name)
            )
            await db.commit()
            if cursor.rowcount == 0:
                return None
            return cursor.lastrowid

    async def update_user_activity(self, telegram_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                "UPDATE users SET message_count = message_count + 1 WHERE telegram_id = ?",
                (telegram_id,)
            )
            await db.commit()

    async def update_user_downloads(self, telegram_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                "UPDATE users SET book_downloads = book_downloads + 1 WHERE telegram_id = ?",
                (telegram_id,)
            )
            await db.commit()

    async def update_user_warn_count(self, telegram_id: int, count: int):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                "UPDATE users SET warn_count = ? WHERE telegram_id = ?",
                (count, telegram_id)
            )
            await db.commit()

    async def set_user_banned(self, telegram_id: int, banned: bool):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                "UPDATE users SET is_banned = ? WHERE telegram_id = ?",
                (1 if banned else 0, telegram_id)
            )
            await db.commit()

    async def set_user_muted(self, telegram_id: int, muted: bool):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                "UPDATE users SET is_muted = ? WHERE telegram_id = ?",
                (1 if muted else 0, telegram_id)
            )
            await db.commit()

    async def get_user_count(self) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_banned_users(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE is_banned = 1 ORDER BY id DESC"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_muted_users(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE is_muted = 1 ORDER BY id DESC"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


    # КНИГИ
    async def get_book_by_id(self, book_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM books WHERE id = ?", (book_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_all_books(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM books ORDER BY id DESC")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def add_book(self, title: str, author: str, description: str = None, poster_file_id: str = None, book_file_id: str = None, file_type: str = None) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                "INSERT INTO books (title, author, description, poster_file_id, book_file_id, file_type) VALUES (?, ?, ?, ?, ?, ?)",
                (title, author, description, poster_file_id, book_file_id, file_type)
            )
            await db.commit()
            return cursor.lastrowid

    async def update_book(self, book_id: int, title: str = None, author: str = None, description: str = None, poster_file_id: str = None, book_file_id: str = None, file_type: str = None):
        async with aiosqlite.connect(self.db_name) as db:
            updates, params = [], []
            if title is not None: updates.append("title = ?"); params.append(title)
            if author is not None: updates.append("author = ?"); params.append(author)
            if description is not None: updates.append("description = ?"); params.append(description)
            if poster_file_id is not None: updates.append("poster_file_id = ?"); params.append(poster_file_id)
            if book_file_id is not None: updates.append("book_file_id = ?"); params.append(book_file_id)
            if file_type is not None: updates.append("file_type = ?"); params.append(file_type)
            if updates:
                params.append(book_id)
                await db.execute(f"UPDATE books SET {', '.join(updates)} WHERE id = ?", params)
                await db.commit()

    async def delete_book(self, book_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("DELETE FROM books WHERE id = ?", (book_id,))
            await db.commit()

    async def increment_book_downloads(self, book_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("UPDATE books SET downloads = downloads + 1 WHERE id = ?", (book_id,))
            await db.commit()

    # ЗАГРУЗКИ КНИГ
    async def add_book_download(self, user_id: int, book_id: int) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("INSERT INTO book_downloads (user_id, book_id) VALUES (?, ?)", (user_id, book_id))
            await db.commit()
            return cursor.lastrowid

    async def has_downloaded_book(self, user_id: int, book_id: int) -> bool:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("SELECT 1 FROM book_downloads WHERE user_id = ? AND book_id = ?", (user_id, book_id))
            return await cursor.fetchone() is not None

    async def get_user_book_downloads(self, user_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM book_downloads WHERE user_id = ?", (user_id,))
            return [dict(row) for row in await cursor.fetchall()]

    async def get_book_download_count(self, book_id: int) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM book_downloads WHERE book_id = ?", (book_id,))
            row = await cursor.fetchone()
            return row[0] if row else 0

    # ТРИГГЕРЫ
    async def get_trigger_by_id(self, trigger_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM triggers WHERE id = ?", (trigger_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_all_triggers(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM triggers ORDER BY id DESC")
            return [dict(row) for row in await cursor.fetchall()]

    async def add_trigger(self, keywords: str, action: str, value: str = None) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("INSERT INTO triggers (keywords, action, value) VALUES (?, ?, ?)", (keywords, action, value))
            await db.commit()
            return cursor.lastrowid

    async def update_trigger(self, trigger_id: int, keywords: str = None, action: str = None, value: str = None):
        async with aiosqlite.connect(self.db_name) as db:
            updates, params = [], []
            if keywords is not None: updates.append("keywords = ?"); params.append(keywords)
            if action is not None: updates.append("action = ?"); params.append(action)
            if value is not None: updates.append("value = ?"); params.append(value)
            if updates:
                params.append(trigger_id)
                await db.execute(f"UPDATE triggers SET {', '.join(updates)} WHERE id = ?", params)
                await db.commit()

    async def delete_trigger(self, trigger_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("DELETE FROM triggers WHERE id = ?", (trigger_id,))
            await db.commit()

    # АДМИНИСТРАТОРЫ
    async def get_admin_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM admins WHERE telegram_id = ?", (telegram_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_all_admins(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM admins")
            return [dict(row) for row in await cursor.fetchall()]

    async def add_admin(self, telegram_id: int) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("INSERT INTO admins (telegram_id) VALUES (?)", (telegram_id,))
            await db.commit()
            return cursor.lastrowid

    async def remove_admin(self, telegram_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("DELETE FROM admins WHERE telegram_id = ?", (telegram_id,))
            await db.commit()

    # НАКАЗАНИЯ
    async def add_punishment(self, user_id: int, p_type: str, reason: str = None, issued_by: int = None, end_time: str = None) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                "INSERT INTO punishments (user_id, type, reason, issued_by, end_time) VALUES (?, ?, ?, ?, ?)",
                (user_id, p_type, reason, issued_by, end_time)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_active_punishments(self, user_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM punishments WHERE user_id = ? AND (end_time IS NULL OR end_time > datetime('now')) ORDER BY start_time DESC",
                (user_id,)
            )
            return [dict(row) for row in await cursor.fetchall()]

    async def get_punishment_history(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM punishments WHERE user_id = ? ORDER BY start_time DESC LIMIT ?", (user_id, limit))
            return [dict(row) for row in await cursor.fetchall()]

    async def delete_punishment(self, punishment_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("DELETE FROM punishments WHERE id = ?", (punishment_id,))
            await db.commit()

    async def get_punishment_by_id(self, punishment_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM punishments WHERE id = ?", (punishment_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    # ЛОГИ
    async def add_log(self, user_id: int, action: str, details: str = None) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("INSERT INTO logs (user_id, action, details) VALUES (?, ?, ?)", (user_id, action, details))
            await db.commit()
            return cursor.lastrowid

    async def get_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,))
            return [dict(row) for row in await cursor.fetchall()]

    # ДОНАТЕРЫ
    async def get_all_donators(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM donators ORDER BY id DESC")
            return [dict(row) for row in await cursor.fetchall()]

    async def add_donator(self, name: str, username: str = None, comment: str = None) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("INSERT INTO donators (name, username, comment) VALUES (?, ?, ?)", (name, username, comment))
            await db.commit()
            return cursor.lastrowid

    async def remove_donator(self, donator_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("DELETE FROM donators WHERE id = ?", (donator_id,))
            await db.commit()

    # РАССЫЛКИ
    async def add_broadcast(self, broadcast_data: Dict[str, Any]) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                "INSERT INTO broadcasts (type, title, text, button_text, button_url, image_file_id, forward_message_id, forward_chat_id, sent_count, failed_count, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (broadcast_data.get('type'), broadcast_data.get('title'), broadcast_data.get('text'), broadcast_data.get('button_text'), broadcast_data.get('button_url'), broadcast_data.get('image_file_id'), broadcast_data.get('forward_message_id'), broadcast_data.get('forward_chat_id'), broadcast_data.get('sent_count', 0), broadcast_data.get('failed_count', 0), broadcast_data.get('created_by'))
            )
            await db.commit()
            return cursor.lastrowid

    async def get_all_broadcasts(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM broadcasts ORDER BY id DESC")
            return [dict(row) for row in await cursor.fetchall()]

    async def get_broadcast_by_id(self, broadcast_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM broadcasts WHERE id = ?", (broadcast_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_broadcast_stats(self, broadcast_id: int, sent_count: int, failed_count: int):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("UPDATE broadcasts SET sent_count = ?, failed_count = ? WHERE id = ?", (sent_count, failed_count, broadcast_id))
            await db.commit()

    async def delete_broadcast(self, broadcast_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("DELETE FROM broadcasts WHERE id = ?", (broadcast_id,))
            await db.commit()



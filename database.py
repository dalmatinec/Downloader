import aiosqlite
from typing import Optional, List, Dict, Any


class Database:
    def __init__(self):
        self.db_name = "bot_database.db"

    async def init_db(self):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("PRAGMA foreign_keys = ON")

            # Пользователи
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT DEFAULT '',
                    downloads INTEGER DEFAULT 0,
                    is_blocked INTEGER DEFAULT 0,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Книги
            await db.execute('''
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    description TEXT,
                    poster_file_id TEXT,
                    book_file_id TEXT,
                    downloads INTEGER DEFAULT 0
                )
            ''')

            # Донатеры
            await db.execute('''
                CREATE TABLE IF NOT EXISTS donators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    username TEXT DEFAULT ''
                )
            ''')

            # Рассылки
            await db.execute('''
                CREATE TABLE IF NOT EXISTS broadcasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    sent INTEGER DEFAULT 0,
                    failed INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            await db.commit()

    # === USERS ===
    async def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def add_user(self, telegram_id: int, username: str = "") -> None:
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                """
                INSERT INTO users (telegram_id, username)
                VALUES (?, ?)
                ON CONFLICT(telegram_id)
                DO UPDATE SET username = excluded.username
                """,
                (telegram_id, username)
            )
            await db.commit()

    async def add_download(self, telegram_id: int) -> None:
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                "UPDATE users SET downloads = downloads + 1 WHERE telegram_id = ?",
                (telegram_id,)
            )
            await db.commit()

    async def set_blocked(self, telegram_id: int, blocked: bool) -> None:
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                "UPDATE users SET is_blocked = ? WHERE telegram_id = ?",
                (1 if blocked else 0, telegram_id)
            )
            await db.commit()

    async def get_all_users(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_active_users(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE is_blocked = 0")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_users_count(self) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_blocked_count(self) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE is_blocked = 1")
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_today_users_count(self) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM users WHERE DATE(joined_at) = DATE('now')"
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_week_users_count(self) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM users WHERE joined_at >= DATE('now', '-7 days')"
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_month_users_count(self) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM users WHERE joined_at >= DATE('now', '-30 days')"
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    # === BOOKS ===
    async def get_book(self, book_id: int) -> Optional[Dict[str, Any]]:
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

    async def add_book(self, title: str, author: str, description: str, poster_file_id: str, book_file_id: str) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                "INSERT INTO books (title, author, description, poster_file_id, book_file_id) VALUES (?, ?, ?, ?, ?)",
                (title, author, description, poster_file_id, book_file_id)
            )
            await db.commit()
            return cursor.lastrowid

    async def delete_book(self, book_id: int) -> None:
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("DELETE FROM books WHERE id = ?", (book_id,))
            await db.commit()

    async def increment_book_downloads(self, book_id: int) -> None:
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                "UPDATE books SET downloads = downloads + 1 WHERE id = ?",
                (book_id,)
            )
            await db.commit()

    async def get_books_count(self) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM books")
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_total_downloads(self) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("SELECT SUM(downloads) FROM books")
            row = await cursor.fetchone()
            return row[0] if row else 0

    # === DONATORS ===
    async def get_all_donators(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM donators ORDER BY id DESC")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def add_donator(self, name: str, username: str = "") -> int:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                "INSERT INTO donators (name, username) VALUES (?, ?)",
                (name, username)
            )
            await db.commit()
            return cursor.lastrowid

    async def delete_donator(self, donator_id: int) -> None:
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("DELETE FROM donators WHERE id = ?", (donator_id,))
            await db.commit()

    # === BROADCASTS ===
    async def add_broadcast(self, broadcast_type: str, sent: int, failed: int) -> None:
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                "INSERT INTO broadcasts (type, sent, failed) VALUES (?, ?, ?)",
                (broadcast_type, sent, failed)
            )
            await db.commit()
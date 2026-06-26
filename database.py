import sqlite3
from datetime import datetime
from config import DATABASE_NAME


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Пользователи
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TEXT,
            downloads INTEGER DEFAULT 0,
            supporter INTEGER DEFAULT 0,
            supporter_until TEXT
        )
        """)

        # Статистика
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS statistics (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            total_users INTEGER DEFAULT 0,
            total_downloads INTEGER DEFAULT 0,
            downloads_today INTEGER DEFAULT 0,
            new_users_today INTEGER DEFAULT 0,
            last_reset TEXT
        )
        """)

        # Проверяем наличие строки статистики
        self.cursor.execute("SELECT id FROM statistics WHERE id = 1")

        if not self.cursor.fetchone():
            self.cursor.execute("""
            INSERT INTO statistics(
                id,
                total_users,
                total_downloads,
                downloads_today,
                new_users_today,
                last_reset
            )
            VALUES(1, 0, 0, 0, 0, ?)
            """, (datetime.now().strftime("%Y-%m-%d"),))

        self.conn.commit()

    # ==========================
    # Пользователи
    # ==========================

    def add_user(self, user):
        self.cursor.execute(
            "SELECT user_id FROM users WHERE user_id = ?",
            (user.id,)
        )

        if self.cursor.fetchone():
            return False

        self.cursor.execute("""
        INSERT INTO users(
            user_id,
            username,
            first_name,
            joined_at
        )
        VALUES (?, ?, ?, ?)
        """, (
            user.id,
            user.username,
            user.first_name,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        self.cursor.execute("""
        UPDATE statistics
        SET total_users = total_users + 1,
            new_users_today = new_users_today + 1
        WHERE id = 1
        """)

        self.conn.commit()
        return True

    def get_user(self, user_id):
        self.cursor.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        )
        return self.cursor.fetchone()

    def get_all_users(self):
        self.cursor.execute(
            "SELECT user_id FROM users"
        )
        return self.cursor.fetchall()

    # ==========================
    # Подписка
    # ==========================

    def issue_subscription(self, user_id, until):
        self.cursor.execute("""
        UPDATE users
        SET supporter = 1,
            supporter_until = ?
        WHERE user_id = ?
        """, (until, user_id))

        self.conn.commit()

    def issue_lifetime(self, user_id):
        self.cursor.execute("""
        UPDATE users
        SET supporter = 1,
            supporter_until = 'lifetime'
        WHERE user_id = ?
        """, (user_id,))

        self.conn.commit()

    def check_subscription(self, user_id):
        user = self.get_user(user_id)

        if not user:
            return False

        if user["supporter"] == 0:
            return False

        if user["supporter_until"] == "lifetime":
            return True

        expire = datetime.strptime(
            user["supporter_until"],
            "%Y-%m-%d %H:%M:%S"
        )

        if datetime.now() >= expire:

            self.cursor.execute("""
            UPDATE users
            SET supporter = 0,
                supporter_until = NULL
            WHERE user_id = ?
            """, (user_id,))

            self.conn.commit()

            return False

        return True

    # ==========================
    # Скачивания
    # ==========================

    def add_download(self, user_id):
        self.cursor.execute("""
        UPDATE users
        SET downloads = downloads + 1
        WHERE user_id = ?
        """, (user_id,))

        self.cursor.execute("""
        UPDATE statistics
        SET total_downloads = total_downloads + 1,
            downloads_today = downloads_today + 1
        WHERE id = 1
        """)

        self.conn.commit()

    # ==========================
    # Статистика
    # ==========================

    def get_statistics(self):
        self.cursor.execute("""
        SELECT * FROM statistics
        WHERE id = 1
        """)
        return self.cursor.fetchone()

    def supported_users(self):
        self.cursor.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE supporter = 1
        """)
        return self.cursor.fetchone()[0]

    def total_users(self):
        self.cursor.execute("""
        SELECT COUNT(*)
        FROM users
        """)
        return self.cursor.fetchone()[0]

    def total_downloads(self):
        self.cursor.execute("""
        SELECT SUM(downloads)
        FROM users
        """)

        result = self.cursor.fetchone()[0]

        if result is None:
            return 0

        return result

    def reset_daily_statistics(self):
        today = datetime.now().strftime("%Y-%m-%d")

        self.cursor.execute("""
        SELECT last_reset
        FROM statistics
        WHERE id = 1
        """)

        last = self.cursor.fetchone()["last_reset"]

        if last != today:

            self.cursor.execute("""
            UPDATE statistics
            SET downloads_today = 0,
                new_users_today = 0,
                last_reset = ?
            WHERE id = 1
            """, (today,))

            self.conn.commit()

    # ==========================
    # Админ
    # ==========================

    def user_exists(self, user_id):
        self.cursor.execute("""
        SELECT user_id
        FROM users
        WHERE user_id = ?
        """, (user_id,))

        return self.cursor.fetchone() is not None

    def remove_expired_subscriptions(self):
        self.cursor.execute("""
        SELECT user_id, supporter_until
        FROM users
        WHERE supporter = 1
        """)

        users = self.cursor.fetchall()

        now = datetime.now()

        for user in users:

            if user["supporter_until"] == "lifetime":
                continue

            expire = datetime.strptime(
                user["supporter_until"],
                "%Y-%m-%d %H:%M:%S"
            )

            if now >= expire:

                self.cursor.execute("""
                UPDATE users
                SET supporter = 0,
                    supporter_until = NULL
                WHERE user_id = ?
                """, (user["user_id"],))

        self.conn.commit()

    # ==========================
    # Закрытие базы
    # ==========================

    def close(self):
        self.conn.close()


db = Database()
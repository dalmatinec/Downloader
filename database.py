import sqlite3
import logging
from datetime import datetime, timedelta
from config import DATABASE_NAME, LIFETIME

logger = logging.getLogger(__name__)


def get_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            registered_at TEXT DEFAULT (datetime('now')),
            downloads INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            sub_type TEXT,
            expires_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            url TEXT,
            platform TEXT,
            quality TEXT,
            downloaded_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            payment_type TEXT NOT NULL,
            subscription_type TEXT NOT NULL,
            paid_at TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized")


def register_user(user_id: int, username: str, full_name: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, username, full_name)
        VALUES (?, ?, ?)
    """, (user_id, username, full_name))
    cursor.execute("""
        UPDATE users SET username = ?, full_name = ?
        WHERE user_id = ?
    """, (username, full_name, user_id))
    conn.commit()
    conn.close()


def get_user(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def increment_downloads(user_id: int, url: str, platform: str, quality: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET downloads = downloads + 1 WHERE user_id = ?
    """, (user_id,))
    cursor.execute("""
        INSERT INTO downloads (user_id, url, platform, quality)
        VALUES (?, ?, ?, ?)
    """, (user_id, url, platform, quality))
    conn.commit()
    conn.close()


def get_user_downloads_count(user_id: int) -> int:
    """Returns total download count for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT downloads FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row["downloads"] if row else 0


def get_subscription(user_id: int):
    """Returns subscription dict if active, None if absent or expired.
    Does NOT delete expired subscriptions — use check_premium_expired() for that."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subscriptions WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    sub = dict(row)
    expires_at = datetime.fromisoformat(sub["expires_at"])
    if expires_at < datetime.now():
        return None
    return sub


def add_subscription(user_id: int, sub_type: str, days: int):
    conn = get_connection()
    cursor = conn.cursor()
    expires_at = datetime.now() + timedelta(days=days)
    cursor.execute("""
        INSERT OR REPLACE INTO subscriptions (user_id, sub_type, expires_at)
        VALUES (?, ?, ?)
    """, (user_id, sub_type, expires_at.isoformat()))
    conn.commit()
    conn.close()


def remove_subscription(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def check_premium_expired():
    """Deletes all expired subscriptions. Call periodically."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("DELETE FROM subscriptions WHERE expires_at < ?", (now,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    if deleted:
        logger.info(f"check_premium_expired: removed {deleted} expired subscription(s)")
    return deleted


def is_premium(user_id: int) -> bool:
    return get_subscription(user_id) is not None


def get_premium_users() -> list[int]:
    """Returns list of user IDs with an active (non-expired) subscription."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
        SELECT user_id FROM subscriptions
        WHERE expires_at > ?
    """, (now,))
    rows = cursor.fetchall()
    conn.close()
    return [r["user_id"] for r in rows]


def get_all_users() -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE is_banned = 0")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_regular_users() -> list[int]:
    """Returns IDs of non-banned users WITHOUT an active subscription.
    Single JOIN query — no N+1."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
        SELECT u.user_id
        FROM users u
        LEFT JOIN subscriptions s
            ON u.user_id = s.user_id
            AND s.expires_at > :now
        WHERE u.is_banned = 0
          AND s.user_id IS NULL
    """, {"now": now})
    rows = cursor.fetchall()
    conn.close()
    return [r["user_id"] for r in rows]


def get_stats() -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM users")
    total = cursor.fetchone()["total"]
    now = datetime.now().isoformat()
    cursor.execute("SELECT COUNT(*) as total FROM subscriptions WHERE expires_at > ?", (now,))
    premium = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) as total FROM downloads")
    downloads = cursor.fetchone()["total"]
    conn.close()
    return {"total_users": total, "premium_users": premium, "total_downloads": downloads}


def log_payment(user_id: int, amount: int, payment_type: str, subscription_type: str):
    """Logs a payment to the payments table."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO payments (user_id, amount, payment_type, subscription_type)
        VALUES (?, ?, ?, ?)
    """, (user_id, amount, payment_type, subscription_type))
    conn.commit()
    conn.close()
    logger.info(f"Payment logged: user={user_id} amount={amount} type={payment_type} sub={subscription_type}")


def ban_user(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def unban_user(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def is_banned(user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return bool(row["is_banned"]) if row else False
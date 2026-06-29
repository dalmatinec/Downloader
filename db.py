# ========================================
# БАЗА ДАННЫХ (SQLite)
# ========================================

import sqlite3
from datetime import datetime, timedelta

DB_NAME = "users.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            premium INTEGER DEFAULT 0,
            premium_until TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_user(user_id, username):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
        (user_id, username)
    )
    conn.commit()
    conn.close()

def set_premium(user_id, days=30):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    until = (datetime.now() + timedelta(days=days)).isoformat()
    cursor.execute(
        "UPDATE users SET premium = 1, premium_until = ? WHERE user_id = ?",
        (until, user_id)
    )
    conn.commit()
    conn.close()

def is_premium(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT premium, premium_until FROM users WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    
    if result is None or result[0] == 0:
        return False
    
    if result[1]:
        until = datetime.fromisoformat(result[1])
        if until < datetime.now():
            return False
    
    return True

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result
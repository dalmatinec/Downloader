# database.py
import sqlite3
import datetime
from config import DATABASE_NAME

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Пользователи
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_premium BOOLEAN DEFAULT FALSE,
                premium_until TIMESTAMP,
                subscription_type TEXT,
                total_downloads INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')

        # Скачивания
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                platform TEXT,
                file_type TEXT,
                quality TEXT,
                file_size INTEGER,
                download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Платежи
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                payment_type TEXT,
                subscription_type TEXT,
                payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_successful BOOLEAN DEFAULT TRUE
            )
        ''')

        self.conn.commit()

    def add_user(self, user_id, username, first_name, last_name):
        self.cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name))
        self.conn.commit()

    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()

    def set_premium(self, user_id, subscription_type, days):
        premium_until = datetime.datetime.now() + datetime.timedelta(days=days)
        self.cursor.execute('''
            UPDATE users 
            SET is_premium = TRUE, premium_until = ?, subscription_type = ?
            WHERE user_id = ?
        ''', (premium_until, subscription_type, user_id))
        self.conn.commit()

    def remove_premium(self, user_id):
        self.cursor.execute('''
            UPDATE users 
            SET is_premium = FALSE, premium_until = NULL, subscription_type = NULL
            WHERE user_id = ?
        ''', (user_id,))
        self.conn.commit()

    def check_premium_expired(self):
        current_time = datetime.datetime.now()
        self.cursor.execute('''
            SELECT user_id FROM users 
            WHERE is_premium = TRUE AND premium_until < ?
        ''', (current_time,))
        expired = self.cursor.fetchall()
        for user in expired:
            self.remove_premium(user[0])
        return len(expired)

    def add_download(self, user_id, platform, file_type, quality, file_size):
        self.cursor.execute('''
            INSERT INTO downloads (user_id, platform, file_type, quality, file_size)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, platform, file_type, quality, file_size))
        self.cursor.execute('''
            UPDATE users SET total_downloads = total_downloads + 1 WHERE user_id = ?
        ''', (user_id,))
        self.conn.commit()

    def get_stats(self):
        self.cursor.execute('SELECT COUNT(*) FROM users')
        total_users = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT COUNT(*) FROM users WHERE is_premium = TRUE')
        premium_users = self.cursor.fetchone()[0]
        
        today = datetime.datetime.now().date()
        self.cursor.execute('SELECT COUNT(*) FROM users WHERE DATE(joined_date) = ?', (today,))
        new_users = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT COUNT(*) FROM downloads')
        total_downloads = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT COUNT(*) FROM downloads WHERE DATE(download_date) = ?', (today,))
        downloads_today = self.cursor.fetchone()[0]
        
        return {
            'total_users': total_users,
            'premium_users': premium_users,
            'new_users_today': new_users,
            'total_downloads': total_downloads,
            'downloads_today': downloads_today
        }

    def get_all_users(self):
        self.cursor.execute('SELECT user_id FROM users WHERE is_active = TRUE')
        return self.cursor.fetchall()

    def log_payment(self, user_id, amount, payment_type, subscription_type):
        self.cursor.execute('''
            INSERT INTO payments (user_id, amount, payment_type, subscription_type)
            VALUES (?, ?, ?, ?)
        ''', (user_id, amount, payment_type, subscription_type))
        self.conn.commit()

    def get_user_downloads_count(self, user_id):
        self.cursor.execute('SELECT total_downloads FROM users WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def close(self):
        self.conn.close()
# database.py
import sqlite3
import datetime
from typing import Optional, Dict, List, Tuple
from config import DATABASE_NAME, MONTH_DAYS, THREE_MONTHS_DAYS, SIX_MONTHS_DAYS, YEAR_DAYS, LIFETIME


class Database:
    def __init__(self):
        """Инициализация базы данных"""
        self.conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """Создание всех таблиц"""
        # Таблица пользователей
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

        # Таблица скачиваний
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                platform TEXT,
                file_type TEXT,
                quality TEXT,
                file_size INTEGER,
                download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        # Таблица статистики
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE DEFAULT CURRENT_DATE,
                total_users INTEGER DEFAULT 0,
                new_users INTEGER DEFAULT 0,
                total_downloads INTEGER DEFAULT 0,
                downloads_today INTEGER DEFAULT 0,
                premium_users INTEGER DEFAULT 0
            )
        ''')

        # Таблица платежей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                payment_type TEXT,
                subscription_type TEXT,
                payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_successful BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        self.conn.commit()

    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Добавление нового пользователя"""
        self.cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name))
        self.conn.commit()

    def get_user(self, user_id: int) -> Optional[Tuple]:
        """Получение информации о пользователе"""
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()

    def update_user_activity(self, user_id: int):
        """Обновление активности пользователя"""
        self.cursor.execute('''
            UPDATE users SET is_active = TRUE WHERE user_id = ?
        ''', (user_id,))
        self.conn.commit()

    def set_premium(self, user_id: int, subscription_type: str, days: int):
        """Выдача подписки пользователю"""
        premium_until = datetime.datetime.now() + datetime.timedelta(days=days)
        self.cursor.execute('''
            UPDATE users 
            SET is_premium = TRUE, 
                premium_until = ?,
                subscription_type = ?
            WHERE user_id = ?
        ''', (premium_until, subscription_type, user_id))
        self.conn.commit()

    def remove_premium(self, user_id: int):
        """Снятие подписки у пользователя"""
        self.cursor.execute('''
            UPDATE users 
            SET is_premium = FALSE, 
                premium_until = NULL,
                subscription_type = NULL
            WHERE user_id = ?
        ''', (user_id,))
        self.conn.commit()

    def check_premium_expired(self) -> int:
        """Проверка и снятие истекших подписок"""
        current_time = datetime.datetime.now()
        self.cursor.execute('''
            SELECT user_id FROM users 
            WHERE is_premium = TRUE 
            AND premium_until < ?
        ''', (current_time,))
        expired_users = self.cursor.fetchall()
        
        for user in expired_users:
            self.remove_premium(user[0])
        
        return len(expired_users)

    def add_download(self, user_id: int, platform: str, file_type: str, quality: str, file_size: int):
        """Добавление записи о скачивании"""
        self.cursor.execute('''
            INSERT INTO downloads (user_id, platform, file_type, quality, file_size)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, platform, file_type, quality, file_size))
        
        self.cursor.execute('''
            UPDATE users SET total_downloads = total_downloads + 1
            WHERE user_id = ?
        ''', (user_id,))
        
        self.conn.commit()

    def get_stats(self) -> Dict:
        """Получение статистики"""
        # Общее количество пользователей
        self.cursor.execute('SELECT COUNT(*) FROM users')
        total_users = self.cursor.fetchone()[0]
        
        # Активные подписчики
        self.cursor.execute('SELECT COUNT(*) FROM users WHERE is_premium = TRUE')
        premium_users = self.cursor.fetchone()[0]
        
        # Новые пользователи за сутки
        today = datetime.datetime.now().date()
        self.cursor.execute('''
            SELECT COUNT(*) FROM users 
            WHERE DATE(joined_date) = ?
        ''', (today,))
        new_users_today = self.cursor.fetchone()[0]
        
        # Всего скачиваний
        self.cursor.execute('SELECT COUNT(*) FROM downloads')
        total_downloads = self.cursor.fetchone()[0]
        
        # Скачиваний за сутки
        self.cursor.execute('''
            SELECT COUNT(*) FROM downloads 
            WHERE DATE(download_date) = ?
        ''', (today,))
        downloads_today = self.cursor.fetchone()[0]
        
        return {
            'total_users': total_users,
            'premium_users': premium_users,
            'new_users_today': new_users_today,
            'total_downloads': total_downloads,
            'downloads_today': downloads_today
        }

    def get_all_users(self) -> List[Tuple]:
        """Получение всех пользователей"""
        self.cursor.execute('SELECT user_id FROM users WHERE is_active = TRUE')
        return self.cursor.fetchall()

    def get_premium_users(self) -> List[Tuple]:
        """Получение всех премиум пользователей"""
        self.cursor.execute('SELECT user_id FROM users WHERE is_premium = TRUE')
        return self.cursor.fetchall()

    def log_payment(self, user_id: int, amount: int, payment_type: str, subscription_type: str):
        """Логирование платежа"""
        self.cursor.execute('''
            INSERT INTO payments (user_id, amount, payment_type, subscription_type)
            VALUES (?, ?, ?, ?)
        ''', (user_id, amount, payment_type, subscription_type))
        self.conn.commit()

    def get_user_downloads_count(self, user_id: int) -> int:
        """Получение количества скачиваний пользователя"""
        self.cursor.execute('''
            SELECT total_downloads FROM users WHERE user_id = ?
        ''', (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def update_stats_daily(self):
        """Обновление ежедневной статистики"""
        today = datetime.datetime.now().date()
        
        # Проверяем, есть ли запись за сегодня
        self.cursor.execute('SELECT id FROM stats WHERE date = ?', (today,))
        if not self.cursor.fetchone():
            # Создаем новую запись
            self.cursor.execute('''
                INSERT INTO stats (date, total_users, new_users, total_downloads, downloads_today, premium_users)
                SELECT 
                    ?,
                    COUNT(*),
                    SUM(CASE WHEN DATE(joined_date) = ? THEN 1 ELSE 0 END),
                    (SELECT COUNT(*) FROM downloads),
                    (SELECT COUNT(*) FROM downloads WHERE DATE(download_date) = ?),
                    SUM(CASE WHEN is_premium = TRUE THEN 1 ELSE 0 END)
                FROM users
            ''', (today, today, today))
            self.conn.commit()

    def close(self):
        """Закрытие соединения с базой данных"""
        self.conn.close()
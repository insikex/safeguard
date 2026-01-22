"""
Database Service
================
SQLite database service for storing group configurations, user data, statistics,
premium subscriptions, payments, and broadcasts.
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
import threading


class Database:
    """SQLite Database Service"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: str = "safeguard.db"):
        """Singleton pattern with thread safety"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: str = "safeguard.db"):
        """Initialize database connection"""
        if self._initialized:
            return
        
        self.db_path = db_path
        self._local = threading.local()
        self._create_tables()
        self._initialized = True
    
    @property
    def conn(self):
        """Get thread-local connection"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor"""
        cursor = self.conn.cursor()
        try:
            yield cursor
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e
        finally:
            cursor.close()
    
    def _create_tables(self):
        """Create database tables"""
        with self.get_cursor() as cursor:
            # Groups configuration table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    chat_id INTEGER PRIMARY KEY,
                    title TEXT,
                    language TEXT DEFAULT 'en',
                    welcome_enabled INTEGER DEFAULT 1,
                    welcome_message TEXT DEFAULT '',
                    verification_enabled INTEGER DEFAULT 1,
                    verification_type TEXT DEFAULT 'button',
                    antiflood_enabled INTEGER DEFAULT 1,
                    flood_limit INTEGER DEFAULT 5,
                    flood_time_window INTEGER DEFAULT 10,
                    antilink_enabled INTEGER DEFAULT 0,
                    antispam_enabled INTEGER DEFAULT 1,
                    antibadword_enabled INTEGER DEFAULT 0,
                    badwords TEXT DEFAULT '[]',
                    warn_limit INTEGER DEFAULT 3,
                    mute_duration INTEGER DEFAULT 3600,
                    rules TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER,
                    chat_id INTEGER,
                    username TEXT,
                    full_name TEXT,
                    language TEXT DEFAULT 'en',
                    is_verified INTEGER DEFAULT 0,
                    is_muted INTEGER DEFAULT 0,
                    mute_until TIMESTAMP,
                    warnings INTEGER DEFAULT 0,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_message TIMESTAMP,
                    message_count INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, chat_id)
                )
            """)
            
            # Pending verifications table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pending_verifications (
                    user_id INTEGER,
                    chat_id INTEGER,
                    verification_type TEXT,
                    answer TEXT,
                    attempts INTEGER DEFAULT 0,
                    message_id INTEGER,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, chat_id)
                )
            """)
            
            # Statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    stat_type TEXT,
                    stat_date DATE DEFAULT CURRENT_DATE,
                    count INTEGER DEFAULT 0,
                    UNIQUE(chat_id, stat_type, stat_date)
                )
            """)
            
            # Action logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS action_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    admin_id INTEGER,
                    target_user_id INTEGER,
                    action_type TEXT,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Bot users table (for broadcast feature - tracks users who interacted with bot)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    language TEXT DEFAULT 'en',
                    is_blocked INTEGER DEFAULT 0,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Premium subscriptions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS premium_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE,
                    plan_type TEXT,
                    price_paid REAL,
                    currency TEXT DEFAULT 'USD',
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    is_renewal INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Payments table (CryptoBot payment history)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    invoice_id INTEGER,
                    plan_type TEXT,
                    amount REAL,
                    currency TEXT,
                    crypto_currency TEXT,
                    status TEXT DEFAULT 'pending',
                    paid_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Broadcasts table (broadcast history)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS broadcasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_text TEXT,
                    photo_file_id TEXT,
                    total_users INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    failed_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_chat ON users(chat_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pending_expires ON pending_verifications(expires_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stats_chat_date ON statistics(chat_id, stat_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bot_users_blocked ON bot_users(is_blocked)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_premium_user ON premium_subscriptions(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_premium_active ON premium_subscriptions(is_active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_invoice ON payments(invoice_id)")
    
    # ==================== Group Methods ====================
    
    def get_group(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get group configuration"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM groups WHERE chat_id = ?", (chat_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def create_or_update_group(self, chat_id: int, title: str = None, **kwargs) -> Dict[str, Any]:
        """Create or update group configuration"""
        existing = self.get_group(chat_id)
        
        if existing:
            # Update existing
            updates = []
            values = []
            for key, value in kwargs.items():
                updates.append(f"{key} = ?")
                values.append(value)
            
            if title:
                updates.append("title = ?")
                values.append(title)
            
            if updates:
                updates.append("updated_at = CURRENT_TIMESTAMP")
                values.append(chat_id)
                
                with self.get_cursor() as cursor:
                    cursor.execute(
                        f"UPDATE groups SET {', '.join(updates)} WHERE chat_id = ?",
                        values
                    )
        else:
            # Create new
            with self.get_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO groups (chat_id, title) VALUES (?, ?)",
                    (chat_id, title or "Unknown")
                )
                
                if kwargs:
                    updates = []
                    values = []
                    for key, value in kwargs.items():
                        updates.append(f"{key} = ?")
                        values.append(value)
                    values.append(chat_id)
                    
                    cursor.execute(
                        f"UPDATE groups SET {', '.join(updates)} WHERE chat_id = ?",
                        values
                    )
        
        return self.get_group(chat_id)
    
    def update_group_setting(self, chat_id: int, setting: str, value: Any):
        """Update a single group setting"""
        with self.get_cursor() as cursor:
            cursor.execute(
                f"UPDATE groups SET {setting} = ?, updated_at = CURRENT_TIMESTAMP WHERE chat_id = ?",
                (value, chat_id)
            )
    
    # ==================== User Methods ====================
    
    def get_user(self, user_id: int, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get user in a specific group"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE user_id = ? AND chat_id = ?",
                (user_id, chat_id)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def create_or_update_user(self, user_id: int, chat_id: int, **kwargs) -> Dict[str, Any]:
        """Create or update user record"""
        existing = self.get_user(user_id, chat_id)
        
        if existing:
            if kwargs:
                updates = [f"{k} = ?" for k in kwargs.keys()]
                values = list(kwargs.values()) + [user_id, chat_id]
                
                with self.get_cursor() as cursor:
                    cursor.execute(
                        f"UPDATE users SET {', '.join(updates)} WHERE user_id = ? AND chat_id = ?",
                        values
                    )
        else:
            columns = ["user_id", "chat_id"] + list(kwargs.keys())
            placeholders = ["?"] * len(columns)
            values = [user_id, chat_id] + list(kwargs.values())
            
            with self.get_cursor() as cursor:
                cursor.execute(
                    f"INSERT INTO users ({', '.join(columns)}) VALUES ({', '.join(placeholders)})",
                    values
                )
        
        return self.get_user(user_id, chat_id)
    
    def verify_user(self, user_id: int, chat_id: int):
        """Mark user as verified"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "UPDATE users SET is_verified = 1 WHERE user_id = ? AND chat_id = ?",
                (user_id, chat_id)
            )
    
    def add_warning(self, user_id: int, chat_id: int) -> int:
        """Add warning to user, returns new warning count"""
        user = self.get_user(user_id, chat_id)
        new_count = (user.get('warnings', 0) if user else 0) + 1
        
        with self.get_cursor() as cursor:
            if user:
                cursor.execute(
                    "UPDATE users SET warnings = ? WHERE user_id = ? AND chat_id = ?",
                    (new_count, user_id, chat_id)
                )
            else:
                cursor.execute(
                    "INSERT INTO users (user_id, chat_id, warnings) VALUES (?, ?, ?)",
                    (user_id, chat_id, new_count)
                )
        
        return new_count
    
    def remove_warning(self, user_id: int, chat_id: int) -> int:
        """Remove warning from user, returns new warning count"""
        user = self.get_user(user_id, chat_id)
        new_count = max(0, (user.get('warnings', 0) if user else 0) - 1)
        
        with self.get_cursor() as cursor:
            cursor.execute(
                "UPDATE users SET warnings = ? WHERE user_id = ? AND chat_id = ?",
                (new_count, user_id, chat_id)
            )
        
        return new_count
    
    def reset_warnings(self, user_id: int, chat_id: int):
        """Reset user warnings to 0"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "UPDATE users SET warnings = 0 WHERE user_id = ? AND chat_id = ?",
                (user_id, chat_id)
            )
    
    def mute_user(self, user_id: int, chat_id: int, duration: int):
        """Mute user for duration (seconds)"""
        mute_until = datetime.now() + timedelta(seconds=duration)
        with self.get_cursor() as cursor:
            cursor.execute(
                "UPDATE users SET is_muted = 1, mute_until = ? WHERE user_id = ? AND chat_id = ?",
                (mute_until, user_id, chat_id)
            )
    
    def unmute_user(self, user_id: int, chat_id: int):
        """Unmute user"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "UPDATE users SET is_muted = 0, mute_until = NULL WHERE user_id = ? AND chat_id = ?",
                (user_id, chat_id)
            )
    
    # ==================== Verification Methods ====================
    
    def create_pending_verification(
        self,
        user_id: int,
        chat_id: int,
        verification_type: str,
        answer: str,
        message_id: int,
        timeout: int = 120
    ):
        """Create pending verification record"""
        expires_at = datetime.now() + timedelta(seconds=timeout)
        
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT OR REPLACE INTO pending_verifications 
                (user_id, chat_id, verification_type, answer, message_id, expires_at, attempts)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            """, (user_id, chat_id, verification_type, answer, message_id, expires_at))
    
    def get_pending_verification(self, user_id: int, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get pending verification"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM pending_verifications WHERE user_id = ? AND chat_id = ?",
                (user_id, chat_id)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def increment_verification_attempts(self, user_id: int, chat_id: int) -> int:
        """Increment verification attempts, returns new count"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "UPDATE pending_verifications SET attempts = attempts + 1 WHERE user_id = ? AND chat_id = ?",
                (user_id, chat_id)
            )
            cursor.execute(
                "SELECT attempts FROM pending_verifications WHERE user_id = ? AND chat_id = ?",
                (user_id, chat_id)
            )
            row = cursor.fetchone()
            return row['attempts'] if row else 0
    
    def delete_pending_verification(self, user_id: int, chat_id: int):
        """Delete pending verification"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "DELETE FROM pending_verifications WHERE user_id = ? AND chat_id = ?",
                (user_id, chat_id)
            )
    
    def get_expired_verifications(self) -> List[Dict[str, Any]]:
        """Get all expired pending verifications"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM pending_verifications WHERE expires_at < ?",
                (datetime.now(),)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def cleanup_expired_verifications(self):
        """Delete all expired verifications"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "DELETE FROM pending_verifications WHERE expires_at < ?",
                (datetime.now(),)
            )
    
    # ==================== Statistics Methods ====================
    
    def increment_stat(self, chat_id: int, stat_type: str, count: int = 1):
        """Increment a statistic counter"""
        today = datetime.now().date()
        
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO statistics (chat_id, stat_type, stat_date, count)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chat_id, stat_type, stat_date) 
                DO UPDATE SET count = count + ?
            """, (chat_id, stat_type, today, count, count))
    
    def get_stats(self, chat_id: int, days: int = 1) -> Dict[str, int]:
        """Get statistics for a group"""
        start_date = datetime.now().date() - timedelta(days=days-1)
        
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT stat_type, SUM(count) as total
                FROM statistics
                WHERE chat_id = ? AND stat_date >= ?
                GROUP BY stat_type
            """, (chat_id, start_date))
            
            return {row['stat_type']: row['total'] for row in cursor.fetchall()}
    
    # ==================== Action Log Methods ====================
    
    def log_action(
        self,
        chat_id: int,
        admin_id: int,
        target_user_id: int,
        action_type: str,
        reason: str = ""
    ):
        """Log an admin action"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO action_logs (chat_id, admin_id, target_user_id, action_type, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (chat_id, admin_id, target_user_id, action_type, reason))
    
    # ==================== Bot Users Methods (for Broadcast) ====================
    
    def register_bot_user(
        self,
        user_id: int,
        username: str = None,
        full_name: str = None,
        language: str = "en"
    ):
        """Register or update a bot user (for broadcast feature)"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO bot_users (user_id, username, full_name, language, last_seen)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = COALESCE(?, username),
                    full_name = COALESCE(?, full_name),
                    language = COALESCE(?, language),
                    last_seen = CURRENT_TIMESTAMP
            """, (user_id, username, full_name, language, username, full_name, language))
    
    def get_bot_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get bot user by ID"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM bot_users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def get_all_bot_users(self, include_blocked: bool = False) -> List[Dict[str, Any]]:
        """Get all bot users for broadcast"""
        with self.get_cursor() as cursor:
            if include_blocked:
                cursor.execute("SELECT * FROM bot_users")
            else:
                cursor.execute("SELECT * FROM bot_users WHERE is_blocked = 0")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_bot_users_count(self, include_blocked: bool = False) -> int:
        """Get total count of bot users"""
        with self.get_cursor() as cursor:
            if include_blocked:
                cursor.execute("SELECT COUNT(*) as count FROM bot_users")
            else:
                cursor.execute("SELECT COUNT(*) as count FROM bot_users WHERE is_blocked = 0")
            row = cursor.fetchone()
            return row['count'] if row else 0
    
    def mark_user_blocked(self, user_id: int):
        """Mark user as blocked (when bot can't send message)"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "UPDATE bot_users SET is_blocked = 1 WHERE user_id = ?",
                (user_id,)
            )
    
    def mark_user_unblocked(self, user_id: int):
        """Mark user as unblocked"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "UPDATE bot_users SET is_blocked = 0 WHERE user_id = ?",
                (user_id,)
            )
    
    # ==================== Premium Subscription Methods ====================
    
    def create_premium_subscription(
        self,
        user_id: int,
        plan_type: str,
        price_paid: float,
        duration_days: int,
        currency: str = "USD",
        is_renewal: bool = False
    ) -> int:
        """Create a new premium subscription"""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=duration_days)
        
        with self.get_cursor() as cursor:
            # Deactivate any existing subscription
            cursor.execute(
                "UPDATE premium_subscriptions SET is_active = 0 WHERE user_id = ?",
                (user_id,)
            )
            
            cursor.execute("""
                INSERT INTO premium_subscriptions 
                (user_id, plan_type, price_paid, currency, start_date, end_date, is_active, is_renewal)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """, (user_id, plan_type, price_paid, currency, start_date, end_date, 1 if is_renewal else 0))
            
            return cursor.lastrowid
    
    def get_premium_subscription(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get active premium subscription for user"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM premium_subscriptions 
                WHERE user_id = ? AND is_active = 1 AND end_date > ?
                ORDER BY end_date DESC LIMIT 1
            """, (user_id, datetime.now()))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def is_premium_user(self, user_id: int) -> bool:
        """Check if user has active premium subscription"""
        sub = self.get_premium_subscription(user_id)
        return sub is not None
    
    def has_previous_subscription(self, user_id: int) -> bool:
        """Check if user had any previous subscription (for renewal discount)"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) as count FROM premium_subscriptions WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            return row['count'] > 0 if row else False
    
    def get_expired_subscriptions(self) -> List[Dict[str, Any]]:
        """Get all expired but still active subscriptions"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM premium_subscriptions 
                WHERE is_active = 1 AND end_date < ?
            """, (datetime.now(),))
            return [dict(row) for row in cursor.fetchall()]
    
    def deactivate_subscription(self, subscription_id: int):
        """Deactivate a subscription"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "UPDATE premium_subscriptions SET is_active = 0 WHERE id = ?",
                (subscription_id,)
            )
    
    # ==================== Payment Methods ====================
    
    def create_payment(
        self,
        user_id: int,
        invoice_id: int,
        plan_type: str,
        amount: float,
        currency: str,
        crypto_currency: str = None
    ) -> int:
        """Create a new payment record"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO payments 
                (user_id, invoice_id, plan_type, amount, currency, crypto_currency, status)
                VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """, (user_id, invoice_id, plan_type, amount, currency, crypto_currency))
            return cursor.lastrowid
    
    def get_payment_by_invoice(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """Get payment by invoice ID"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM payments WHERE invoice_id = ?",
                (invoice_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def update_payment_status(self, invoice_id: int, status: str):
        """Update payment status"""
        with self.get_cursor() as cursor:
            if status == 'paid':
                cursor.execute(
                    "UPDATE payments SET status = ?, paid_at = CURRENT_TIMESTAMP WHERE invoice_id = ?",
                    (status, invoice_id)
                )
            else:
                cursor.execute(
                    "UPDATE payments SET status = ? WHERE invoice_id = ?",
                    (status, invoice_id)
                )
    
    def get_user_payments(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all payments for a user"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM payments WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== Broadcast Methods ====================
    
    def create_broadcast(
        self,
        message_text: str,
        photo_file_id: str = None,
        total_users: int = 0
    ) -> int:
        """Create a new broadcast record"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO broadcasts (message_text, photo_file_id, total_users)
                VALUES (?, ?, ?)
            """, (message_text, photo_file_id, total_users))
            return cursor.lastrowid
    
    def update_broadcast_stats(
        self,
        broadcast_id: int,
        success_count: int,
        failed_count: int
    ):
        """Update broadcast statistics"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE broadcasts SET success_count = ?, failed_count = ?
                WHERE id = ?
            """, (success_count, failed_count, broadcast_id))
    
    def get_broadcast(self, broadcast_id: int) -> Optional[Dict[str, Any]]:
        """Get broadcast by ID"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM broadcasts WHERE id = ?", (broadcast_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    


# Global database instance
db = Database()

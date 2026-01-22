"""
Database Service
================
SQLite database service for storing group configurations, user data, and statistics.
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
            
            # Bot users table (users who started the bot in private chat)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    language TEXT DEFAULT 'en',
                    is_premium INTEGER DEFAULT 0,
                    premium_until TIMESTAMP,
                    premium_plan TEXT,
                    total_spent REAL DEFAULT 0,
                    referral_code TEXT UNIQUE,
                    referred_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Premium subscriptions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS premium_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    plan TEXT,
                    amount REAL,
                    currency TEXT DEFAULT 'USD',
                    duration_days INTEGER,
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES bot_users(user_id)
                )
            """)
            
            # Payment invoices table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payment_invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    invoice_id TEXT UNIQUE,
                    amount REAL,
                    currency TEXT,
                    plan TEXT,
                    status TEXT DEFAULT 'pending',
                    pay_url TEXT,
                    paid_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES bot_users(user_id)
                )
            """)
            
            # Broadcasts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS broadcasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    message_text TEXT,
                    photo_file_id TEXT,
                    total_users INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    failed_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_chat ON users(chat_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pending_expires ON pending_verifications(expires_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stats_chat_date ON statistics(chat_id, stat_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bot_users_premium ON bot_users(is_premium)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_invoices_status ON payment_invoices(status)")
    
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


    # ==================== Bot User Methods ====================
    
    def get_bot_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get bot user by ID"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM bot_users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def create_or_update_bot_user(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Create or update bot user"""
        import secrets
        existing = self.get_bot_user(user_id)
        
        if existing:
            if kwargs:
                updates = [f"{k} = ?" for k in kwargs.keys()]
                updates.append("last_active = CURRENT_TIMESTAMP")
                values = list(kwargs.values()) + [user_id]
                
                with self.get_cursor() as cursor:
                    cursor.execute(
                        f"UPDATE bot_users SET {', '.join(updates)} WHERE user_id = ?",
                        values
                    )
        else:
            # Generate unique referral code
            referral_code = secrets.token_hex(4).upper()
            columns = ["user_id", "referral_code"] + list(kwargs.keys())
            placeholders = ["?"] * len(columns)
            values = [user_id, referral_code] + list(kwargs.values())
            
            with self.get_cursor() as cursor:
                cursor.execute(
                    f"INSERT INTO bot_users ({', '.join(columns)}) VALUES ({', '.join(placeholders)})",
                    values
                )
        
        return self.get_bot_user(user_id)
    
    def get_all_bot_users(self) -> List[Dict[str, Any]]:
        """Get all bot users for broadcasting"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM bot_users")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_premium_users(self) -> List[Dict[str, Any]]:
        """Get all premium users"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM bot_users WHERE is_premium = 1 AND premium_until > ?",
                (datetime.now(),)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_bot_users_count(self) -> int:
        """Get total count of bot users"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM bot_users")
            row = cursor.fetchone()
            return row['count'] if row else 0
    
    # ==================== Premium Methods ====================
    
    def set_user_premium(self, user_id: int, plan: str, duration_days: int, amount: float):
        """Set user as premium"""
        user = self.get_bot_user(user_id)
        
        # Calculate end date
        if user and user.get('is_premium') and user.get('premium_until'):
            # Extend existing premium
            try:
                current_end = datetime.fromisoformat(str(user['premium_until']))
                if current_end > datetime.now():
                    end_date = current_end + timedelta(days=duration_days)
                else:
                    end_date = datetime.now() + timedelta(days=duration_days)
            except:
                end_date = datetime.now() + timedelta(days=duration_days)
        else:
            end_date = datetime.now() + timedelta(days=duration_days)
        
        start_date = datetime.now()
        
        with self.get_cursor() as cursor:
            # Update bot user
            cursor.execute("""
                UPDATE bot_users 
                SET is_premium = 1, premium_until = ?, premium_plan = ?, 
                    total_spent = total_spent + ?
                WHERE user_id = ?
            """, (end_date, plan, amount, user_id))
            
            # Create subscription record
            cursor.execute("""
                INSERT INTO premium_subscriptions 
                (user_id, plan, amount, duration_days, start_date, end_date, status)
                VALUES (?, ?, ?, ?, ?, ?, 'active')
            """, (user_id, plan, amount, duration_days, start_date, end_date))
    
    def check_premium_status(self, user_id: int) -> bool:
        """Check if user has active premium"""
        user = self.get_bot_user(user_id)
        if not user or not user.get('is_premium'):
            return False
        
        premium_until = user.get('premium_until')
        if not premium_until:
            return False
        
        try:
            end_date = datetime.fromisoformat(str(premium_until))
            return end_date > datetime.now()
        except:
            return False
    
    def get_premium_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's premium subscription info"""
        user = self.get_bot_user(user_id)
        if not user:
            return None
        
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM premium_subscriptions 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (user_id,))
            row = cursor.fetchone()
            
        return {
            'is_premium': self.check_premium_status(user_id),
            'premium_until': user.get('premium_until'),
            'premium_plan': user.get('premium_plan'),
            'total_spent': user.get('total_spent', 0),
            'last_subscription': dict(row) if row else None
        }
    
    def expire_premium(self):
        """Expire all ended premium subscriptions"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE bot_users 
                SET is_premium = 0 
                WHERE is_premium = 1 AND premium_until < ?
            """, (datetime.now(),))
            
            cursor.execute("""
                UPDATE premium_subscriptions 
                SET status = 'expired' 
                WHERE status = 'active' AND end_date < ?
            """, (datetime.now(),))
    
    # ==================== Payment Invoice Methods ====================
    
    def create_invoice(self, user_id: int, invoice_id: str, amount: float, 
                      currency: str, plan: str, pay_url: str) -> Dict[str, Any]:
        """Create payment invoice record"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO payment_invoices 
                (user_id, invoice_id, amount, currency, plan, pay_url, status)
                VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """, (user_id, invoice_id, amount, currency, plan, pay_url))
        
        return self.get_invoice(invoice_id)
    
    def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Get invoice by ID"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM payment_invoices WHERE invoice_id = ?",
                (invoice_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def get_pending_invoices(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user's pending invoices"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM payment_invoices WHERE user_id = ? AND status = 'pending'",
                (user_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def update_invoice_status(self, invoice_id: str, status: str):
        """Update invoice status"""
        with self.get_cursor() as cursor:
            if status == 'paid':
                cursor.execute("""
                    UPDATE payment_invoices 
                    SET status = ?, paid_at = CURRENT_TIMESTAMP 
                    WHERE invoice_id = ?
                """, (status, invoice_id))
            else:
                cursor.execute(
                    "UPDATE payment_invoices SET status = ? WHERE invoice_id = ?",
                    (status, invoice_id)
                )
    
    # ==================== Broadcast Methods ====================
    
    def create_broadcast(self, admin_id: int, message_text: str, 
                        photo_file_id: str = None, total_users: int = 0) -> int:
        """Create broadcast record, returns broadcast ID"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO broadcasts 
                (admin_id, message_text, photo_file_id, total_users, status)
                VALUES (?, ?, ?, ?, 'sending')
            """, (admin_id, message_text, photo_file_id, total_users))
            return cursor.lastrowid
    
    def update_broadcast_progress(self, broadcast_id: int, success: int = 0, failed: int = 0):
        """Update broadcast progress"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE broadcasts 
                SET success_count = success_count + ?, failed_count = failed_count + ?
                WHERE id = ?
            """, (success, failed, broadcast_id))
    
    def complete_broadcast(self, broadcast_id: int):
        """Mark broadcast as completed"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "UPDATE broadcasts SET status = 'completed' WHERE id = ?",
                (broadcast_id,)
            )
    
    def get_broadcast_stats(self, broadcast_id: int) -> Optional[Dict[str, Any]]:
        """Get broadcast statistics"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM broadcasts WHERE id = ?", (broadcast_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None


# Global database instance
db = Database()

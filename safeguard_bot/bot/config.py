"""
Safeguard Bot Configuration
============================
Configuration management for the Telegram Safeguard Bot.
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class BotConfig:
    """Bot configuration settings"""
    
    # Telegram Bot Token
    token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    
    # Bot Admin IDs (comma separated in env)
    admin_ids: list = field(default_factory=lambda: [
        int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
    ])
    
    # Database settings
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///safeguard.db"))
    
    # Verification settings
    verification_timeout: int = field(default_factory=lambda: int(os.getenv("VERIFICATION_TIMEOUT", "120")))
    max_verification_attempts: int = field(default_factory=lambda: int(os.getenv("MAX_VERIFICATION_ATTEMPTS", "3")))
    
    # Anti-spam settings
    flood_limit: int = field(default_factory=lambda: int(os.getenv("FLOOD_LIMIT", "5")))
    flood_time_window: int = field(default_factory=lambda: int(os.getenv("FLOOD_TIME_WINDOW", "10")))
    
    # Warning settings
    max_warnings: int = field(default_factory=lambda: int(os.getenv("MAX_WARNINGS", "3")))
    
    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    
    # Web server for portal verification
    web_host: str = field(default_factory=lambda: os.getenv("WEB_HOST", "0.0.0.0"))
    web_port: int = field(default_factory=lambda: int(os.getenv("WEB_PORT", "8080")))
    web_url: str = field(default_factory=lambda: os.getenv("WEB_URL", "http://localhost:8080"))
    
    def validate(self) -> bool:
        """Validate required configuration"""
        if not self.token:
            raise ValueError("BOT_TOKEN is required!")
        return True


@dataclass
class DefaultGroupConfig:
    """Default configuration for new groups"""
    
    # Welcome settings
    welcome_enabled: bool = True
    welcome_message: str = ""  # Empty = use default
    
    # Verification settings
    verification_enabled: bool = True
    verification_type: str = "button"  # button, math, emoji, portal
    
    # Protection settings
    antiflood_enabled: bool = True
    antilink_enabled: bool = False
    antispam_enabled: bool = True
    antibadword_enabled: bool = False
    
    # Moderation settings
    warn_limit: int = 3
    mute_duration: int = 3600  # seconds
    
    # Captcha settings
    captcha_timeout: int = 120  # seconds


# Global config instance
config = BotConfig()
default_group_config = DefaultGroupConfig()


# Supported languages
SUPPORTED_LANGUAGES = {
    "id": "Indonesia",
    "en": "English"
}

# Default language
DEFAULT_LANGUAGE = "en"

# Indonesian language codes for auto-detection
INDONESIAN_CODES = ["id", "in", "jv", "su", "ms"]  # Indonesian, Javanese, Sundanese, Malay

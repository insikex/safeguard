"""
Language Service
================
Handles multi-language support with automatic language detection.
"""

import json
import os
from typing import Optional, Dict, Any
from functools import lru_cache
from telegram import User

from bot.config import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE, INDONESIAN_CODES


class LanguageService:
    """Service for handling multi-language support"""
    
    _instance = None
    _locales: Dict[str, Dict[str, Any]] = {}
    _user_languages: Dict[int, str] = {}  # Cache user language preferences
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_locales()
        return cls._instance
    
    def _load_locales(self):
        """Load all locale files"""
        locale_dir = os.path.join(os.path.dirname(__file__), "..", "locales")
        
        for lang_code in SUPPORTED_LANGUAGES:
            locale_path = os.path.join(locale_dir, f"{lang_code}.json")
            if os.path.exists(locale_path):
                with open(locale_path, "r", encoding="utf-8") as f:
                    self._locales[lang_code] = json.load(f)
            else:
                print(f"Warning: Locale file not found: {locale_path}")
    
    def detect_language(self, user: Optional[User]) -> str:
        """
        Detect user's language based on Telegram language_code.
        Returns 'id' for Indonesian users, 'en' for others.
        """
        if user is None:
            return DEFAULT_LANGUAGE
        
        # Check cached preference first
        if user.id in self._user_languages:
            return self._user_languages[user.id]
        
        # Get language from Telegram
        lang_code = getattr(user, 'language_code', None) or DEFAULT_LANGUAGE
        lang_code = lang_code.lower().split('-')[0]  # Get base language (e.g., 'en-US' -> 'en')
        
        # Check if Indonesian
        if lang_code in INDONESIAN_CODES:
            detected = "id"
        elif lang_code in SUPPORTED_LANGUAGES:
            detected = lang_code
        else:
            detected = DEFAULT_LANGUAGE
        
        return detected
    
    def set_user_language(self, user_id: int, language: str):
        """Set user's preferred language"""
        if language in SUPPORTED_LANGUAGES:
            self._user_languages[user_id] = language
    
    def get_user_language(self, user_id: int) -> str:
        """Get user's cached language preference"""
        return self._user_languages.get(user_id, DEFAULT_LANGUAGE)
    
    def get(self, key: str, language: str = DEFAULT_LANGUAGE, **kwargs) -> str:
        """
        Get translated string by key path.
        
        Args:
            key: Dot-separated key path (e.g., 'welcome.start_private')
            language: Language code
            **kwargs: Format arguments
        
        Returns:
            Translated string with formatting applied
        """
        if language not in self._locales:
            language = DEFAULT_LANGUAGE
        
        locale = self._locales.get(language, {})
        
        # Navigate through nested keys
        keys = key.split('.')
        value = locale
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                # Fallback to English
                value = self._locales.get(DEFAULT_LANGUAGE, {})
                for k2 in keys:
                    if isinstance(value, dict) and k2 in value:
                        value = value[k2]
                    else:
                        return f"[{key}]"  # Key not found
                break
        
        if isinstance(value, str):
            try:
                return value.format(**kwargs) if kwargs else value
            except KeyError:
                return value
        
        return str(value)
    
    def get_for_user(self, key: str, user: Optional[User], **kwargs) -> str:
        """
        Get translated string for a specific user.
        Automatically detects language based on user's Telegram settings.
        """
        language = self.detect_language(user)
        return self.get(key, language, **kwargs)


# Global instance
lang_service = LanguageService()


# Helper functions
def get_text(key: str, user: Optional[User] = None, language: str = None, **kwargs) -> str:
    """
    Shortcut function to get translated text.
    
    If user is provided, automatically detects their language.
    If language is provided, uses that language.
    Otherwise, uses default language.
    """
    if user is not None:
        return lang_service.get_for_user(key, user, **kwargs)
    elif language is not None:
        return lang_service.get(key, language, **kwargs)
    else:
        return lang_service.get(key, DEFAULT_LANGUAGE, **kwargs)


def detect_lang(user: Optional[User]) -> str:
    """Shortcut to detect user's language"""
    return lang_service.detect_language(user)


def set_lang(user_id: int, language: str):
    """Shortcut to set user's language"""
    lang_service.set_user_language(user_id, language)

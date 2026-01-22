"""
Services Package
================
Contains all service classes for the Safeguard Bot.
"""

from .language import LanguageService, lang_service, get_text, detect_lang, set_lang
from .database import Database, db
from .captcha import CaptchaService, captcha_service, CaptchaType, CaptchaChallenge
from .payment import PaymentService, payment_service, PREMIUM_PLANS, get_premium_features

__all__ = [
    # Language
    "LanguageService",
    "lang_service",
    "get_text",
    "detect_lang",
    "set_lang",
    
    # Database
    "Database",
    "db",
    
    # Captcha
    "CaptchaService",
    "captcha_service",
    "CaptchaType",
    "CaptchaChallenge",
    
    # Payment
    "PaymentService",
    "payment_service",
    "PREMIUM_PLANS",
    "get_premium_features",
]

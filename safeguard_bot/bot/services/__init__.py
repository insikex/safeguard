"""
Services Package
================
Contains all service classes for the Safeguard Bot.
"""

from .language import LanguageService, lang_service, get_text, detect_lang, set_lang
from .database import Database, db
from .captcha import CaptchaService, captcha_service, CaptchaType, CaptchaChallenge
from .payment import PaymentService, payment_service, PREMIUM_PLANS, get_premium_features
from .pakasir import (
    PakasirService, 
    pakasir_service, 
    PREMIUM_PLANS_IDR, 
    get_premium_features_id,
    format_rupiah
)

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
    
    # Payment (Legacy CryptoBot)
    "PaymentService",
    "payment_service",
    "PREMIUM_PLANS",
    "get_premium_features",
    
    # Pakasir Payment (QRIS Indonesia)
    "PakasirService",
    "pakasir_service",
    "PREMIUM_PLANS_IDR",
    "get_premium_features_id",
    "format_rupiah",
]

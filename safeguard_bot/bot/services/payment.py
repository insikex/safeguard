"""
Payment Service
================
CryptoBot (Crypto Pay) payment integration using aiocryptopay.
Documentation: https://help.send.tg/en/articles/10279948-crypto-pay-api
"""

import logging
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta

from aiocryptopay import AioCryptoPay, Networks
from aiocryptopay.models.invoice import Invoice
from aiocryptopay.models.update import Update as CryptoUpdate

from bot.config import config
from bot.services.database import db

logger = logging.getLogger(__name__)


# Premium plan configurations
PREMIUM_PLANS = {
    "1_month": {
        "name": "1 Month Premium",
        "name_id": "Premium 1 Bulan",
        "duration_days": 30,
        "price": config.premium_price_1_month,  # $10
        "original_price": 10,
        "discount": 0,
    },
    "3_months": {
        "name": "3 Months Premium",
        "name_id": "Premium 3 Bulan",
        "duration_days": 90,
        "price": config.premium_price_3_months,  # $18
        "original_price": 30,
        "discount": 40,  # 40% off ($30 -> $18)
    },
    "6_months": {
        "name": "6 Months Premium",
        "name_id": "Premium 6 Bulan",
        "duration_days": 180,
        "price": config.premium_price_6_months,  # $50
        "original_price": 100,
        "discount": 50,  # 50% off ($100 -> $50)
    }
}


class PaymentService:
    """CryptoBot Payment Service"""
    
    _instance = None
    _crypto: Optional[AioCryptoPay] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the payment service"""
        if self._crypto is None and config.cryptobot_token:
            network = Networks.TEST_NET if config.cryptobot_testnet else Networks.MAIN_NET
            self._crypto = AioCryptoPay(
                token=config.cryptobot_token,
                network=network
            )
            logger.info(f"CryptoBot initialized on {'testnet' if config.cryptobot_testnet else 'mainnet'}")
    
    @property
    def is_configured(self) -> bool:
        """Check if CryptoBot is properly configured"""
        return self._crypto is not None and bool(config.cryptobot_token)
    
    async def get_me(self) -> Optional[Dict[str, Any]]:
        """Get CryptoBot app info"""
        if not self.is_configured:
            return None
        try:
            return await self._crypto.get_me()
        except Exception as e:
            logger.error(f"Error getting CryptoBot info: {e}")
            return None
    
    def get_plan_price(self, plan_type: str, is_renewal: bool = False) -> float:
        """
        Get the price for a plan.
        6-month plan gets 50% discount on renewal.
        """
        plan = PREMIUM_PLANS.get(plan_type)
        if not plan:
            return 0
        
        price = plan["price"]
        
        # Additional discount for 6-month renewal
        if plan_type == "6_months" and is_renewal:
            # Already 50% off, no additional discount needed
            # The 50% discount applies to every renewal
            pass
        
        return price
    
    def get_plan_info(self, plan_type: str, lang: str = "en") -> Optional[Dict[str, Any]]:
        """Get plan information"""
        plan = PREMIUM_PLANS.get(plan_type)
        if not plan:
            return None
        
        name_key = "name_id" if lang == "id" else "name"
        return {
            "type": plan_type,
            "name": plan[name_key],
            "duration_days": plan["duration_days"],
            "price": plan["price"],
            "original_price": plan["original_price"],
            "discount": plan["discount"]
        }
    
    async def create_invoice(
        self,
        user_id: int,
        plan_type: str,
        is_renewal: bool = False
    ) -> Optional[Invoice]:
        """
        Create a payment invoice for premium subscription.
        Returns the invoice object with pay_url for payment.
        """
        if not self.is_configured:
            logger.error("CryptoBot is not configured")
            return None
        
        plan = PREMIUM_PLANS.get(plan_type)
        if not plan:
            logger.error(f"Invalid plan type: {plan_type}")
            return None
        
        price = self.get_plan_price(plan_type, is_renewal)
        
        try:
            # Create invoice with CryptoBot
            # Supported currencies: USDT, TON, BTC, ETH, LTC, BNB, TRX, USDC
            invoice = await self._crypto.create_invoice(
                asset="USDT",  # Using USDT as default
                amount=price,
                description=f"Safeguard Bot - {plan['name']}",
                hidden_message="Thank you for your purchase! Your premium subscription is now active.",
                paid_btn_name="callback",
                paid_btn_url=f"https://t.me/{config.token.split(':')[0]}",  # Bot link
                payload=f"{user_id}:{plan_type}:{1 if is_renewal else 0}",
                expires_in=3600,  # 1 hour expiration
                allow_comments=False,
                allow_anonymous=False
            )
            
            # Record payment in database
            db.create_payment(
                user_id=user_id,
                invoice_id=invoice.invoice_id,
                plan_type=plan_type,
                amount=price,
                currency="USDT",
                crypto_currency="USDT"
            )
            
            logger.info(f"Created invoice {invoice.invoice_id} for user {user_id}, plan {plan_type}, amount ${price}")
            
            return invoice
            
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            return None
    
    async def check_invoice(self, invoice_id: int) -> Optional[str]:
        """
        Check the status of an invoice.
        Returns: 'active', 'paid', 'expired', or None if error
        """
        if not self.is_configured:
            return None
        
        try:
            invoices = await self._crypto.get_invoices(invoice_ids=[invoice_id])
            if invoices:
                return invoices[0].status
            return None
        except Exception as e:
            logger.error(f"Error checking invoice {invoice_id}: {e}")
            return None
    
    async def process_payment(self, invoice_id: int) -> bool:
        """
        Process a paid invoice and activate premium subscription.
        Returns True if successful.
        """
        try:
            # Get payment from database
            payment = db.get_payment_by_invoice(invoice_id)
            if not payment:
                logger.error(f"Payment not found for invoice {invoice_id}")
                return False
            
            if payment['status'] == 'paid':
                logger.info(f"Payment {invoice_id} already processed")
                return True
            
            # Verify payment with CryptoBot
            status = await self.check_invoice(invoice_id)
            if status != 'paid':
                logger.warning(f"Invoice {invoice_id} status is {status}, not paid")
                return False
            
            # Update payment status
            db.update_payment_status(invoice_id, 'paid')
            
            # Check if this is a renewal
            is_renewal = db.has_previous_subscription(payment['user_id'])
            
            # Get plan info
            plan = PREMIUM_PLANS.get(payment['plan_type'])
            if not plan:
                logger.error(f"Invalid plan type: {payment['plan_type']}")
                return False
            
            # Create premium subscription
            db.create_premium_subscription(
                user_id=payment['user_id'],
                plan_type=payment['plan_type'],
                price_paid=payment['amount'],
                duration_days=plan['duration_days'],
                currency=payment['currency'],
                is_renewal=is_renewal
            )
            
            logger.info(f"Premium activated for user {payment['user_id']}, plan {payment['plan_type']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing payment {invoice_id}: {e}")
            return False
    
    async def setup_webhook(self, callback: Callable) -> bool:
        """
        Setup webhook handler for payment updates.
        Note: This is called when using long polling for updates.
        """
        if not self.is_configured:
            return False
        
        try:
            # Register the update handler
            @self._crypto.pay_handler()
            async def payment_handler(update: CryptoUpdate):
                if update.update_type == "invoice_paid":
                    invoice = update.payload
                    logger.info(f"Received payment for invoice {invoice.invoice_id}")
                    await callback(invoice)
            
            return True
        except Exception as e:
            logger.error(f"Error setting up webhook: {e}")
            return False
    
    async def start_polling(self):
        """Start polling for payment updates"""
        if not self.is_configured:
            return
        
        try:
            logger.info("Starting CryptoBot payment polling...")
            await self._crypto.start_polling()
        except Exception as e:
            logger.error(f"Error in payment polling: {e}")
    
    async def close(self):
        """Close the CryptoBot session"""
        if self._crypto:
            try:
                await self._crypto.close()
            except Exception as e:
                logger.error(f"Error closing CryptoBot session: {e}")


# Premium features list
PREMIUM_FEATURES = {
    "en": [
        "Unlimited group protections",
        "Advanced anti-spam filters",
        "Custom verification types",
        "Priority support",
        "No broadcast messages from bot",
        "Custom welcome messages with media",
        "Advanced statistics & analytics",
        "Whitelist management",
        "Auto-moderation rules",
        "Export group data"
    ],
    "id": [
        "Proteksi grup tanpa batas",
        "Filter anti-spam tingkat lanjut",
        "Tipe verifikasi kustom",
        "Dukungan prioritas",
        "Tidak ada pesan broadcast dari bot",
        "Pesan selamat datang kustom dengan media",
        "Statistik & analitik lengkap",
        "Manajemen whitelist",
        "Aturan auto-moderasi",
        "Ekspor data grup"
    ]
}


def get_premium_features(lang: str = "en") -> list:
    """Get list of premium features"""
    return PREMIUM_FEATURES.get(lang, PREMIUM_FEATURES["en"])


# Global payment service instance
payment_service = PaymentService()

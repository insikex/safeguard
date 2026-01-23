"""
Pakasir Payment Service
========================
QRIS payment integration using Pakasir.com API for Indonesian users.
Documentation: https://pakasir.com/p/docs

Pricing follows real-time USD to IDR exchange rates.
"""

import logging
import httpx
import io
import base64
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

from bot.config import config
from bot.services.database import db
from bot.services.exchange_rate import exchange_rate_service, get_current_rate

logger = logging.getLogger(__name__)


# Pakasir API Base URL
PAKASIR_API_BASE = "https://app.pakasir.com/api"


# Premium plan configurations in USD (converted to IDR at real-time rates)
PREMIUM_PLANS_USD = {
    "1_month": {
        "name": "1 Month Premium",
        "name_id": "Premium 1 Bulan",
        "duration_days": 30,
        "price_usd": 3.0,  # $3 USD
        "original_price_usd": 3.0,
        "discount": 0,
    },
    "3_months": {
        "name": "3 Months Premium",
        "name_id": "Premium 3 Bulan",
        "duration_days": 90,
        "price_usd": 6.0,  # $6 USD (33% off from $9)
        "original_price_usd": 9.0,
        "discount": 33,  # 33% off
    },
    "6_months": {
        "name": "6 Months Premium",
        "name_id": "Premium 6 Bulan",
        "duration_days": 180,
        "price_usd": 9.0,  # $9 USD (50% off from $18)
        "original_price_usd": 18.0,
        "discount": 50,  # 50% off
    }
}

# Legacy static IDR pricing (used as fallback if exchange rate unavailable)
PREMIUM_PLANS_IDR = {
    "1_month": {
        "name": "1 Month Premium",
        "name_id": "Premium 1 Bulan",
        "duration_days": 30,
        "price_idr": 50000,  # Rp 50.000
        "original_price_idr": 50000,
        "discount": 0,
    },
    "3_months": {
        "name": "3 Months Premium",
        "name_id": "Premium 3 Bulan",
        "duration_days": 90,
        "price_idr": 100000,  # Rp 100.000
        "original_price_idr": 150000,
        "discount": 33,  # 33% off
    },
    "6_months": {
        "name": "6 Months Premium",
        "name_id": "Premium 6 Bulan",
        "duration_days": 180,
        "price_idr": 150000,  # Rp 150.000
        "original_price_idr": 300000,
        "discount": 50,  # 50% off
    }
}


@dataclass
class PakasirPayment:
    """Pakasir Payment Response Data"""
    project: str
    order_id: str
    amount: int
    fee: int
    total_payment: int
    payment_method: str
    payment_number: str  # QR string for QRIS
    expired_at: str
    
    @property
    def qr_string(self) -> str:
        """Get QR string for QRIS"""
        return self.payment_number


@dataclass
class PakasirTransactionStatus:
    """Pakasir Transaction Status"""
    order_id: str
    amount: int
    project: str
    status: str  # pending, completed, expired, cancelled
    payment_method: str
    completed_at: Optional[str] = None


class PakasirService:
    """Pakasir QRIS Payment Service with Real-time Exchange Rates"""
    
    _instance = None
    _cached_rate: float = 16000.0  # Fallback rate
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the Pakasir service"""
        self.project_slug = getattr(config, 'pakasir_project_slug', '')
        self.api_key = getattr(config, 'pakasir_api_key', '')
        self.is_sandbox = getattr(config, 'pakasir_sandbox', True)
        
        if self.is_configured:
            logger.info(f"Pakasir initialized - Project: {self.project_slug}, Mode: {'sandbox' if self.is_sandbox else 'production'}")
    
    @property
    def is_configured(self) -> bool:
        """Check if Pakasir is properly configured"""
        return bool(self.project_slug) and bool(self.api_key)
    
    async def get_exchange_rate(self) -> Tuple[float, str]:
        """
        Get current USD to IDR exchange rate.
        Returns tuple of (rate, source).
        """
        rate, source = await get_current_rate()
        self._cached_rate = rate  # Cache for sync methods
        return rate, source
    
    def _convert_usd_to_idr(self, usd_amount: float, rate: float) -> int:
        """
        Convert USD to IDR and round to nearest 1000.
        """
        idr_raw = usd_amount * rate
        return int(round(idr_raw / 1000) * 1000)
    
    async def get_plan_info_dynamic(self, plan_type: str, lang: str = "id") -> Optional[Dict[str, Any]]:
        """
        Get plan information with real-time IDR pricing.
        Uses current USD to IDR exchange rate.
        """
        plan = PREMIUM_PLANS_USD.get(plan_type)
        if not plan:
            return None
        
        # Get current exchange rate
        rate, source = await self.get_exchange_rate()
        
        # Calculate IDR prices
        price_idr = self._convert_usd_to_idr(plan["price_usd"], rate)
        original_price_idr = self._convert_usd_to_idr(plan["original_price_usd"], rate)
        
        name_key = "name_id" if lang == "id" else "name"
        return {
            "type": plan_type,
            "name": plan[name_key],
            "duration_days": plan["duration_days"],
            "price_usd": plan["price_usd"],
            "price_idr": price_idr,
            "original_price_usd": plan["original_price_usd"],
            "original_price_idr": original_price_idr,
            "discount": plan["discount"],
            "exchange_rate": rate,
            "rate_source": source
        }
    
    def get_plan_info(self, plan_type: str, lang: str = "id") -> Optional[Dict[str, Any]]:
        """
        Get plan information in IDR (sync version, uses cached rate).
        For async operations, use get_plan_info_dynamic.
        """
        plan = PREMIUM_PLANS_USD.get(plan_type)
        if not plan:
            # Fallback to legacy static pricing
            legacy = PREMIUM_PLANS_IDR.get(plan_type)
            if not legacy:
                return None
            name_key = "name_id" if lang == "id" else "name"
            return {
                "type": plan_type,
                "name": legacy[name_key],
                "duration_days": legacy["duration_days"],
                "price_idr": legacy["price_idr"],
                "original_price_idr": legacy["original_price_idr"],
                "discount": legacy["discount"]
            }
        
        # Use cached rate for sync conversion
        rate = self._cached_rate
        price_idr = self._convert_usd_to_idr(plan["price_usd"], rate)
        original_price_idr = self._convert_usd_to_idr(plan["original_price_usd"], rate)
        
        name_key = "name_id" if lang == "id" else "name"
        return {
            "type": plan_type,
            "name": plan[name_key],
            "duration_days": plan["duration_days"],
            "price_usd": plan["price_usd"],
            "price_idr": price_idr,
            "original_price_usd": plan["original_price_usd"],
            "original_price_idr": original_price_idr,
            "discount": plan["discount"]
        }
    
    async def get_plan_price_dynamic(self, plan_type: str, is_renewal: bool = False) -> Tuple[int, float, float]:
        """
        Get the price for a plan in IDR using real-time exchange rate.
        
        Returns:
            Tuple of (price_idr, price_usd, exchange_rate)
        """
        plan = PREMIUM_PLANS_USD.get(plan_type)
        if not plan:
            return 0, 0.0, 0.0
        
        rate, _ = await self.get_exchange_rate()
        price_idr = self._convert_usd_to_idr(plan["price_usd"], rate)
        
        return price_idr, plan["price_usd"], rate
    
    def get_plan_price(self, plan_type: str, is_renewal: bool = False) -> int:
        """
        Get the price for a plan in IDR (sync version, uses cached rate).
        For async operations with fresh rate, use get_plan_price_dynamic.
        """
        plan = PREMIUM_PLANS_USD.get(plan_type)
        if not plan:
            # Fallback to legacy static pricing
            legacy = PREMIUM_PLANS_IDR.get(plan_type)
            if not legacy:
                return 0
            return legacy["price_idr"]
        
        # Use cached rate for sync conversion
        return self._convert_usd_to_idr(plan["price_usd"], self._cached_rate)
    
    def get_usd_price(self, plan_type: str) -> float:
        """Get the USD price for a plan"""
        plan = PREMIUM_PLANS_USD.get(plan_type)
        if not plan:
            return 0.0
        return plan["price_usd"]
    
    async def get_all_plans_with_prices(self, lang: str = "id") -> Dict[str, Dict[str, Any]]:
        """
        Get all plans with real-time pricing information.
        """
        rate, source = await self.get_exchange_rate()
        
        result = {}
        for plan_type, plan in PREMIUM_PLANS_USD.items():
            price_idr = self._convert_usd_to_idr(plan["price_usd"], rate)
            original_price_idr = self._convert_usd_to_idr(plan["original_price_usd"], rate)
            
            name_key = "name_id" if lang == "id" else "name"
            result[plan_type] = {
                "name": plan[name_key],
                "duration_days": plan["duration_days"],
                "price_usd": plan["price_usd"],
                "price_idr": price_idr,
                "original_price_usd": plan["original_price_usd"],
                "original_price_idr": original_price_idr,
                "discount": plan["discount"]
            }
        
        return result
    
    def _generate_order_id(self, user_id: int, plan_type: str) -> str:
        """Generate unique order ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"SFG{user_id}_{plan_type[:2].upper()}_{timestamp}"
    
    async def create_qris_payment(
        self,
        user_id: int,
        plan_type: str,
        is_renewal: bool = False
    ) -> Optional[PakasirPayment]:
        """
        Create a QRIS payment via Pakasir API.
        Uses real-time USD to IDR exchange rate.
        Returns payment info with QR string.
        """
        if not self.is_configured:
            logger.error("Pakasir is not configured")
            return None
        
        plan = PREMIUM_PLANS_USD.get(plan_type)
        if not plan:
            logger.error(f"Invalid plan type: {plan_type}")
            return None
        
        # Get real-time price in IDR
        amount, price_usd, rate = await self.get_plan_price_dynamic(plan_type, is_renewal)
        order_id = self._generate_order_id(user_id, plan_type)
        
        logger.info(f"Creating payment for {plan_type}: ${price_usd} USD = Rp {amount:,} IDR (rate: {rate:,.2f})")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{PAKASIR_API_BASE}/transactioncreate/qris",
                    json={
                        "project": self.project_slug,
                        "order_id": order_id,
                        "amount": amount,
                        "api_key": self.api_key
                    },
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code != 200:
                    logger.error(f"Pakasir API error: {response.status_code} - {response.text}")
                    return None
                
                data = response.json()
                
                if "payment" not in data:
                    logger.error(f"Invalid Pakasir response: {data}")
                    return None
                
                payment_data = data["payment"]
                
                payment = PakasirPayment(
                    project=payment_data.get("project", ""),
                    order_id=payment_data.get("order_id", ""),
                    amount=payment_data.get("amount", 0),
                    fee=payment_data.get("fee", 0),
                    total_payment=payment_data.get("total_payment", 0),
                    payment_method=payment_data.get("payment_method", "qris"),
                    payment_number=payment_data.get("payment_number", ""),
                    expired_at=payment_data.get("expired_at", "")
                )
                
                # Store payment in database
                db.create_pakasir_payment(
                    user_id=user_id,
                    order_id=order_id,
                    plan_type=plan_type,
                    amount=amount,
                    fee=payment.fee,
                    total_payment=payment.total_payment,
                    qr_string=payment.payment_number,
                    expired_at=payment.expired_at
                )
                
                logger.info(f"Created Pakasir QRIS payment: {order_id} for user {user_id}, amount Rp {amount}")
                
                return payment
                
        except Exception as e:
            logger.error(f"Error creating Pakasir payment: {e}")
            return None
    
    async def check_payment_status(self, order_id: str, amount: int) -> Optional[PakasirTransactionStatus]:
        """
        Check payment status via Pakasir API.
        Returns transaction status.
        """
        if not self.is_configured:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{PAKASIR_API_BASE}/transactiondetail",
                    params={
                        "project": self.project_slug,
                        "order_id": order_id,
                        "amount": amount,
                        "api_key": self.api_key
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Pakasir status check error: {response.status_code} - {response.text}")
                    return None
                
                data = response.json()
                
                if "transaction" not in data:
                    logger.error(f"Invalid Pakasir status response: {data}")
                    return None
                
                tx_data = data["transaction"]
                
                return PakasirTransactionStatus(
                    order_id=tx_data.get("order_id", ""),
                    amount=tx_data.get("amount", 0),
                    project=tx_data.get("project", ""),
                    status=tx_data.get("status", "pending"),
                    payment_method=tx_data.get("payment_method", "qris"),
                    completed_at=tx_data.get("completed_at")
                )
                
        except Exception as e:
            logger.error(f"Error checking Pakasir payment status: {e}")
            return None
    
    async def simulate_payment(self, order_id: str, amount: int) -> bool:
        """
        Simulate payment (only works in Sandbox mode).
        For testing purposes.
        """
        if not self.is_configured or not self.is_sandbox:
            return False
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{PAKASIR_API_BASE}/paymentsimulation",
                    json={
                        "project": self.project_slug,
                        "order_id": order_id,
                        "amount": amount,
                        "api_key": self.api_key
                    },
                    headers={"Content-Type": "application/json"}
                )
                
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Error simulating payment: {e}")
            return False
    
    async def cancel_payment(self, order_id: str, amount: int) -> bool:
        """Cancel a pending payment"""
        if not self.is_configured:
            return False
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{PAKASIR_API_BASE}/transactioncancel",
                    json={
                        "project": self.project_slug,
                        "order_id": order_id,
                        "amount": amount,
                        "api_key": self.api_key
                    },
                    headers={"Content-Type": "application/json"}
                )
                
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Error cancelling payment: {e}")
            return False
    
    async def process_payment(self, order_id: str) -> bool:
        """
        Process a completed payment and activate premium subscription.
        Returns True if successful.
        """
        try:
            # Get payment from database
            payment = db.get_pakasir_payment_by_order(order_id)
            if not payment:
                logger.error(f"Payment not found for order {order_id}")
                return False
            
            if payment['status'] == 'completed':
                logger.info(f"Payment {order_id} already processed")
                return True
            
            # Verify payment with Pakasir API
            status = await self.check_payment_status(order_id, payment['amount'])
            if not status or status.status != 'completed':
                logger.warning(f"Payment {order_id} status is {status.status if status else 'unknown'}, not completed")
                return False
            
            # Update payment status
            db.update_pakasir_payment_status(order_id, 'completed', status.completed_at)
            
            # Check if this is a renewal
            is_renewal = db.has_previous_subscription(payment['user_id'])
            
            # Get plan info
            plan = PREMIUM_PLANS_IDR.get(payment['plan_type'])
            if not plan:
                logger.error(f"Invalid plan type: {payment['plan_type']}")
                return False
            
            # Create premium subscription
            db.create_premium_subscription(
                user_id=payment['user_id'],
                plan_type=payment['plan_type'],
                price_paid=payment['amount'],
                duration_days=plan['duration_days'],
                currency="IDR",
                is_renewal=is_renewal
            )
            
            logger.info(f"Premium activated for user {payment['user_id']}, plan {payment['plan_type']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing payment {order_id}: {e}")
            return False
    
    def generate_qr_image_base64(self, qr_string: str) -> Optional[str]:
        """
        Generate QR code image from QR string.
        Returns base64 encoded PNG image.
        """
        if not HAS_QRCODE:
            logger.warning("qrcode library not installed, cannot generate QR image")
            return None
        
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_string)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to bytes
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            # Encode to base64
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error generating QR image: {e}")
            return None
    
    def generate_qr_image_bytes(self, qr_string: str) -> Optional[bytes]:
        """
        Generate QR code image from QR string.
        Returns PNG image bytes for sending via Telegram.
        """
        if not HAS_QRCODE:
            logger.warning("qrcode library not installed, cannot generate QR image")
            return None
        
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_string)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to bytes
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating QR image: {e}")
            return None


def format_rupiah(amount: int) -> str:
    """Format amount as Indonesian Rupiah"""
    return f"Rp {amount:,}".replace(",", ".")


# Premium features list for Indonesian market
PREMIUM_FEATURES_ID = [
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


def get_premium_features_id() -> list:
    """Get list of premium features in Indonesian"""
    return PREMIUM_FEATURES_ID


# Global Pakasir service instance
pakasir_service = PakasirService()

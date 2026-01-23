"""
Pakasir Payment Service
========================
QRIS payment integration using Pakasir.com API for Indonesian users.
Documentation: https://pakasir.com/p/docs
"""

import logging
import httpx
import io
import base64
from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

from bot.config import config
from bot.services.database import db

logger = logging.getLogger(__name__)


# Pakasir API Base URL
PAKASIR_API_BASE = "https://app.pakasir.com/api"


# Premium plan configurations in IDR (Rupiah)
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
    """Pakasir QRIS Payment Service"""
    
    _instance = None
    
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
    
    def get_plan_info(self, plan_type: str, lang: str = "id") -> Optional[Dict[str, Any]]:
        """Get plan information in IDR"""
        plan = PREMIUM_PLANS_IDR.get(plan_type)
        if not plan:
            return None
        
        name_key = "name_id" if lang == "id" else "name"
        return {
            "type": plan_type,
            "name": plan[name_key],
            "duration_days": plan["duration_days"],
            "price_idr": plan["price_idr"],
            "original_price_idr": plan["original_price_idr"],
            "discount": plan["discount"]
        }
    
    def get_plan_price(self, plan_type: str, is_renewal: bool = False) -> int:
        """Get the price for a plan in IDR"""
        plan = PREMIUM_PLANS_IDR.get(plan_type)
        if not plan:
            return 0
        return plan["price_idr"]
    
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
        Returns payment info with QR string.
        """
        if not self.is_configured:
            logger.error("Pakasir is not configured")
            return None
        
        plan = PREMIUM_PLANS_IDR.get(plan_type)
        if not plan:
            logger.error(f"Invalid plan type: {plan_type}")
            return None
        
        amount = self.get_plan_price(plan_type, is_renewal)
        order_id = self._generate_order_id(user_id, plan_type)
        
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

"""
Payment Service - CryptoBot Integration
========================================
Handles payment processing via CryptoBot (Crypto Pay API)
API Documentation: https://help.send.tg/en/articles/10279948-crypto-pay-api
"""

import aiohttp
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class PremiumPlan(Enum):
    """Premium subscription plans"""
    MONTHLY = "monthly"      # 1 month - $10
    QUARTERLY = "quarterly"  # 3 months - $18
    BIANNUAL = "biannual"    # 6 months - $50 (50% off from $100)


@dataclass
class PlanDetails:
    """Details of a premium plan"""
    name: str
    duration_days: int
    price: float
    original_price: float  # For showing discount
    discount_percent: int
    description: str


# Premium plan configurations
PREMIUM_PLANS: Dict[str, PlanDetails] = {
    PremiumPlan.MONTHLY.value: PlanDetails(
        name="Premium Monthly",
        duration_days=30,
        price=10.0,
        original_price=10.0,
        discount_percent=0,
        description="1 Month Premium"
    ),
    PremiumPlan.QUARTERLY.value: PlanDetails(
        name="Premium Quarterly",
        duration_days=90,
        price=18.0,
        original_price=30.0,  # Would be $30 at monthly rate
        discount_percent=40,
        description="3 Months Premium"
    ),
    PremiumPlan.BIANNUAL.value: PlanDetails(
        name="Premium Biannual",
        duration_days=180,
        price=50.0,
        original_price=100.0,  # 50% discount
        discount_percent=50,
        description="6 Months Premium (50% OFF!)"
    ),
}


class CryptoPayService:
    """Service for handling CryptoBot payments"""
    
    # API endpoints
    MAINNET_URL = "https://pay.crypt.bot/api"
    TESTNET_URL = "https://testnet-pay.crypt.bot/api"
    
    def __init__(self, api_token: str, testnet: bool = False):
        """
        Initialize CryptoBot payment service
        
        Args:
            api_token: CryptoBot API token from @CryptoBot
            testnet: Use testnet for testing (default: False)
        """
        self.api_token = api_token
        self.base_url = self.TESTNET_URL if testnet else self.MAINNET_URL
        self._session: Optional[aiohttp.ClientSession] = None
    
    @property
    def headers(self) -> Dict[str, str]:
        """Get API headers"""
        return {
            "Crypto-Pay-API-Token": self.api_token,
            "Content-Type": "application/json"
        }
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """Close the session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _request(self, method: str, endpoint: str, 
                       data: Dict = None) -> Optional[Dict[str, Any]]:
        """Make API request to CryptoBot"""
        url = f"{self.base_url}/{endpoint}"
        session = await self._get_session()
        
        try:
            async with session.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data
            ) as response:
                result = await response.json()
                
                if result.get("ok"):
                    return result.get("result")
                else:
                    error = result.get("error", {})
                    logger.error(f"CryptoBot API error: {error}")
                    return None
                    
        except Exception as e:
            logger.error(f"CryptoBot request failed: {e}")
            return None
    
    async def get_me(self) -> Optional[Dict[str, Any]]:
        """
        Get basic information about the app
        Returns app_id, name, payment_processing_bot_username
        """
        return await self._request("GET", "getMe")
    
    async def get_balance(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get balances of the app
        Returns list of balances by currency
        """
        return await self._request("GET", "getBalance")
    
    async def create_invoice(
        self,
        user_id: int,
        plan: str,
        currency: str = "USDT",
        description: str = None,
        payload: str = None,
        paid_btn_name: str = "callback",
        paid_btn_url: str = None,
        expires_in: int = 3600  # 1 hour default
    ) -> Optional[Dict[str, Any]]:
        """
        Create a payment invoice
        
        Args:
            user_id: Telegram user ID
            plan: Premium plan (monthly, quarterly, biannual)
            currency: Cryptocurrency code (USDT, TON, BTC, etc.)
            description: Invoice description
            payload: Custom payload data
            paid_btn_name: Button shown after payment (callback, viewItem, openChannel, openBot)
            paid_btn_url: URL for the button
            expires_in: Invoice expiry time in seconds
        
        Returns:
            Invoice data including invoice_id and pay_url
        """
        plan_details = PREMIUM_PLANS.get(plan)
        if not plan_details:
            logger.error(f"Invalid plan: {plan}")
            return None
        
        # Prepare payload
        if payload is None:
            payload = f"{user_id}:{plan}"
        
        if description is None:
            description = f"Safeguard Bot {plan_details.description}"
        
        data = {
            "currency_type": "fiat",  # Use fiat pricing, auto-convert to crypto
            "fiat": "USD",
            "amount": str(plan_details.price),
            "description": description,
            "payload": payload,
            "expires_in": expires_in,
            "allow_comments": False,
            "allow_anonymous": False
        }
        
        # Add button for after payment
        if paid_btn_name and paid_btn_url:
            data["paid_btn_name"] = paid_btn_name
            data["paid_btn_url"] = paid_btn_url
        
        result = await self._request("POST", "createInvoice", data)
        
        if result:
            logger.info(f"Invoice created for user {user_id}: {result.get('invoice_id')}")
        
        return result
    
    async def get_invoices(
        self,
        invoice_ids: List[str] = None,
        status: str = None,
        offset: int = 0,
        count: int = 100
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get invoices with optional filters
        
        Args:
            invoice_ids: List of invoice IDs to get
            status: Filter by status (active, paid, expired)
            offset: Pagination offset
            count: Number of invoices to return
        
        Returns:
            List of invoice objects
        """
        data = {
            "offset": offset,
            "count": count
        }
        
        if invoice_ids:
            data["invoice_ids"] = ",".join(str(i) for i in invoice_ids)
        
        if status:
            data["status"] = status
        
        return await self._request("GET", "getInvoices", data)
    
    async def get_invoice_status(self, invoice_id: str) -> Optional[str]:
        """
        Get status of a specific invoice
        
        Returns: 'active', 'paid', or 'expired'
        """
        result = await self.get_invoices(invoice_ids=[invoice_id])
        
        if result and len(result) > 0:
            return result[0].get("status")
        
        return None
    
    async def check_invoice_paid(self, invoice_id: str) -> bool:
        """Check if an invoice has been paid"""
        status = await self.get_invoice_status(invoice_id)
        return status == "paid"
    
    async def delete_invoice(self, invoice_id: str) -> bool:
        """
        Delete an invoice
        
        Args:
            invoice_id: Invoice ID to delete
        
        Returns:
            True if successful
        """
        result = await self._request("POST", "deleteInvoice", {
            "invoice_id": invoice_id
        })
        return result is not None
    
    async def get_currencies(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get list of supported cryptocurrencies
        """
        return await self._request("GET", "getCurrencies")
    
    async def get_exchange_rates(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get current exchange rates
        """
        return await self._request("GET", "getExchangeRates")


# Global instance (initialized later with config)
crypto_pay: Optional[CryptoPayService] = None


def init_crypto_pay(api_token: str, testnet: bool = False) -> CryptoPayService:
    """Initialize the global CryptoBot service"""
    global crypto_pay
    crypto_pay = CryptoPayService(api_token, testnet)
    return crypto_pay


def get_plan_details(plan: str) -> Optional[PlanDetails]:
    """Get details for a premium plan"""
    return PREMIUM_PLANS.get(plan)


def get_all_plans() -> Dict[str, PlanDetails]:
    """Get all available premium plans"""
    return PREMIUM_PLANS

"""
Exchange Rate Service
======================
Real-time USD to IDR exchange rate fetcher with caching.
Supports multiple API providers for reliability.
"""

import logging
import asyncio
from typing import Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)


@dataclass
class ExchangeRateCache:
    """Cached exchange rate data"""
    rate: float
    source: str
    timestamp: datetime
    
    def is_expired(self, max_age_minutes: int = 60) -> bool:
        """Check if cache is expired"""
        return datetime.now() - self.timestamp > timedelta(minutes=max_age_minutes)


class ExchangeRateService:
    """
    Real-time USD to IDR exchange rate service.
    Uses multiple API sources for reliability with smart caching.
    """
    
    _instance = None
    _cache: Optional[ExchangeRateCache] = None
    _lock: asyncio.Lock = None
    
    # Default fallback rate (approximately current market rate)
    DEFAULT_FALLBACK_RATE = 16000.0
    
    # Cache duration in minutes
    CACHE_DURATION_MINUTES = 30
    
    # API endpoints for exchange rates (free tier APIs)
    API_SOURCES = [
        {
            "name": "ExchangeRate-API",
            "url": "https://api.exchangerate-api.com/v4/latest/USD",
            "parser": lambda data: data.get("rates", {}).get("IDR")
        },
        {
            "name": "Fawaz Ahmed",
            "url": "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json",
            "parser": lambda data: data.get("usd", {}).get("idr")
        },
        {
            "name": "Currency API (Github)",
            "url": "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.min.json",
            "parser": lambda data: data.get("usd", {}).get("idr")
        },
        {
            "name": "Open Exchange Rates",
            "url": "https://open.er-api.com/v6/latest/USD",
            "parser": lambda data: data.get("rates", {}).get("IDR")
        }
    ]
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._lock = asyncio.Lock()
        return cls._instance
    
    def __init__(self):
        """Initialize the exchange rate service"""
        if self._cache is None:
            logger.info("Exchange Rate Service initialized")
    
    async def get_usd_to_idr_rate(self, force_refresh: bool = False) -> Tuple[float, str]:
        """
        Get current USD to IDR exchange rate.
        
        Returns:
            Tuple of (rate, source_name)
        """
        async with self._lock:
            # Check cache first
            if not force_refresh and self._cache and not self._cache.is_expired(self.CACHE_DURATION_MINUTES):
                logger.debug(f"Using cached rate: {self._cache.rate} from {self._cache.source}")
                return self._cache.rate, f"{self._cache.source} (cached)"
            
            # Fetch fresh rate
            rate, source = await self._fetch_rate()
            
            if rate:
                # Update cache
                self._cache = ExchangeRateCache(
                    rate=rate,
                    source=source,
                    timestamp=datetime.now()
                )
                logger.info(f"Updated exchange rate: 1 USD = {rate:,.2f} IDR (from {source})")
                return rate, source
            
            # Use cached rate if available (even if expired)
            if self._cache:
                logger.warning(f"Using expired cached rate: {self._cache.rate}")
                return self._cache.rate, f"{self._cache.source} (expired cache)"
            
            # Fallback to default
            logger.warning(f"Using default fallback rate: {self.DEFAULT_FALLBACK_RATE}")
            return self.DEFAULT_FALLBACK_RATE, "fallback"
    
    async def _fetch_rate(self) -> Tuple[Optional[float], str]:
        """
        Fetch exchange rate from multiple API sources.
        Tries each source until one succeeds.
        """
        for source in self.API_SOURCES:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(source["url"])
                    
                    if response.status_code == 200:
                        data = response.json()
                        rate = source["parser"](data)
                        
                        if rate and isinstance(rate, (int, float)) and rate > 0:
                            return float(rate), source["name"]
                        
            except httpx.TimeoutException:
                logger.warning(f"Timeout fetching from {source['name']}")
            except httpx.RequestError as e:
                logger.warning(f"Request error from {source['name']}: {e}")
            except Exception as e:
                logger.warning(f"Error fetching from {source['name']}: {e}")
        
        return None, "none"
    
    def convert_usd_to_idr(self, usd_amount: float, rate: float) -> int:
        """
        Convert USD to IDR and round to nearest 1000.
        
        Args:
            usd_amount: Amount in USD
            rate: Current USD to IDR rate
            
        Returns:
            Amount in IDR (rounded to nearest 1000)
        """
        idr_raw = usd_amount * rate
        # Round to nearest 1000
        return int(round(idr_raw / 1000) * 1000)
    
    def convert_usd_to_idr_exact(self, usd_amount: float, rate: float) -> int:
        """
        Convert USD to IDR without rounding.
        
        Args:
            usd_amount: Amount in USD
            rate: Current USD to IDR rate
            
        Returns:
            Amount in IDR (exact)
        """
        return int(usd_amount * rate)
    
    async def get_formatted_rate(self) -> str:
        """
        Get formatted exchange rate string for display.
        
        Returns:
            Formatted string like "1 USD = Rp 16.000"
        """
        rate, source = await self.get_usd_to_idr_rate()
        return f"1 USD = Rp {rate:,.0f}".replace(",", ".")
    
    def get_cached_rate(self) -> Optional[float]:
        """
        Get cached rate without fetching.
        Returns None if no cache available.
        """
        if self._cache:
            return self._cache.rate
        return None
    
    def get_cached_rate_sync(self) -> float:
        """
        Synchronous method to get cached rate.
        Returns fallback rate if no cache.
        """
        if self._cache:
            return self._cache.rate
        return self.DEFAULT_FALLBACK_RATE
    
    def clear_cache(self):
        """Clear the cached rate"""
        self._cache = None
        logger.info("Exchange rate cache cleared")


# Global service instance
exchange_rate_service = ExchangeRateService()


async def get_current_rate() -> Tuple[float, str]:
    """Convenience function to get current rate"""
    return await exchange_rate_service.get_usd_to_idr_rate()


def usd_to_idr(usd_amount: float, rate: float) -> int:
    """Convenience function to convert USD to IDR"""
    return exchange_rate_service.convert_usd_to_idr(usd_amount, rate)

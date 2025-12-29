"""
Price Tracker Module

Real-time price tracking from Binance API with caching fallback.
"""

import time
import logging
import os
import requests
import ast
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PriceData:
    """Cached price data."""
    symbol: str
    price: float
    timestamp: int


class PriceTracker:
    """
    Price tracker for real-time market prices from Binance.
    
    Features:
    - Fetches prices from Binance API
    - Caches prices for fallback when API unavailable
    - Supports batch price updates
    """
    
    BINANCE_API_ENDPOINTS = (
        "https://fapi.binance.com/fapi/v1/ticker/price",
        "https://data-api.binance.vision/fapi/v1/ticker/price",
        "https://api.binance.com/api/v3/ticker/price",
        "https://data-api.binance.vision/api/v3/ticker/price",
    )
    
    def __init__(self, cache_ttl_seconds: int = 60, proxies: Optional[Dict[str, str]] = None):
        """
        Initialize price tracker.
        
        Args:
            cache_ttl_seconds: How long cached prices remain valid
            proxies: Optional requests proxies dict, e.g. {"http": "...", "https": "..."}
        """
        self.cache_ttl = cache_ttl_seconds
        self.price_cache: Dict[str, PriceData] = {}
        self._retry_count = 3
        self._retry_delay = 1  # seconds

        self._proxies: Optional[Dict[str, str]] = proxies
        self._proxies_loaded_at = 0.0
        self._warned_no_proxy = False
        if proxies is None:
            self._reload_proxies(force=True)

    @staticmethod
    def _read_config_value(path: Path, key: str):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None

        try:
            tree = ast.parse(text)
        except Exception:
            return None

        for node in getattr(tree, "body", []) or []:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets or []:
                if isinstance(target, ast.Name) and target.id == key:
                    try:
                        return ast.literal_eval(node.value)
                    except Exception:
                        return None
        return None

    @classmethod
    def _resolve_requests_proxies(cls) -> Optional[Dict[str, str]]:
        env_proxy = (
            (os.getenv("VALUESCAN_SOCKS5_PROXY") or "").strip()
            or (os.getenv("SOCKS5_PROXY") or "").strip()
        )
        if env_proxy:
            return {"http": env_proxy, "https": env_proxy}

        env_http_proxy = (
            (os.getenv("VALUESCAN_HTTP_PROXY") or "").strip()
            or (os.getenv("HTTPS_PROXY") or "").strip()
            or (os.getenv("HTTP_PROXY") or "").strip()
        )
        if env_http_proxy:
            return {"http": env_http_proxy, "https": env_http_proxy}

        base_dir = Path(__file__).resolve().parents[1]
        candidates = [
            base_dir / "binance_trader" / "config.py",
            base_dir / "signal_monitor" / "config.py",
            Path("/opt/valuescan/binance_trader/config.py"),
            Path("/opt/valuescan/signal_monitor/config.py"),
        ]
        for cfg_path in candidates:
            if not cfg_path.exists():
                continue
            val = cls._read_config_value(cfg_path, "SOCKS5_PROXY")
            if isinstance(val, str) and val.strip():
                proxy = val.strip()
                return {"http": proxy, "https": proxy}

            val = cls._read_config_value(cfg_path, "HTTP_PROXY")
            if isinstance(val, str) and val.strip():
                proxy = val.strip()
                return {"http": proxy, "https": proxy}
        return None

    def _reload_proxies(self, force: bool = False) -> None:
        # Reload at most once per minute to allow config updates from the dashboard.
        now = time.time()
        if not force and self._proxies_loaded_at and (now - self._proxies_loaded_at) < 60.0:
            return
        try:
            self._proxies = self._resolve_requests_proxies()
        except Exception:
            self._proxies = None
        self._proxies_loaded_at = now

        if self._proxies is None and not self._warned_no_proxy:
            logger.warning("Binance proxy is not configured. Price requests may fail in restricted networks.")
            self._warned_no_proxy = True

    def get_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a symbol.
        
        Tries Binance API first, falls back to cache if unavailable.
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            
        Returns:
            Current price or None if unavailable
        """
        self._reload_proxies()
        # Try to fetch from API
        price = self._fetch_price_from_api(symbol)
        
        if price is not None:
            # Update cache
            self.price_cache[symbol] = PriceData(
                symbol=symbol,
                price=price,
                timestamp=int(time.time() * 1000)
            )
            return price
        
        # Fall back to cache
        return self._get_cached_price(symbol)

    def get_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        Get prices for multiple symbols.
        
        Args:
            symbols: List of trading pairs
            
        Returns:
            Dict mapping symbol to price
        """
        self._reload_proxies()
        prices = {}
        
        # Try batch fetch first
        all_prices = self._fetch_all_prices()

        if not all_prices and self._proxies is None:
            for symbol in symbols:
                cached = self._get_cached_price(symbol)
                if cached is not None:
                    prices[symbol] = cached
            return prices
        
        for symbol in symbols:
            if symbol in all_prices:
                prices[symbol] = all_prices[symbol]
                self.price_cache[symbol] = PriceData(
                    symbol=symbol,
                    price=all_prices[symbol],
                    timestamp=int(time.time() * 1000)
                )
            else:
                # Try individual fetch or cache
                price = self.get_price(symbol)
                if price is not None:
                    prices[symbol] = price
        
        return prices
    
    def _fetch_price_from_api(self, symbol: str) -> Optional[float]:
        """
        Fetch price from Binance API with retry.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Price or None if failed
        """
        for attempt in range(self._retry_count):
            for endpoint in self.BINANCE_API_ENDPOINTS:
                try:
                    response = requests.get(
                        endpoint,
                        params={'symbol': symbol},
                        timeout=5,
                        proxies=self._proxies,
                    )

                    # HTTP 451 is commonly returned when Binance is blocked by region/IP.
                    if response.status_code in (418, 451):
                        continue

                    if response.status_code == 200:
                        data = response.json()
                        return float(data['price'])

                except requests.RequestException as e:
                    logger.warning(
                        f"API request failed (attempt {attempt + 1}) via {endpoint}: {e}"
                    )

            if attempt < self._retry_count - 1:
                time.sleep(self._retry_delay * (2 ** attempt))  # Exponential backoff
        
        logger.warning(f"Failed to fetch price for {symbol} after {self._retry_count} attempts")
        return None
    
    def _fetch_all_prices(self) -> Dict[str, float]:
        """
        Fetch all prices from Binance API.
        
        Returns:
            Dict mapping symbol to price
        """
        for endpoint in self.BINANCE_API_ENDPOINTS:
            try:
                response = requests.get(endpoint, timeout=10, proxies=self._proxies)

                if response.status_code in (418, 451):
                    continue

                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, dict):
                        data = [data]
                    return {item['symbol']: float(item['price']) for item in data}

            except requests.RequestException as e:
                logger.warning(f"Failed to fetch all prices via {endpoint}: {e}")
        
        return {}
    
    def _get_cached_price(self, symbol: str) -> Optional[float]:
        """
        Get price from cache if still valid.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Cached price or None if expired/missing
        """
        if symbol not in self.price_cache:
            return None
        
        cached = self.price_cache[symbol]
        age_ms = int(time.time() * 1000) - cached.timestamp
        
        if age_ms > self.cache_ttl * 1000:
            logger.warning(f"Cache expired for {symbol}, using stale price")
        
        logger.info(f"Using cached price for {symbol}: {cached.price}")
        return cached.price
    
    def update_cache(self, symbol: str, price: float) -> None:
        """
        Manually update price cache.
        
        Args:
            symbol: Trading pair
            price: Price to cache
        """
        self.price_cache[symbol] = PriceData(
            symbol=symbol,
            price=price,
            timestamp=int(time.time() * 1000)
        )
    
    def clear_cache(self) -> None:
        """Clear all cached prices."""
        self.price_cache.clear()

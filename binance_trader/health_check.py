#!/usr/bin/env python3
"""
Binance Futures trading module health check.
- Verifies config.py exists and required fields are set.
- Optionally pings Binance Futures API to confirm connectivity.
Safe to run; it will not place orders.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import List, Tuple

from binance.client import Client
from binance.exceptions import BinanceAPIException


CONFIG_PATH = Path(__file__).parent / "config.py"


class CheckResult:
    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.infos: List[str] = []

    def ok(self) -> bool:
        return not self.errors

    def print(self) -> None:
        print("\n== Health Check ==")
        for msg in self.infos:
            print(f"[INFO] {msg}")
        for msg in self.warnings:
            print(f"[WARN] {msg}")
        for msg in self.errors:
            print(f"[ERR ] {msg}")


def _load_config() -> Tuple[object, CheckResult]:
    result = CheckResult()
    if not CONFIG_PATH.exists():
        result.errors.append(
            f"Missing config.py ({CONFIG_PATH}). Copy config.example.py and fill in your API keys."
        )
        return None, result  # type: ignore[return-value]

    try:
        from binance_trader import config  # type: ignore
        result.infos.append(f"Loaded config.py from {CONFIG_PATH}")
        return config, result
    except Exception as exc:  # pragma: no cover - defensive
        result.errors.append(f"Failed to import config.py: {exc}")
        return None, result  # type: ignore[return-value]


def _is_placeholder(value: str) -> bool:
    placeholders = {"your_api_key_here", "your_api_secret_here", ""}
    return value is None or value in placeholders


def validate_config(cfg) -> CheckResult:
    result = CheckResult()

    # Required: API keys
    api_key = getattr(cfg, "BINANCE_API_KEY", "")
    api_secret = getattr(cfg, "BINANCE_API_SECRET", "")
    if _is_placeholder(api_key) or _is_placeholder(api_secret):
        result.errors.append(
            "API keys are missing or placeholders. Set BINANCE_API_KEY and BINANCE_API_SECRET in config.py."
        )
    else:
        result.infos.append("API keys present.")

    # Trading mode
    use_testnet = getattr(cfg, "USE_TESTNET", True)
    auto_trading = getattr(cfg, "AUTO_TRADING_ENABLED", False)
    if use_testnet:
        result.infos.append("Running in TESTNET mode (safe).")
    else:
        result.warnings.append("USE_TESTNET = False (MAINNET). Double-check risk settings.")
    if auto_trading:
        result.infos.append("AUTO_TRADING_ENABLED = True")
    else:
        result.warnings.append("AUTO_TRADING_ENABLED = False (observation mode).")

    # Symbol suffix sanity
    symbol_suffix = getattr(cfg, "SYMBOL_SUFFIX", "USDT")
    if not symbol_suffix:
        result.errors.append("SYMBOL_SUFFIX is empty; set it to the futures quote asset (e.g., USDT).")

    # Risk limits
    max_pos = getattr(cfg, "MAX_POSITION_PERCENT", None)
    max_total = getattr(cfg, "MAX_TOTAL_POSITION_PERCENT", None)
    major_total = getattr(cfg, "MAJOR_TOTAL_POSITION_PERCENT", None)
    alt_total = getattr(cfg, "ALT_TOTAL_POSITION_PERCENT", None)
    if max_pos is not None and max_pos > 20:
        result.warnings.append(f"MAX_POSITION_PERCENT is high ({max_pos}%).")
    if max_total is not None and max_total > 80:
        result.warnings.append(f"MAX_TOTAL_POSITION_PERCENT is high ({max_total}%).")
    if major_total is not None and major_total > 80:
        result.warnings.append(f"MAJOR_TOTAL_POSITION_PERCENT is high ({major_total}%).")
    if alt_total is not None and alt_total > 80:
        result.warnings.append(f"ALT_TOTAL_POSITION_PERCENT is high ({alt_total}%).")

    return result


def ping_binance(cfg) -> CheckResult:
    result = CheckResult()
    api_key = getattr(cfg, "BINANCE_API_KEY", "")
    api_secret = getattr(cfg, "BINANCE_API_SECRET", "")
    timeout = getattr(cfg, "API_TIMEOUT", 30)
    enable_proxy_fallback = getattr(cfg, "ENABLE_PROXY_FALLBACK", True)

    if _is_placeholder(api_key) or _is_placeholder(api_secret):
        result.errors.append("Skip API ping: API keys not set.")
        return result

    proxy = getattr(cfg, "SOCKS5_PROXY", None)
    requests_params = None
    if proxy:
        requests_params = {"proxies": {"http": proxy, "https": proxy}, "timeout": timeout}
        proxy_display = proxy.split("@")[-1] if "@" in proxy else proxy
        result.infos.append(f"Using SOCKS5 proxy: {proxy_display}")

    client = Client(
        api_key,
        api_secret,
        testnet=getattr(cfg, "USE_TESTNET", True),
        ping=False,
        requests_params=requests_params,
    )
    try:
        client.session.trust_env = False
    except Exception:
        pass
    if getattr(cfg, "USE_TESTNET", True):
        client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"

    def _sync_time(target_client: Client) -> None:
        try:
            server_time = target_client.futures_time().get("serverTime")
            if not server_time:
                return
            local_time = int(time.time() * 1000)
            raw_offset = int(server_time) - local_time
            safety_ms = int(getattr(cfg, "BINANCE_TIME_SYNC_SAFETY_MS", 1500) or 1500)
            target_client.timestamp_offset = raw_offset - safety_ms
        except Exception:
            return

    try:
        client.futures_ping()
        result.infos.append("Binance futures_ping OK.")
    except BinanceAPIException as exc:
        result.errors.append(f"futures_ping failed: {exc}")
        return result
    except Exception as exc:  # pragma: no cover - network defensive
        if proxy and enable_proxy_fallback:
            result.warnings.append(f"Proxy ping error: {exc}")
            result.warnings.append("Retrying futures_ping without proxy...")

            direct_client = Client(
                api_key,
                api_secret,
                testnet=getattr(cfg, "USE_TESTNET", True),
                ping=False,
                requests_params={"timeout": timeout},
            )
            try:
                direct_client.session.trust_env = False
            except Exception:
                pass
            if getattr(cfg, "USE_TESTNET", True):
                direct_client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"

            try:
                direct_client.futures_ping()
                result.infos.append("Binance futures_ping OK (direct).")
                client = direct_client
            except Exception as exc2:  # pragma: no cover - network defensive
                result.errors.append(f"futures_ping error (direct): {exc2}")
                return result
        else:
            result.errors.append(f"futures_ping error: {exc}")
            return result

    try:
        _sync_time(client)
        account = client.futures_account()
        total_wallet = float(account.get("totalWalletBalance", 0))
        available = float(account.get("availableBalance", 0))
        result.infos.append(f"Account balance fetched: total={total_wallet} available={available}")
    except BinanceAPIException as exc:
        result.errors.append(f"futures_account failed: {exc}")
    except Exception as exc:  # pragma: no cover - network defensive
        result.errors.append(f"futures_account error: {exc}")

    return result


def main() -> int:
    cfg, load_result = _load_config()
    load_result.print()
    if not cfg:
        return 1

    cfg_result = validate_config(cfg)
    cfg_result.print()
    if not cfg_result.ok():
        return 1

    print("\nPinging Binance Futures...")
    ping_result = ping_binance(cfg)
    ping_result.print()

    if ping_result.ok():
        print("\nHealth check PASSED.")
        return 0

    print("\nHealth check detected issues.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

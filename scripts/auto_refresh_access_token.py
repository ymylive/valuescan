#!/usr/bin/env python3
"""
Auto refresh access_token via refresh_token.

Checks token validity with the ValuScan API and refreshes only when invalid.
No proactive expiry logic.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict

import requests


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import token_refresher  # type: ignore  # noqa: E402


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _resolve_proxies() -> Optional[Dict[str, str]]:
    proxy = (
        os.getenv("SOCKS5_PROXY")
        or os.getenv("VALUESCAN_SOCKS5_PROXY")
        or os.getenv("VALUESCAN_PROXY")
        or ""
    ).strip()
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def _refresh_once(session: requests.Session, proxies: Optional[Dict[str, str]], force: bool) -> bool:
    data = token_refresher._load_localstorage()
    refresh_token_value = (data.get("refresh_token") or "").strip()
    account_token = (data.get("account_token") or "").strip()
    ticket_value = (data.get("ticket") or "").strip()

    if not refresh_token_value:
        logger.warning("Refresh token missing; cannot auto refresh.")
        return False

    if account_token:
        status, reason = token_refresher._check_api_token_status(session, account_token, proxies=proxies)
    else:
        status, reason = ("missing", "missing_account_token")

    if status == "valid" and not force:
        logger.info("Token still valid; skipping refresh.")
        return True

    if status != "invalid" and not force:
        logger.warning("Token status %s (%s); skipping refresh.", status, reason)
        return True

    updated = token_refresher._refresh(
        session,
        refresh_token_value,
        account_token_value=account_token,
        ticket_value=ticket_value,
        proxies=proxies,
    )
    if not updated:
        logger.warning("Refresh token exchange failed.")
        return False

    data["account_token"] = updated["account_token"]
    data["refresh_token"] = updated["refresh_token"]
    data["last_refresh"] = datetime.now(timezone.utc).isoformat()
    if token_refresher._persist_localstorage(data):
        logger.info("Token refreshed successfully.")
        return True
    logger.warning("Failed to persist refreshed token.")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto refresh access_token via refresh_token")
    parser.add_argument("--interval", type=int, default=30, help="Check interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run one check and exit")
    parser.add_argument("--force", action="store_true", help="Force refresh even if token looks valid")
    args = parser.parse_args()

    session = requests.Session()
    proxies = _resolve_proxies()

    while True:
        _refresh_once(session, proxies, force=args.force)
        if args.once:
            break
        time.sleep(max(5, int(args.interval)))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

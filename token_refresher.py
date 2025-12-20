#!/usr/bin/env python3
"""
ValueScan token refresher.

Keeps `valuescan_localstorage.json` fresh by periodically exchanging refresh_token
for a new account_token.

This module is also used by tests in `tests/test_token_refresher_utils.py`.
"""

from __future__ import annotations

import base64
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import requests


REFRESH_URL = os.getenv("VALUESCAN_REFRESH_URL", "https://api.valuescan.io/api/account/refreshToken")
TOKEN_FILE = Path(os.getenv("VALUESCAN_TOKEN_FILE") or Path(__file__).resolve().parent / "signal_monitor" / "valuescan_localstorage.json")

CHECK_INTERVAL_S = int(os.getenv("VALUESCAN_TOKEN_REFRESH_INTERVAL", "30"))
REFRESH_SAFETY_S = int(os.getenv("VALUESCAN_TOKEN_REFRESH_SAFETY", "120"))
REQUEST_TIMEOUT_S = int(os.getenv("VALUESCAN_TOKEN_REFRESH_TIMEOUT", "15"))


def _b64url_decode(segment: str) -> bytes:
    seg = (segment or "").strip()
    if not seg:
        return b""
    pad = "=" * (-len(seg) % 4)
    return base64.urlsafe_b64decode((seg + pad).encode("ascii", errors="ignore"))


def _jwt_expiry_seconds(token: str) -> Optional[int]:
    parts = (token or "").split(".")
    if len(parts) < 2:
        return None
    try:
        payload_raw = _b64url_decode(parts[1])
        payload = json.loads(payload_raw.decode("utf-8", errors="ignore") or "null")
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    exp = payload.get("exp")
    if isinstance(exp, int):
        return exp
    if isinstance(exp, str) and exp.strip().isdigit():
        try:
            return int(exp.strip())
        except Exception:
            return None
    return None


def _seconds_until_expiry(token: str) -> Optional[int]:
    exp = _jwt_expiry_seconds(token)
    if not exp:
        return None
    now = int(time.time())
    return max(0, exp - now)


def _load_localstorage(retries: int = 3, delay: float = 0.2) -> Dict[str, Any]:
    for attempt in range(max(1, retries)):
        try:
            content = TOKEN_FILE.read_text(encoding="utf-8")
            data = json.loads(content or "null")
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            if attempt < retries - 1:
                time.sleep(delay)
                continue
            return {}
        except FileNotFoundError:
            return {}
        except Exception:
            return {}
    return {}


def _persist_localstorage(data: Dict[str, Any]) -> bool:
    try:
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = TOKEN_FILE.with_suffix(TOKEN_FILE.suffix + ".tmp")
        tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(TOKEN_FILE)
        return True
    except Exception:
        try:
            tmp_path = TOKEN_FILE.with_suffix(TOKEN_FILE.suffix + ".tmp")
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass
        return False


def _refresh(session: requests.Session, refresh_token_value: str, proxies: Optional[Dict[str, str]] = None) -> Optional[Dict[str, str]]:
    headers = {"Authorization": f"Bearer {refresh_token_value}", "Content-Type": "application/json"}
    try:
        resp = session.post(REFRESH_URL, headers=headers, json={}, proxies=proxies, timeout=REQUEST_TIMEOUT_S)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    try:
        payload = resp.json()
    except ValueError:
        return None
    if not isinstance(payload, dict) or payload.get("code") != 200:
        return None
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        return None
    account_token = (data.get("account_token") or data.get("token") or "").strip()
    refresh_token_new = (data.get("refresh_token") or refresh_token_value or "").strip()
    if not account_token:
        return None
    return {"account_token": account_token, "refresh_token": refresh_token_new}


def main() -> int:
    session = requests.Session()
    proxy = (os.getenv("SOCKS5_PROXY") or os.getenv("VALUESCAN_SOCKS5_PROXY") or os.getenv("VALUESCAN_PROXY") or "").strip()
    proxies = {"http": proxy, "https": proxy} if proxy else None

    while True:
        ls = _load_localstorage()
        refresh_token_value = (ls.get("refresh_token") or "").strip()
        account_token = (ls.get("account_token") or "").strip()

        if not refresh_token_value:
            time.sleep(CHECK_INTERVAL_S)
            continue

        seconds_left = _seconds_until_expiry(account_token) if account_token else None
        should_refresh = (not account_token) or (seconds_left is not None and seconds_left <= REFRESH_SAFETY_S)

        if should_refresh:
            updated = _refresh(session, refresh_token_value, proxies=proxies)
            if updated:
                ls["account_token"] = updated["account_token"]
                ls["refresh_token"] = updated["refresh_token"]
                ls["last_refresh"] = datetime.now(timezone.utc).isoformat()
                _persist_localstorage(ls)

        time.sleep(CHECK_INTERVAL_S)


if __name__ == "__main__":
    raise SystemExit(main())


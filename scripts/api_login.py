#!/usr/bin/env python3
"""
Login via ValueScan API to obtain tokens.

Usage:
  python scripts/api_login.py <email> <password>

Or set env vars:
  VALUESCAN_EMAIL, VALUESCAN_PASSWORD
  SOCKS5_PROXY (optional, e.g. socks5://127.0.0.1:1080)
  VALUESCAN_TOKEN_FILE (optional output path)
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from typing import Optional, Dict

import requests


def _get_credentials() -> tuple[str, str]:
    email = (os.getenv("VALUESCAN_EMAIL") or "").strip()
    password = (os.getenv("VALUESCAN_PASSWORD") or "").strip()
    if len(sys.argv) > 1:
        email = sys.argv[1].strip()
    if len(sys.argv) > 2:
        password = sys.argv[2].strip()
    if not email or not password:
        raise SystemExit(
            "Missing credentials. Pass args: scripts/api_login.py <email> <password> "
            "or set env VALUESCAN_EMAIL/VALUESCAN_PASSWORD."
        )
    return email, password


def _get_proxies() -> Optional[Dict[str, str]]:
    proxy = (os.getenv("SOCKS5_PROXY") or os.getenv("VALUESCAN_SOCKS5_PROXY") or "").strip()
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def main() -> int:
    email, password = _get_credentials()
    proxies = _get_proxies()

    url = "https://api.valuescan.io/api/account/login"
    headers = {"Content-Type": "application/json"}

    payloads = [
        {"account": email, "password": password},
        {"email": email, "password": password},
        {"username": email, "password": password},
        {"account": email, "password": hashlib.md5(password.encode("utf-8")).hexdigest()},
    ]

    for idx, payload in enumerate(payloads, start=1):
        print(f"\nTry {idx}: {list(payload.keys())}")
        resp = requests.post(url, json=payload, headers=headers, proxies=proxies, timeout=30)
        print(f"Status: {resp.status_code}")
        data = resp.json()
        if data.get("code") != 200:
            print(f"Response: {json.dumps(data, ensure_ascii=False)[:300]}")
            continue

        token_data = data.get("data", {}) or {}
        account_token = token_data.get("account_token") or token_data.get("token") or ""
        refresh_token = token_data.get("refresh_token") or ""

        if not account_token:
            print("Login succeeded but token missing in response.")
            continue

        output_path = os.getenv("VALUESCAN_TOKEN_FILE") or os.path.join(
            os.getcwd(), "valuescan_localstorage.json"
        )
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                {"account_token": account_token, "refresh_token": refresh_token, "language": "en-US"},
                f,
                indent=2,
                ensure_ascii=False,
            )
        print(f"Token saved to: {output_path}")
        return 0

    print("Login failed for all payload variants.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())


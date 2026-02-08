#!/usr/bin/env python3
"""
ValueScan HTTP API login helper.

This script logs into https://www.valuescan.io using pure HTTP requests,
without requiring a browser. This is more reliable for headless servers.

Usage:
  python http_api_login.py <email> <password>

Or set env vars:
  VALUESCAN_EMAIL, VALUESCAN_PASSWORD
"""

import base64
import json
import hashlib
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

PUBLIC_KEY_B64 = "MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBAI6T4TlLunddUVX+ES3olnybVtplwTfRAwVRC405CUjzO03nUL8AIgwtnbNUVvY5nyEVx1a8VFudR3FGXPVIlW0CAwEAAQ=="
AES_TICKET_KEY = b"BxlAG1lX9daAAHgj"


def _get_credentials():
    email = (os.getenv("VALUESCAN_EMAIL") or "").strip()
    password = (os.getenv("VALUESCAN_PASSWORD") or "").strip()
    if len(sys.argv) > 1:
        email = sys.argv[1].strip()
    if len(sys.argv) > 2:
        password = sys.argv[2].strip()
    if not email or not password:
        raise SystemExit(
            "Missing credentials. Use: python http_api_login.py <email> <password> "
            "or set VALUESCAN_EMAIL/VALUESCAN_PASSWORD."
        )
    return email, password


def _get_proxies_from_env() -> Optional[Dict[str, str]]:
    proxy = (
        os.getenv("VALUESCAN_PROXY")
        or os.getenv("SOCKS5_PROXY")
        or os.getenv("VALUESCAN_SOCKS5_PROXY")
        or ""
    ).strip()
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def _try_json(response: requests.Response) -> Optional[Any]:
    try:
        return response.json()
    except Exception:
        return None


def _extract_tokens_from_obj(obj: Any) -> Dict[str, str]:
    """
    Extract tokens from common ValueScan API response shapes.

    Expected examples:
      {"code": 200, "data": {"account_token": "...", "refresh_token": "..."}}
      {"data": {"token": "..."}}
      {"access_token": "..."}  # less common
    """
    if not isinstance(obj, dict):
        return {}

    token_keys = ["account_token", "token", "access_token", "accessToken", "jwt"]
    refresh_keys = ["refresh_token", "refreshToken", "refresh"]

    def _pick(d: Dict[str, Any], keys: List[str]) -> str:
        for k in keys:
            v = d.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return ""

    def _as_dict(v: Any) -> Dict[str, Any]:
        return v if isinstance(v, dict) else {}

    # Try top-level first
    account_token = _pick(obj, token_keys)
    refresh_token = _pick(obj, refresh_keys)
    if account_token or refresh_token:
        return {"account_token": account_token, "refresh_token": refresh_token}

    # Common nested shapes
    for k in ("data", "result", "payload"):
        nested = _as_dict(obj.get(k))
        account_token = _pick(nested, token_keys)
        refresh_token = _pick(nested, refresh_keys)
        if account_token or refresh_token:
            return {"account_token": account_token, "refresh_token": refresh_token}

    def _search_nested(d: Dict[str, Any], depth: int) -> Dict[str, str]:
        if depth <= 0:
            return {}
        account_token = _pick(d, token_keys)
        refresh_token = _pick(d, refresh_keys)
        if account_token or refresh_token:
            return {"account_token": account_token, "refresh_token": refresh_token}
        for v in d.values():
            if isinstance(v, dict):
                found = _search_nested(v, depth - 1)
                if found:
                    return found
        return {}

    # Deeply nested fallback: limited recursive scan
    found = _search_nested(obj, depth=4)
    if found:
        return found

    return {}


def _pkcs7_pad(data: bytes, block_size: int = 16) -> bytes:
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len]) * pad_len


def _rsa_encrypt_password(password: str) -> str:
    payload = password.encode("utf-8")
    key_der = base64.b64decode(PUBLIC_KEY_B64)
    try:
        from Crypto.PublicKey import RSA  # type: ignore
        from Crypto.Cipher import PKCS1_v1_5  # type: ignore

        pub_key = RSA.import_key(key_der)
        cipher = PKCS1_v1_5.new(pub_key)
        encrypted = cipher.encrypt(payload)
    except Exception:
        from cryptography.hazmat.primitives import serialization  # type: ignore
        from cryptography.hazmat.primitives.asymmetric import padding  # type: ignore

        pub_key = serialization.load_der_public_key(key_der)
        encrypted = pub_key.encrypt(payload, padding.PKCS1v15())
    return base64.b64encode(encrypted).decode("ascii")


def _aes_encrypt_ticket(ticket: str) -> str:
    raw = (ticket or "").encode("utf-8")
    try:
        from Crypto.Cipher import AES  # type: ignore

        cipher = AES.new(AES_TICKET_KEY, AES.MODE_ECB)
        encrypted = cipher.encrypt(_pkcs7_pad(raw))
    except Exception:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes  # type: ignore
        from cryptography.hazmat.backends import default_backend  # type: ignore

        encryptor = Cipher(
            algorithms.AES(AES_TICKET_KEY),
            modes.ECB(),
            backend=default_backend(),
        ).encryptor()
        encrypted = encryptor.update(_pkcs7_pad(raw)) + encryptor.finalize()
    return base64.b64encode(encrypted).decode("ascii")


def _fetch_ticket(session: requests.Session) -> str:
    try:
        resp = session.get("https://api.valuescan.io/api/ticket/getTicket", timeout=15)
    except requests.RequestException:
        return ""
    obj = _try_json(resp)
    if isinstance(obj, dict):
        data = obj.get("data") or obj.get("ticket") or obj.get("result")
        if isinstance(data, str) and data.strip():
            return data.strip()
    return ""


def _extract_auth_cookie_value(session: requests.Session) -> str:
    auth_cookie_names = ("token", "auth", "session", "jwt", "access_token")
    for cookie in session.cookies:
        try:
            name = (cookie.name or "").lower()
        except Exception:
            continue
        if any(part in name for part in auth_cookie_names):
            return cookie.value or ""
    return ""


def _build_login_endpoints() -> List[str]:
    env_urls = (os.getenv("VALUESCAN_LOGIN_ENDPOINTS") or "").strip()
    urls: List[str] = []
    if env_urls:
        urls.extend([u.strip() for u in env_urls.split(",") if u.strip()])

    defaults = [
        # Current web login endpoint (RSA-encrypted code + access-ticket)
        "https://api.valuescan.io/api/authority/login",
        # Most reliable based on existing repo scripts
        "https://api.valuescan.io/api/account/login",
        # Newer versioned endpoints observed in the wild
        "https://api.valuescan.io/api/v1/account/login",
        "https://api.valuescan.io/api/v1/login",
        "https://api.valuescan.io/api/v1/auth/login",
        "https://api.valuescan.io/api/v2/account/login",
        "https://api.valuescan.io/v1/account/login",
        "https://api.valuescan.io/v1/login",
        "https://api.valuescan.io/api/v1/user/login",
        "https://api.valuescan.io/api/v1/user/loginByPassword",
        "https://api.valuescan.io/api/v1/auth/loginByPassword",
        "https://api.valuescan.io/api/v1/account/loginByPassword",
        # Older/alternate endpoints
        "https://api.valuescan.io/api/login",
        "https://api.valuescan.io/api/user/login",
        "https://api.valuescan.io/api/user/loginByPassword",
        "https://api.valuescan.io/api/auth/login",
        "https://api.valuescan.io/api/auth/loginByPassword",
        "https://api.valuescan.io/login",
        "https://www.valuescan.io/api/v1/login",
        "https://www.valuescan.io/api/v1/account/login",
        "https://www.valuescan.io/api/auth/login",
        "https://www.valuescan.io/api/login",
        "https://www.valuescan.io/api/account/login",
    ]
    for url in defaults:
        if url and url not in urls:
            urls.append(url)
    return urls


def _build_login_attempts(
    email: str,
    password: str,
    access_ticket: str,
) -> List[Tuple[str, Dict[str, Any], Dict[str, str]]]:
    """
    Returns a list of (endpoint, json_payload) attempts.

    ValueScan has used multiple API hosts/paths and multiple credential field names
    over time; we try a small set of combinations to keep this script resilient.
    """
    endpoints = _build_login_endpoints()

    authority_payload = {
        "phoneOrEmail": email,
        "code": f"$$##=={_rsa_encrypt_password(password)}",
        "loginTypeEnum": 2,
        "endpointEnum": 1,
    }
    authority_headers = {
        "Access-Ticket": access_ticket,
        "Authorization": "Bearer",
        "Content-Type": "application/json;charset=UTF-8",
    }

    pwd_md5 = hashlib.md5(password.encode("utf-8")).hexdigest()
    pwd_sha256 = hashlib.sha256(password.encode("utf-8")).hexdigest()
    payloads: List[Dict[str, Any]] = [
        {"account": email, "password": password, "language": "en-US"},
        {"email": email, "password": password, "language": "en-US"},
        {"username": email, "password": password, "language": "en-US"},
        {"account": email, "password": pwd_md5, "language": "en-US"},
        {"email": email, "password": pwd_md5, "language": "en-US"},
        {"account": email, "password": pwd_sha256, "language": "en-US"},
        {"email": email, "password": pwd_sha256, "language": "en-US"},
        {"account": email, "password": password, "remember": True},
        {"email": email, "password": password, "remember": True},
    ]

    attempts: List[Tuple[str, Dict[str, Any], Dict[str, str]]] = []
    attempts.append(("https://api.valuescan.io/api/authority/login", authority_payload, authority_headers))
    for endpoint in endpoints:
        for payload in payloads:
            attempts.append((endpoint, payload, {}))
    return attempts


def main():
    email, password = _get_credentials()

    out_dir = Path(os.getenv("VALUESCAN_LOGIN_OUT_DIR") or Path(__file__).resolve().parent)
    out_dir.mkdir(parents=True, exist_ok=True)

    cookies_path = Path(os.getenv("VALUESCAN_COOKIES_FILE") or (out_dir / "valuescan_cookies.json"))
    token_path = Path(os.getenv("VALUESCAN_TOKEN_FILE") or (out_dir / "valuescan_localstorage.json"))

    # Setup session with common headers
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "Origin": "https://www.valuescan.io",
        "Referer": "https://www.valuescan.io/login",
    })

    proxies = _get_proxies_from_env()
    if proxies:
        session.proxies = proxies

    try:
        token_payload: Dict[str, Any] = {"language": "en-US"}
        response: Optional[requests.Response] = None
        last_error = ""

        # Warm up cookies (some deployments set anti-bot cookies on first GET)
        try:
            session.get("https://www.valuescan.io/", timeout=15)
        except Exception:
            pass

        ticket = (os.getenv("VALUESCAN_TICKET") or "").strip()
        if not ticket:
            ticket = _fetch_ticket(session)
        if ticket:
            token_payload["ticket"] = ticket
        access_ticket = _aes_encrypt_ticket(ticket)

        attempts = _build_login_attempts(email, password, access_ticket)
        for idx, (endpoint, payload, extra_headers) in enumerate(attempts, start=1):
            try:
                print(f"Trying endpoint ({idx}/{len(attempts)}): {endpoint} fields={list(payload.keys())}")
                headers = dict(session.headers)
                if extra_headers:
                    headers.update(extra_headers)
                resp = session.post(endpoint, json=payload, headers=headers, timeout=30)
            except requests.RequestException as exc:
                last_error = f"{endpoint} failed: {exc}"
                continue

            response = resp
            if resp.status_code == 404:
                continue

            obj = _try_json(resp)
            tokens = _extract_tokens_from_obj(obj)
            cookie_token = _extract_auth_cookie_value(session)

            if tokens.get("account_token") or tokens.get("refresh_token"):
                if isinstance(obj, dict):
                    token_payload.update(obj)
                token_payload.update(tokens)
                print(f"Success with endpoint: {endpoint}")
                break

            if cookie_token:
                token_payload["account_token"] = token_payload.get("account_token") or cookie_token
                if isinstance(obj, dict):
                    token_payload.update(obj)
                print(f"Success with endpoint (auth cookie): {endpoint}")
                break

            # Status 200 may still be an application-level error, keep trying.
            if isinstance(obj, dict):
                code = obj.get("code")
                msg = obj.get("msg") or obj.get("message") or ""
                if code is not None or msg:
                    last_error = f"{endpoint} responded but token missing: code={code} msg={msg}".strip()
                else:
                    last_error = f"{endpoint} responded but token missing"
            else:
                snippet = (resp.text or "").strip().replace("\n", " ")[:200]
                last_error = f"{endpoint} non-JSON response (status {resp.status_code}): {snippet}".strip()

        # Very last resort: form-based login (often blocked by CSRF/captcha)
        if not token_payload.get("account_token") and not _extract_auth_cookie_value(session):
            try:
                print("Trying form-based login fallback...")
                response = session.post(
                    "https://www.valuescan.io/login",
                    data={"email": email, "password": password},
                    timeout=30,
                    allow_redirects=True,
                )
            except requests.RequestException as exc:
                last_error = f"Form login failed: {exc}"
            else:
                obj = _try_json(response) if response is not None else None
                tokens = _extract_tokens_from_obj(obj)
                if isinstance(obj, dict):
                    token_payload.update(obj)
                if tokens:
                    token_payload.update(tokens)
                cookie_token = _extract_auth_cookie_value(session)
                if cookie_token:
                    token_payload["account_token"] = token_payload.get("account_token") or cookie_token

        if last_error and not token_payload.get("account_token"):
            token_payload["last_error"] = last_error

        # Extract cookies
        cookies = []
        for cookie in session.cookies:
            cookies.append({
                "name": cookie.name,
                "value": cookie.value,
                "domain": cookie.domain,
                "path": cookie.path,
                "secure": cookie.secure,
            })

        cookie_token = _extract_auth_cookie_value(session)
        if cookie_token:
            token_payload["account_token"] = token_payload.get("account_token") or cookie_token

        # Save results
        cookies_path.parent.mkdir(parents=True, exist_ok=True)
        cookies_path.write_text(json.dumps(cookies, indent=2, ensure_ascii=False), encoding="utf-8")

        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(json.dumps(token_payload, indent=2, ensure_ascii=False), encoding="utf-8")

        ok = bool((token_payload.get("account_token") or "").strip()) or len(cookies) > 0
        if ok:
            print(f"Login successful!")
            print(f"Saved cookies to: {cookies_path}")
            print(f"Saved tokens to: {token_path}")
            return 0
        else:
            print("Login completed but no tokens/cookies found.", file=sys.stderr)
            print("This may indicate incorrect credentials or API changes.", file=sys.stderr)
            return 1

    except requests.RequestException as e:
        print(f"Network error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Login error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

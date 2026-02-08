#!/usr/bin/env python3
"""
HTTP-only wrapper for ValueScan token refresher.

For VPS usage: avoid browser login (CAPTCHA) and rely on refresh_token + HTTP API login.
"""

from __future__ import annotations

import os
import sys


def _env_bool(key: str, default: bool) -> bool:
    raw = (os.getenv(key) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "y", "on")


def _apply_env_defaults() -> None:
    force_http = _env_bool("VALUESCAN_FORCE_HTTP", True)

    os.environ.setdefault("VALUESCAN_AUTO_RELOGIN", "1")

    if force_http:
        # Ensure HTTP login path is used, even if env files set browser values.
        os.environ["VALUESCAN_LOGIN_METHOD"] = "http"
        os.environ["VALUESCAN_AUTO_RELOGIN_USE_BROWSER"] = "0"
    else:
        os.environ.setdefault("VALUESCAN_LOGIN_METHOD", "http")
        os.environ.setdefault("VALUESCAN_AUTO_RELOGIN_USE_BROWSER", "0")


def main() -> int:
    _apply_env_defaults()
    import token_refresher

    return token_refresher.main()


if __name__ == "__main__":
    raise SystemExit(main())

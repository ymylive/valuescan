#!/usr/bin/env python3
"""
ValueScan AI 智能选币 -> 本地 AI500(coinpool) API 服务。

用途：
- 给本项目的 Go 交易引擎/策略引擎提供候选币（兼容 AI500 数据源结构）
- 或者给任意交易系统提供“从 ValueScan 页面抓到的候选币列表”

依赖：
- DrissionPage
- 已登录的 Chrome Profile（推荐先运行 signal_monitor/start_with_chrome.py 并登录）

启动示例：
  python -m signal_monitor.ai_coin_pool_server --host 127.0.0.1 --port 30006 --tab 机会监控
然后在交易系统里把 coin_pool_api_url 配置为：
  http://127.0.0.1:30006/api/ai500/list
"""

from __future__ import annotations

import argparse
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, request

from DrissionPage import ChromiumOptions, ChromiumPage

from .ai_coin_pool import rows_to_coin_pool, coin_pool_response


DEFAULT_URL = "https://www.valuescan.io/GEMs/signals"
DEFAULT_USER_DATA_PATH = str(Path(__file__).resolve().parent / "chrome-debug-profile")
DEFAULT_CONFIG_PATH = str(Path(__file__).resolve().parents[1] / "config" / "valuescan_coinpool.json")


def _load_json(path: str) -> Optional[dict]:
    try:
        p = Path(path)
        if not p.exists():
            return None
        import json

        payload = json.loads(p.read_text(encoding="utf-8", errors="ignore") or "null")
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _resolve_defaults() -> dict:
    cfg_path = (os.getenv("VALUESCAN_COINPOOL_CONFIG") or "").strip()  # type: ignore[name-defined]
    if not cfg_path:
        cfg_path = DEFAULT_CONFIG_PATH

    payload = _load_json(cfg_path) or {}
    raw_headless = payload.get("headless", True)
    if isinstance(raw_headless, bool):
        headless = raw_headless
    elif isinstance(raw_headless, str):
        headless = raw_headless.strip().lower() in ("1", "true", "yes", "on")
    else:
        headless = bool(raw_headless)

    return {
        "host": str(payload.get("host") or "127.0.0.1"),
        "port": int(payload.get("port") or 30006),
        "tab": str(payload.get("tab") or "机会监控"),
        "url": str(payload.get("url") or DEFAULT_URL),
        "headless": headless,
        "chrome_debug_port": int(payload.get("chrome_debug_port") or 9222),
        "user_data_path": str(payload.get("user_data_path") or DEFAULT_USER_DATA_PATH),
        "max_pages": int(payload.get("max_pages") or 1),
        "limit": int(payload.get("limit") or 200),
        "cache_ttl_s": int(payload.get("cache_ttl_s") or 15),
        "config_path": cfg_path,
    }


def _create_page(headless: bool, chrome_debug_port: int, user_data_path: str) -> ChromiumPage:
    co = ChromiumOptions()
    if headless:
        co.headless(True)
        co.set_user_data_path(user_data_path)
        co.set_argument("--disable-gpu")
        co.set_argument("--no-sandbox")
        co.set_argument("--disable-dev-shm-usage")
        return ChromiumPage(addr_or_opts=co)

    co.set_local_port(chrome_debug_port)
    return ChromiumPage(addr_or_opts=co)


_EXTRACT_TABLE_JS = r"""
(() => {
  function isVisible(el) {
    if (!el) return false;
    if (el.offsetParent === null) return false;
    const style = window.getComputedStyle(el);
    return style && style.visibility !== 'hidden' && style.display !== 'none';
  }

  function pickTableRoot() {
    const roots = Array.from(document.querySelectorAll('.ant-table')).filter(isVisible);
    for (const root of roots) {
      const rows = root.querySelectorAll('tbody tr');
      if (rows && rows.length) return root;
    }
    const tables = Array.from(document.querySelectorAll('table')).filter(isVisible);
    for (const t of tables) {
      const rows = t.querySelectorAll('tbody tr');
      if (rows && rows.length) return t;
    }
    return null;
  }

  function extractFrom(root) {
    const table = root.tagName.toLowerCase() === 'table' ? root : root.querySelector('table');
    if (!table) return { headers: [], rows: [] };

    const headers = Array.from(table.querySelectorAll('thead th'))
      .map(th => (th.innerText || '').trim())
      .filter(Boolean);

    const bodyRows = [];
    const trs = Array.from(table.querySelectorAll('tbody tr'));
    for (const tr of trs) {
      const tds = Array.from(tr.querySelectorAll('td')).map(td => (td.innerText || '').trim());
      if (!tds.length) continue;

      const row = {};
      for (let i = 0; i < Math.min(headers.length, tds.length); i++) {
        row[headers[i]] = tds[i];
      }
      bodyRows.push(row);
    }

    return { headers, rows: bodyRows };
  }

  const root = pickTableRoot();
  if (!root) return { headers: [], rows: [] };
  return extractFrom(root);
})();
"""


_CLICK_TAB_JS = r"""
((label) => {
  const candidates = Array.from(document.querySelectorAll('.ant-tabs-tab'));
  const target = candidates.find(el => (el.innerText || '').trim() === label);
  if (target) { target.click(); return true; }
  const byRole = Array.from(document.querySelectorAll('[role="tab"]'));
  const target2 = byRole.find(el => (el.innerText || '').trim() === label);
  if (target2) { target2.click(); return true; }
  return false;
})
"""


_HAS_NEXT_PAGE_JS = r"""
(() => {
  const next = document.querySelector('.ant-pagination-next');
  if (!next) return false;
  return !next.classList.contains('ant-pagination-disabled');
})()
"""


_CLICK_NEXT_PAGE_JS = r"""
(() => {
  const next = document.querySelector('.ant-pagination-next');
  if (!next) return false;
  if (next.classList.contains('ant-pagination-disabled')) return false;
  next.click();
  return true;
})()
"""


def _sleep_until(condition, timeout_s: float = 15.0, interval_s: float = 0.25) -> bool:
    start = time.time()
    while time.time() - start < timeout_s:
        if condition():
            return True
        time.sleep(interval_s)
    return False


class ValueScanAICoinPool:
    def __init__(
        self,
        tab: str,
        url: str = DEFAULT_URL,
        headless: bool = False,
        chrome_debug_port: int = 9222,
        user_data_path: str = DEFAULT_USER_DATA_PATH,
        max_pages: int = 1,
        limit: int = 200,
        cache_ttl_s: int = 15,
    ):
        self.tab = tab
        self.url = url
        self.headless = headless
        self.chrome_debug_port = chrome_debug_port
        self.user_data_path = user_data_path
        self.max_pages = max(1, int(max_pages))
        self.limit = max(1, int(limit))
        self.cache_ttl_s = max(1, int(cache_ttl_s))

        self._lock = threading.Lock()
        self._page: Optional[ChromiumPage] = None
        self._cached_at = 0.0
        self._cached_rows: List[Dict[str, Any]] = []

    def _ensure_page(self) -> ChromiumPage:
        if self._page is not None:
            return self._page

        page = _create_page(
            headless=self.headless,
            chrome_debug_port=self.chrome_debug_port,
            user_data_path=self.user_data_path,
        )
        page.get(self.url)
        time.sleep(2)
        self._page = page
        return page

    def _select_tab(self, page: ChromiumPage) -> None:
        if not self.tab:
            return
        try:
            clicked = page.run_js(_CLICK_TAB_JS, self.tab)
        except Exception:
            clicked = False
        if clicked:
            time.sleep(1.5)

    def _extract_rows_once(self, page: ChromiumPage) -> List[Dict[str, Any]]:
        payload = page.run_js(_EXTRACT_TABLE_JS)
        if not isinstance(payload, dict):
            return []
        rows = payload.get("rows") or []
        if isinstance(rows, list):
            return [r for r in rows if isinstance(r, dict)]
        return []

    def _extract_rows_paged(self, page: ChromiumPage) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []

        for _ in range(self.max_pages):
            batch = self._extract_rows_once(page)
            for item in batch:
                if item not in rows:
                    rows.append(item)
                    if len(rows) >= self.limit:
                        return rows

            has_next = False
            try:
                has_next = bool(page.run_js(_HAS_NEXT_PAGE_JS))
            except Exception:
                has_next = False
            if not has_next:
                break

            try:
                clicked = bool(page.run_js(_CLICK_NEXT_PAGE_JS))
            except Exception:
                clicked = False
            if not clicked:
                break

            time.sleep(1.5)
        return rows

    def get_rows(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        with self._lock:
            now = time.time()
            if not force_refresh and (now - self._cached_at) < self.cache_ttl_s:
                return list(self._cached_rows)

            page = self._ensure_page()
            self._select_tab(page)

            ok = _sleep_until(
                lambda: len(self._extract_rows_once(page)) > 0,
                timeout_s=15.0,
            )
            if not ok:
                self._cached_rows = []
                self._cached_at = now
                return []

            rows = self._extract_rows_paged(page)
            self._cached_rows = rows
            self._cached_at = now
            return list(rows)


def build_app(pool: ValueScanAICoinPool) -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify({"ok": True})

    @app.get("/api/ai500/list")
    def ai500_list():
        force = request.args.get("force", "0") == "1"
        limit = request.args.get("limit")
        tab = request.args.get("tab")

        if tab:
            pool.tab = tab

        rows = pool.get_rows(force_refresh=force)
        max_items = pool.limit
        if limit:
            try:
                max_items = max(1, int(limit))
            except ValueError:
                pass

        coins = rows_to_coin_pool(rows, limit=max_items)
        return jsonify(coin_pool_response(coins))

    @app.get("/api/ai500/raw")
    def ai500_raw():
        force = request.args.get("force", "0") == "1"
        rows = pool.get_rows(force_refresh=force)
        return jsonify({"rows": rows, "count": len(rows)})

    return app


def main():
    defaults = _resolve_defaults()
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=defaults["host"])
    parser.add_argument("--port", type=int, default=defaults["port"])
    parser.add_argument("--tab", default=defaults["tab"], help="例如：机会监控/风险监控/手动监控")
    parser.add_argument("--url", default=defaults["url"])
    headless_group = parser.add_mutually_exclusive_group()
    headless_group.add_argument("--headless", action="store_true", help="启用无头模式")
    headless_group.add_argument("--headed", action="store_true", help="启用有头模式")
    parser.add_argument("--chrome-debug-port", type=int, default=defaults["chrome_debug_port"])
    parser.add_argument("--user-data-path", default=defaults["user_data_path"])
    parser.add_argument("--max-pages", type=int, default=defaults["max_pages"])
    parser.add_argument("--limit", type=int, default=defaults["limit"])
    parser.add_argument("--cache-ttl", type=int, default=defaults["cache_ttl_s"])
    args = parser.parse_args()

    headless = defaults["headless"]
    if args.headless:
        headless = True
    if args.headed:
        headless = False

    pool = ValueScanAICoinPool(
        tab=args.tab,
        url=args.url,
        headless=headless,
        chrome_debug_port=args.chrome_debug_port,
        user_data_path=args.user_data_path,
        max_pages=args.max_pages,
        limit=args.limit,
        cache_ttl_s=args.cache_ttl,
    )

    app = build_app(pool)
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Periodic AI signal publisher.
Fetches snapshots for configured symbols and sends to Telegram with
async chart + AI analysis.
"""

from __future__ import annotations

import os
import json
import time
import threading
import atexit
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Optional

import requests

from logger import logger
from market_data_sources import fetch_market_snapshot, is_metal_symbol
from fundamentals_sources import build_macro_brief
from telegram import send_message_with_async_chart

try:
    import config as signal_config
except Exception:
    signal_config = None


DEFAULT_SYMBOLS = ["BTC", "ETH", "BNB", "SOL", "XAUUSDT", "XAGUSDT"]
BEIJING_TZ = timezone(timedelta(hours=8))
_LOCK_FILE_HANDLE = None


def _release_process_lock() -> None:
    global _LOCK_FILE_HANDLE
    if _LOCK_FILE_HANDLE is None:
        return
    try:
        import fcntl  # type: ignore
        fcntl.flock(_LOCK_FILE_HANDLE, fcntl.LOCK_UN)
    except Exception:
        pass
    try:
        _LOCK_FILE_HANDLE.close()
    except Exception:
        pass
    _LOCK_FILE_HANDLE = None


def _acquire_process_lock() -> bool:
    lock_path = os.getenv("NOFX_AI_SIGNAL_LOCK", "/tmp/ai_signal.lock")
    try:
        import fcntl  # type: ignore
    except Exception:
        logger.warning("[AI Signal] Lock not supported; running without lock.")
        return True
    global _LOCK_FILE_HANDLE
    try:
        _LOCK_FILE_HANDLE = open(lock_path, "w")
        try:
            fcntl.flock(_LOCK_FILE_HANDLE, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except Exception:
            logger.warning("[AI Signal] Lock busy, waiting for primary scheduler to release it.")
            fcntl.flock(_LOCK_FILE_HANDLE, fcntl.LOCK_EX)
        _LOCK_FILE_HANDLE.write(str(os.getpid()))
        _LOCK_FILE_HANDLE.flush()
        atexit.register(_release_process_lock)
        return True
    except Exception as exc:
        logger.warning("[AI Signal] Lock failed (%s). Continuing without lock.", exc)
        return True


def _normalize_symbols(raw: Optional[object]) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        tokens = [t.strip().upper() for t in raw.replace(";", ",").split(",")]
        return [t for t in tokens if t]
    if isinstance(raw, (list, tuple, set)):
        out = []
        for item in raw:
            if not item:
                continue
            out.append(str(item).strip().upper())
        return [t for t in out if t]
    return []


def _normalize_api_paths(raw: Optional[object]) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        tokens = [t.strip() for t in raw.replace(";", ",").split(",")]
        return [t for t in tokens if t]
    if isinstance(raw, (list, tuple, set)):
        out = []
        for item in raw:
            if not item:
                continue
            out.append(str(item).strip())
        return [t for t in out if t]
    return []


def _load_market_alert_symbols() -> List[str]:
    cfg_path = Path(__file__).with_name("market_alert_config.json")
    if not cfg_path.exists():
        return []
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, dict):
        return []
    symbols = _normalize_symbols(data.get("symbols"))
    metals_cfg = data.get("metals") if isinstance(data.get("metals"), dict) else {}
    if metals_cfg and metals_cfg.get("enabled"):
        symbols += _normalize_symbols(metals_cfg.get("symbols"))
    out = []
    for sym in symbols:
        if sym not in out:
            out.append(sym)
    return out


def _load_symbols() -> List[str]:
    env_raw = os.getenv("NOFX_AI_SIGNAL_SYMBOLS")
    symbols = _normalize_symbols(env_raw)
    if not symbols and signal_config:
        symbols = _normalize_symbols(getattr(signal_config, "AI_SIGNAL_SYMBOLS", None))
    allowed = _load_market_alert_symbols()
    if allowed:
        symbols = allowed
    return symbols or DEFAULT_SYMBOLS[:]


def _load_interval_minutes() -> int:
    env_raw = os.getenv("NOFX_AI_SIGNAL_INTERVAL_MINUTES")
    if env_raw and env_raw.isdigit():
        return max(1, int(env_raw))
    if signal_config:
        try:
            return max(1, int(getattr(signal_config, "AI_SIGNAL_INTERVAL_MINUTES", 20)))
        except Exception:
            pass
    return 20


def _load_symbol_delay_seconds() -> int:
    env_raw = os.getenv("NOFX_AI_SIGNAL_SYMBOL_DELAY")
    if env_raw and env_raw.isdigit():
        return max(0, int(env_raw))
    if signal_config:
        try:
            return max(0, int(getattr(signal_config, "AI_SIGNAL_SYMBOL_DELAY", 2)))
        except Exception:
            pass
    return 2


def _is_dry_run() -> bool:
    return os.getenv("NOFX_AI_SIGNAL_DRY_RUN", "0").lower() in ("1", "true", "yes", "on")


def _run_once_only() -> bool:
    return os.getenv("NOFX_AI_SIGNAL_RUN_ONCE", "0").lower() in ("1", "true", "yes", "on")


def _save_chart_enabled() -> bool:
    return os.getenv("NOFX_AI_SIGNAL_SAVE_CHART", "0").lower() in ("1", "true", "yes", "on")


def _chart_output_dir() -> str:
    return os.getenv("NOFX_AI_SIGNAL_CHART_DIR", "output")


def _analysis_timeout() -> int:
    raw = os.getenv("NOFX_AI_SIGNAL_AI_TIMEOUT", "180")
    try:
        return max(10, int(raw))
    except Exception:
        return 180


def _chart_timeout() -> int:
    raw = os.getenv("NOFX_AI_SIGNAL_CHART_TIMEOUT", "180")
    try:
        return max(10, int(raw))
    except Exception:
        return 180


def _dedup_window_seconds() -> int:
    raw = os.getenv("NOFX_AI_SIGNAL_DEDUP_SECONDS")
    if raw and raw.isdigit():
        return max(0, int(raw))
    if signal_config:
        try:
            return max(0, int(getattr(signal_config, "AI_SIGNAL_DEDUP_SECONDS", 120)))
        except Exception:
            pass
    return 120


def _dedup_state_path() -> str:
    return os.getenv("NOFX_AI_SIGNAL_DEDUP_PATH", "/tmp/ai_signal_dedup.json")


def _read_dedup_state() -> dict:
    path = _dedup_state_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def _write_dedup_state(state: dict) -> None:
    path = _dedup_state_path()
    folder = os.path.dirname(path)
    if folder:
        try:
            os.makedirs(folder, exist_ok=True)
        except Exception:
            pass
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=True, separators=(",", ":"))
    os.replace(tmp_path, path)


def _should_skip_duplicate(symbol: str) -> bool:
    window = _dedup_window_seconds()
    if window <= 0:
        return False
    symbol = str(symbol).strip().upper()
    now_ts = int(time.time())
    try:
        import fcntl  # type: ignore
    except Exception:
        state = _read_dedup_state()
        last_ts = state.get(symbol)
        if last_ts and (now_ts - int(last_ts)) < window:
            return True
        state[symbol] = now_ts
        _write_dedup_state(state)
        return False

    lock_path = f"{_dedup_state_path()}.lock"
    try:
        with open(lock_path, "w") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            state = _read_dedup_state()
            last_ts = state.get(symbol)
            if last_ts and (now_ts - int(last_ts)) < window:
                return True
            state[symbol] = now_ts
            _write_dedup_state(state)
        return False
    except Exception as exc:
        logger.warning("[AI Signal] Dedup state error: %s", exc)
        return False


def _maybe_generate_market_summary() -> None:
    try:
        from ai_market_summary import check_and_generate_summary
        check_and_generate_summary()
    except Exception as exc:
        logger.warning("[AI Signal] Market summary skipped: %s", exc)


def _start_market_summary_scheduler() -> None:
    """Ensure macro market summary runs on schedule even if main loop slows."""
    def _run():
        logger.info("[AI Signal] Market summary scheduler started.")
        while True:
            _maybe_generate_market_summary()
            time.sleep(60)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


def _resolve_signal_callback(enabled: bool):
    if not enabled:
        return None
    try:
        from ipc_client import forward_signal as _forward_signal
        return _forward_signal
    except Exception:
        return None


def _format_snapshot(symbol: str, snapshot: Optional[dict]) -> str:
    now_bj = datetime.now(tz=BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"Symbol: {symbol}", f"Time: {now_bj}"]
    if snapshot:
        price = snapshot.get("price")
        change = snapshot.get("price_change_percent")
        vol = snapshot.get("volume_24h")
        source = snapshot.get("source")
        if price is not None:
            lines.append(f"Price: {price:,.4f}")
        if change is not None:
            lines.append(f"24H Change: {change:,.2f}%")
        if vol is not None:
            lines.append(f"24H Volume: {vol:,.2f}")
        if source:
            lines.append(f"Source: {source}")
    else:
        lines.append("Data: unavailable")

    macro_lines = build_macro_brief(max_items=3)
    if macro_lines:
        lines.append("Fundamentals:")
        for item in macro_lines:
            lines.append(f"- {item}")

    return "\n".join(lines)



def _fetch_snapshot_with_retry(symbol: str, attempts: int = 3) -> dict:
    last = {}
    force_refresh = is_metal_symbol(symbol)
    for attempt in range(max(1, attempts)):
        snap = fetch_market_snapshot(symbol, force_refresh=force_refresh) or {}
        if isinstance(snap, dict) and snap.get("price"):
            return snap
        last = snap if isinstance(snap, dict) else {}
        if attempt < attempts - 1:
            time.sleep(1 + attempt)
    return last



def _run_once(symbols: Iterable[str]) -> None:
    for symbol in symbols:
        symbol = str(symbol).strip().upper()
        if not symbol:
            continue
        if _should_skip_duplicate(symbol):
            logger.info("[AI Signal] Duplicate suppressed: %s", symbol)
            continue
        try:
            snapshot = _fetch_snapshot_with_retry(symbol, attempts=3)
            message = _format_snapshot(symbol, snapshot)
            if _is_dry_run():
                _run_local(symbol, message)
            else:
                send_message_with_async_chart(message, symbol, pin_message=False, signal_payload=None)
        except Exception as exc:
            logger.warning("[AI Signal] Failed for %s: %s", symbol, exc)
        delay = _load_symbol_delay_seconds()
        if delay:
            time.sleep(delay)


def main() -> None:
    _acquire_process_lock()
    interval_minutes = _load_interval_minutes()
    symbols = _load_symbols()
    logger.info(
        "[AI Signal] Scheduler started. interval=%s minutes symbols=%s",
        interval_minutes,
        ",".join(symbols),
    )
    _start_market_summary_scheduler()
    interval_seconds = interval_minutes * 60
    while True:
        start = time.monotonic()
        _run_once(symbols)
        elapsed = time.monotonic() - start
        sleep_for = max(5, interval_seconds - elapsed)
        logger.info("[AI Signal] Cycle complete. next_run_in=%.1fs", sleep_for)
        if _run_once_only():
            break
        time.sleep(sleep_for)


def _run_local(symbol: str, message: str) -> None:
    os.environ.setdefault("MPLBACKEND", "Agg")
    try:
        from ai_signal_analysis import analyze_signal
    except Exception as exc:
        logger.warning("[AI Signal] AI analysis unavailable: %s", exc)
        analyze_signal = None  # type: ignore[assignment]

    try:
        from chart_pro_v10 import generate_chart_v10
        from ai_key_levels_cache import wait_for_levels
    except Exception as exc:
        logger.warning("[AI Signal] Chart generation unavailable: %s", exc)
        generate_chart_v10 = None  # type: ignore[assignment]
        wait_for_levels = None  # type: ignore[assignment]

    analysis_result = {}
    chart_bytes = None

    def _analysis_worker():
        if not analyze_signal:
            return
        result = analyze_signal(symbol, signal_payload=None)
        if isinstance(result, dict):
            analysis_result.update(result)

    def _chart_worker():
        nonlocal chart_bytes
        if not generate_chart_v10:
            return
        if wait_for_levels:
            try:
                from ai_key_levels_config import get_ai_levels_config
                wait_enabled = get_ai_levels_config().get("enabled", False)
            except Exception:
                wait_enabled = False
            if wait_enabled:
                wait_for_levels(symbol, timeout_sec=8, poll_sec=0.3)
        chart = generate_chart_v10(symbol, "1h", 200)
        if chart:
            chart_bytes = len(chart)
            if _save_chart_enabled():
                os.makedirs(_chart_output_dir(), exist_ok=True)
                out_path = os.path.join(
                    _chart_output_dir(),
                    f"ai_signal_{symbol}_{int(time.time())}.png",
                )
                with open(out_path, "wb") as f:
                    f.write(chart)

    from threading import Thread

    analysis_thread = Thread(target=_analysis_worker, daemon=True)
    chart_thread = Thread(target=_chart_worker, daemon=True)
    analysis_thread.start()
    chart_thread.start()
    analysis_thread.join(timeout=_analysis_timeout())
    chart_thread.join(timeout=_chart_timeout())

    supports = []
    resistances = []

    summary = {
        "symbol": symbol,
        "message": message,
        "analysis": analysis_result.get("analysis"),
        "risk_level": analysis_result.get("risk_level"),
        "entry_decision": analysis_result.get("entry_decision"),
        "direction": analysis_result.get("direction"),
        "supports": supports,
        "resistances": resistances,
        "stop_loss": analysis_result.get("stop_loss"),
        "take_profit": analysis_result.get("take_profit"),
        "rr": analysis_result.get("rr"),
        "chart_bytes": chart_bytes,
    }
    print(summary)


if __name__ == "__main__":
    main()

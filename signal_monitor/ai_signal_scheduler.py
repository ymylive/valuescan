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
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

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
ANOMALY_CONFIG_PATH = Path(__file__).with_name("anomaly_config.json")


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
    # de-dup preserve order
    out = []
    for sym in symbols:
        if sym not in out:
            out.append(sym)
    return out

def _load_json_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _normalize_anomaly_source(raw: Optional[object]) -> str:
    if raw is None:
        return "local"
    value = str(raw).strip().lower()
    if value in ("local", "both"):
        return "local"
    return "local"


def _coerce_bool(value: Optional[object], default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("1", "true", "yes", "on"):
            return True
        if lowered in ("0", "false", "no", "off"):
            return False
    return default


def _coerce_int(value: Optional[object], default: int) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def _coerce_float(value: Optional[object], default: float) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _merge_number_map(
    defaults: Dict[str, float],
    updates: Optional[Dict[str, Any]],
    cast: type = float,
) -> Dict[str, float]:
    if not isinstance(updates, dict):
        return dict(defaults)
    merged: Dict[str, float] = dict(defaults)
    for key, default_value in defaults.items():
        if key not in updates:
            continue
        try:
            merged[key] = cast(updates[key])
        except Exception:
            merged[key] = default_value
    return merged


def _build_anomaly_config(data: Dict[str, Any]):
    try:
        from anomaly_detector import AnomalyConfig
    except Exception:
        from signal_monitor.anomaly_detector import AnomalyConfig

    config = AnomalyConfig()
    if not isinstance(data, dict):
        return config

    local = data.get("local_config") or data.get("local") or data.get("config") or data
    if not isinstance(local, dict):
        return config

    symbols = _normalize_symbols(local.get("symbols"))
    if symbols:
        config.symbols = symbols

    config.vol_spike_threshold = _coerce_float(local.get("vol_spike_threshold"), config.vol_spike_threshold)
    config.vol_zscore_threshold = _coerce_float(local.get("vol_zscore_threshold"), config.vol_zscore_threshold)
    config.price_change_threshold = _coerce_float(local.get("price_change_threshold"), config.price_change_threshold)
    config.funding_warn_negative = _coerce_float(local.get("funding_warn_negative"), config.funding_warn_negative)
    config.funding_warn_positive = _coerce_float(local.get("funding_warn_positive"), config.funding_warn_positive)
    config.funding_extreme_negative = _coerce_float(
        local.get("funding_extreme_negative"),
        config.funding_extreme_negative,
    )
    config.funding_extreme_positive = _coerce_float(
        local.get("funding_extreme_positive"),
        config.funding_extreme_positive,
    )
    config.oi_change_warn = _coerce_float(local.get("oi_change_warn"), config.oi_change_warn)
    config.oi_change_extreme = _coerce_float(local.get("oi_change_extreme"), config.oi_change_extreme)
    config.imbalance_threshold = _coerce_float(local.get("imbalance_threshold"), config.imbalance_threshold)
    config.whale_wall_usd = _coerce_float(local.get("whale_wall_usd"), config.whale_wall_usd)
    config.spread_warn = _coerce_float(local.get("spread_warn"), config.spread_warn)
    config.correlation_window_minutes = _coerce_int(
        local.get("correlation_window_minutes"),
        config.correlation_window_minutes,
    )
    config.independence_threshold = _coerce_float(
        local.get("independence_threshold"),
        config.independence_threshold,
    )
    config.fear_extreme = _coerce_int(local.get("fear_extreme"), config.fear_extreme)
    config.greed_extreme = _coerce_int(local.get("greed_extreme"), config.greed_extreme)
    config.use_dynamic_threshold = _coerce_bool(local.get("use_dynamic_threshold"), config.use_dynamic_threshold)
    config.zscore_threshold = _coerce_float(local.get("zscore_threshold"), config.zscore_threshold)
    config.atr_multiplier = _coerce_float(local.get("atr_multiplier"), config.atr_multiplier)
    config.scoring_enabled = _coerce_bool(local.get("scoring_enabled"), config.scoring_enabled)
    config.scoring_weights = _merge_number_map(config.scoring_weights, local.get("scoring_weights"))
    config.scoring_thresholds = _merge_number_map(
        config.scoring_thresholds,
        local.get("scoring_thresholds"),
        cast=int,
    )
    return config


def _load_anomaly_settings() -> Dict[str, Any]:
    data = _load_json_config(ANOMALY_CONFIG_PATH)
    source = _normalize_anomaly_source(data.get("anomaly_source"))
    return {
        "source": source,
        "local_config": _build_anomaly_config(data),
    }


def _load_symbols() -> List[str]:
    env_raw = os.getenv("NOFX_AI_SIGNAL_SYMBOLS")
    symbols = _normalize_symbols(env_raw)
    if not symbols and signal_config:
        symbols = _normalize_symbols(getattr(signal_config, "AI_SIGNAL_SYMBOLS", None))
    allowed = _load_market_alert_symbols()
    if allowed:
        symbols = allowed
    if not symbols:
        symbols = DEFAULT_SYMBOLS[:]
    return symbols


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


def _realtime_market_enabled() -> bool:
    raw = os.getenv("NOFX_REALTIME_MARKET_ENABLED")
    if raw is not None and str(raw).strip() != "":
        return str(raw).strip().lower() in ("1", "true", "yes", "on")
    if signal_config:
        try:
            return bool(getattr(signal_config, "REALTIME_MARKET_ENABLED", True))
        except Exception:
            return True
    return True


def _market_alert_enabled() -> bool:
    raw = os.getenv("NOFX_MARKET_ALERT_ENABLED")
    if raw is not None and str(raw).strip() != "":
        return str(raw).strip().lower() in ("1", "true", "yes", "on")
    try:
        cfg = _load_json_config(Path(__file__).with_name("market_alert_config.json"))
    except Exception:
        cfg = {}
    return bool(cfg.get("enabled", False))


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


def _market_summary_enabled() -> bool:
    try:
        from ai_market_summary import get_ai_market_config
        config = get_ai_market_config()
        return bool(config.get("enabled", True))
    except Exception as exc:
        logger.warning("[AI Signal] Market summary config unavailable: %s", exc)
        return True


def _start_market_summary_scheduler() -> None:
    """Ensure macro market summary runs on schedule even if main loop slows."""
    def _run():
        logger.info("[AI Signal] Market summary scheduler started.")
        while True:
            _maybe_generate_market_summary()
            time.sleep(60)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


def _start_anomaly_detector(config: Optional[object] = None) -> None:
    """启动异动检测引擎"""
    try:
        from anomaly_detector import AnomalyDetectorEngine, Signal
        from telegram import send_message_with_async_chart

        engine = AnomalyDetectorEngine(config=config)

        def on_signal(sig: Signal):
            emoji = "🔴" if sig.severity == "alert" else "🟡"
            direction = {"bullish": "📈", "bearish": "📉"}.get(sig.direction, "")
            independent = " [独立行情]" if sig.is_independent else ""
            msg = f"{emoji} {sig.symbol} {direction}{independent}\n{sig.description}\n" + "\n".join(sig.triggers)
            try:
                send_message_with_async_chart(msg, sig.symbol)
            except Exception as e:
                logger.warning("[AnomalyDetector] Send failed: %s", e)

        engine.set_signal_callback(on_signal)
        engine.start(interval=60)
        logger.info("[AI Signal] Anomaly detector started.")
    except Exception as exc:
        logger.warning("[AI Signal] Anomaly detector unavailable: %s", exc)


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
    lines = [f"标的: {symbol}", f"时间: {now_bj}"]
    if snapshot:
        price = snapshot.get("price")
        change = snapshot.get("price_change_percent")
        vol = snapshot.get("volume_24h")
        source = snapshot.get("source")
        if price is not None:
            lines.append(f"价格: {price:,.4f}")
        if change is not None:
            lines.append(f"24小时涨跌: {change:,.2f}%")
        if vol is not None:
            lines.append(f"24小时成交量: {vol:,.2f}")
        if source:
            lines.append(f"来源: {source}")
    else:
        lines.append("数据不可用")

    macro_lines = build_macro_brief(max_items=3)
    if macro_lines:
        lines.append("基本面:")
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
    realtime_enabled = _realtime_market_enabled()
    if _market_summary_enabled():
        _start_market_summary_scheduler()
    else:
        logger.info("[AI Signal] Market summary disabled; skipping scheduler.")
    anomaly_settings = _load_anomaly_settings()
    enable_local = anomaly_settings.get("source") in ("local", "both")

    if realtime_enabled:
        # 启动市场异动警报调度器
        if _market_alert_enabled():
            try:
                from market_alert import start_market_alert_scheduler
                start_market_alert_scheduler()
            except Exception as exc:
                logger.warning("[AI Signal] Market alert scheduler unavailable: %s", exc)
        else:
            logger.info("[AI Signal] Market alert disabled; skipping.")
        # 启动异动检测引擎
        if enable_local:
            _start_anomaly_detector(anomaly_settings.get("local_config"))
        else:
            logger.info("[AI Signal] Local anomaly detector skipped. source=%s", anomaly_settings.get("source"))
        # 启动宏观经济数据发布监控
        try:
            from macro_event_monitor import start_macro_event_monitor
            start_macro_event_monitor()
        except Exception as exc:
            logger.warning("[AI Signal] Macro event monitor unavailable: %s", exc)
    else:
        logger.info("[AI Signal] Realtime market disabled; skipping movement, alerts, anomaly, macro monitors.")
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

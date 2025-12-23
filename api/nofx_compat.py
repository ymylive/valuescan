"""
NOFX API compatibility layer (Flask).

The reference NOFX project uses a different backend stack, but its web UI
expects a set of `/api/*` endpoints. This module implements a pragmatic subset
of those endpoints so the NOFX web UI can run against this repository.
"""

from __future__ import annotations

import json
import os
import re
import socket
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, Response, jsonify, request

from ai_trading.exchanges.ccxt_executor import CCXTExecutor
from ai_trading.exchanges.config import get_exchange_config
from ai_trading.llm.config import get_llm_config

try:
    from api.metrics_calculator import MetricsCalculator
    from api.performance_db import get_performance_db

    PERFORMANCE_AVAILABLE = True
except Exception:
    PERFORMANCE_AVAILABLE = False


nofx_bp = Blueprint("nofx_compat", __name__)

BASE_DIR = Path(__file__).parent.parent
STATE_PATH = BASE_DIR / "nofx_state.json"

_DECISION_LOOP_ENABLED = (
    os.getenv("NOFX_DECISION_LOOP", "1").strip().lower() not in {"0", "false", "no", "off"}
)
_DECISION_KEEP_LIMIT = int(os.getenv("NOFX_DECISION_KEEP_LIMIT", "200") or "200")
_DECISION_WORKER_LOCK_PATH = Path(
    os.getenv("NOFX_DECISION_WORKER_LOCK", "/tmp/valuescan_nofx_decision.lock")
)
_DECISION_WORKER_STARTED = False
_DECISION_WORKER_GUARD = threading.Lock()
_DECISION_SCHEDULE: Dict[str, float] = {}
_DECISION_TAG_RE = re.compile(r"(?s)<decision>\s*(.*?)\s*</decision>")
_REASON_TAG_RE = re.compile(r"(?s)<reasoning>\s*(.*?)\s*</reasoning>")
_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|```$", re.IGNORECASE)
_DEFAULT_LLM_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "grok": "https://api.x.ai/v1",
    "kimi": "https://api.moonshot.cn/v1",
}
_DEFAULT_LLM_MODELS = {
    "openai": "gpt-4o-mini",
    "deepseek": "deepseek-chat",
    "qwen": "qwen-plus",
    "grok": "grok-3-latest",
    "kimi": "moonshot-v1-8k",
}


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _require_auth() -> Optional[Response]:
    auth = (request.headers.get("Authorization") or "").strip()
    if not auth.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401
    token = auth[len("Bearer ") :].strip()
    if not token:
        return jsonify({"error": "Unauthorized"}), 401
    return None


def _run_async(coro):
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@dataclass
class TraderState:
    trader_id: str
    trader_name: str
    ai_model: str
    exchange_id: str
    is_running: bool
    show_in_competition: bool
    scan_interval_minutes: int
    initial_balance: float
    is_cross_margin: bool
    strategy_id: Optional[str] = None
    strategy_name: Optional[str] = None
    custom_prompt: str = ""
    system_prompt_template: str = ""
    use_coin_pool: bool = False
    use_oi_top: bool = False
    created_at: str = ""
    updated_at: str = ""
    start_time: str = ""
    call_count: int = 0

    def to_trader_info(self) -> Dict[str, Any]:
        return {
            "trader_id": self.trader_id,
            "trader_name": self.trader_name,
            "ai_model": self.ai_model,
            "exchange_id": self.exchange_id,
            "is_running": self.is_running,
            "show_in_competition": self.show_in_competition,
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "custom_prompt": self.custom_prompt,
            "use_coin_pool": self.use_coin_pool,
            "use_oi_top": self.use_oi_top,
            "system_prompt_template": self.system_prompt_template,
        }

    def to_config(self) -> Dict[str, Any]:
        return {
            "trader_id": self.trader_id,
            "trader_name": self.trader_name,
            "ai_model": self.ai_model,
            "exchange_id": self.exchange_id,
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "is_cross_margin": self.is_cross_margin,
            "show_in_competition": self.show_in_competition,
            "scan_interval_minutes": self.scan_interval_minutes,
            "initial_balance": self.initial_balance,
            "is_running": self.is_running,
            "btc_eth_leverage": 0,
            "altcoin_leverage": 0,
            "trading_symbols": "",
            "custom_prompt": self.custom_prompt,
            "override_base_prompt": False,
            "system_prompt_template": self.system_prompt_template,
            "use_coin_pool": self.use_coin_pool,
            "use_oi_top": self.use_oi_top,
        }

    def to_system_status(self) -> Dict[str, Any]:
        start_time = self.start_time or _now_iso()
        runtime_minutes = 0
        if self.start_time:
            try:
                start_ts = time.mktime(
                    time.strptime(self.start_time, "%Y-%m-%dT%H:%M:%SZ")
                )
                runtime_minutes = max(0, int((time.time() - start_ts) / 60))
            except Exception:
                runtime_minutes = 0

        return {
            "trader_id": self.trader_id,
            "trader_name": self.trader_name,
            "ai_model": self.ai_model,
            "is_running": bool(self.is_running),
            "start_time": start_time,
            "runtime_minutes": runtime_minutes,
            "call_count": int(self.call_count or 0),
            "initial_balance": float(self.initial_balance or 0.0),
            "scan_interval": f"{int(self.scan_interval_minutes)}m",
            "stop_until": "",
            "last_reset_time": "",
            "ai_provider": self.ai_model,
        }


class _StateStore:
    def __init__(self, path: Path):
        self._path = path
        self._lock = threading.Lock()

    def _default_state(self) -> Dict[str, Any]:
        now = _now_iso()
        default_trader = TraderState(
            trader_id="default",
            trader_name="Default Trader",
            ai_model="openai",
            exchange_id="binance",
            is_running=False,
            show_in_competition=True,
            scan_interval_minutes=5,
            initial_balance=1000.0,
            is_cross_margin=True,
            created_at=now,
            updated_at=now,
        )
        return {
            "traders": {default_trader.trader_id: default_trader.to_config()},
            "decisions": {},
            "strategies": {},
            "debates": {},
            "backtests": {},
        }

    def load(self) -> Dict[str, Any]:
        with self._lock:
            if not self._path.exists():
                state = self._default_state()
                self._path.write_text(json.dumps(state, indent=2), encoding="utf-8")
                return state

            try:
                payload = json.loads(self._path.read_text(encoding="utf-8") or "{}")
                if not isinstance(payload, dict):
                    raise ValueError("Invalid state")
                return payload
            except Exception:
                state = self._default_state()
                self._path.write_text(json.dumps(state, indent=2), encoding="utf-8")
                return state

    def save(self, payload: Dict[str, Any]) -> None:
        with self._lock:
            self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _from_config(self, trader_id: str, cfg: Dict[str, Any]) -> TraderState:
        return TraderState(
            trader_id=trader_id,
            trader_name=str(cfg.get("trader_name") or trader_id),
            ai_model=str(cfg.get("ai_model") or "openai").lower(),
            exchange_id=str(cfg.get("exchange_id") or "binance"),
            is_running=bool(cfg.get("is_running", False)),
            show_in_competition=bool(cfg.get("show_in_competition", True)),
            scan_interval_minutes=int(cfg.get("scan_interval_minutes") or 5),
            initial_balance=float(cfg.get("initial_balance") or 1000.0),
            is_cross_margin=bool(cfg.get("is_cross_margin", True)),
            strategy_id=cfg.get("strategy_id"),
            strategy_name=cfg.get("strategy_name"),
            custom_prompt=str(cfg.get("custom_prompt") or ""),
            system_prompt_template=str(cfg.get("system_prompt_template") or ""),
            use_coin_pool=bool(cfg.get("use_coin_pool", False)),
            use_oi_top=bool(cfg.get("use_oi_top", False)),
            created_at=str(cfg.get("created_at") or ""),
            updated_at=str(cfg.get("updated_at") or ""),
            start_time=str(cfg.get("start_time") or ""),
            call_count=int(cfg.get("call_count") or 0),
        )

    def list_traders(self) -> List[TraderState]:
        payload = self.load()
        traders = payload.get("traders") or {}
        if not isinstance(traders, dict):
            return []
        out: List[TraderState] = []
        for tid, cfg in traders.items():
            if isinstance(cfg, dict):
                out.append(self._from_config(str(tid), cfg))
        return out

    def get_trader(self, trader_id: str) -> Optional[TraderState]:
        trader_id = (trader_id or "").strip()
        if not trader_id:
            return None
        payload = self.load()
        traders = payload.get("traders") or {}
        if not isinstance(traders, dict):
            return None
        cfg = traders.get(trader_id)
        if not isinstance(cfg, dict):
            return None
        return self._from_config(trader_id, cfg)

    def upsert_trader(self, trader: TraderState) -> TraderState:
        payload = self.load()
        traders = payload.setdefault("traders", {})
        if not isinstance(traders, dict):
            payload["traders"] = {}
            traders = payload["traders"]

        now = _now_iso()
        trader.updated_at = now
        if not trader.created_at:
            trader.created_at = now
        traders[trader.trader_id] = trader.to_config()
        self.save(payload)
        return trader

    def delete_trader(self, trader_id: str) -> bool:
        payload = self.load()
        traders = payload.get("traders") or {}
        if not isinstance(traders, dict):
            return False
        if trader_id not in traders:
            return False
        del traders[trader_id]
        self.save(payload)
        return True

    def list_decisions(self, trader_id: str) -> List[Dict[str, Any]]:
        payload = self.load()
        decisions = payload.get("decisions") or {}
        if not isinstance(decisions, dict):
            return []
        items = decisions.get(trader_id) or []
        if not isinstance(items, list):
            return []
        return [x for x in items if isinstance(x, dict)]

    def append_decision(self, trader_id: str, record: Dict[str, Any]) -> None:
        payload = self.load()
        decisions = payload.setdefault("decisions", {})
        if not isinstance(decisions, dict):
            payload["decisions"] = {}
            decisions = payload["decisions"]
        items = decisions.get(trader_id)
        if not isinstance(items, list):
            items = []
        items.append(record)
        if _DECISION_KEEP_LIMIT > 0 and len(items) > _DECISION_KEEP_LIMIT:
            items = items[-_DECISION_KEEP_LIMIT :]
        decisions[trader_id] = items
        self.save(payload)


_store = _StateStore(STATE_PATH)
_ensure_decision_worker()


def _resolve_trader_id() -> str:
    trader_id = (request.args.get("trader_id") or "").strip()
    return trader_id or "default"


def _exchange_type_from_exchange_id(exchange_id: str) -> str:
    exchange_id = (exchange_id or "").strip().lower()
    return exchange_id or "binance"


def _normalize_secret(value: Any) -> Optional[str]:
    if value is None:
        return None
    v = str(value).strip()
    return v if v else None


def _exchange_template(exchange_type: str, cfg) -> Optional[Dict[str, Any]]:
    exchange_type = (exchange_type or "").strip().lower()
    for item in getattr(cfg, "SUPPORTED_EXCHANGES", []) or []:
        if str(item.get("exchange_type") or "").strip().lower() == exchange_type:
            return item
    return None


def _is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def _resolve_socks5_proxy() -> str:
    for key in ("SOCKS5_PROXY", "VALUESCAN_SOCKS5_PROXY"):
        value = (os.getenv(key) or "").strip()
        if value.startswith("socks5://"):
            return value
    for port in (1080, 10808):
        if _is_port_open("127.0.0.1", port):
            return f"socks5://127.0.0.1:{port}"
    return ""


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _acquire_worker_lock() -> bool:
    path = _DECISION_WORKER_LOCK_PATH
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, str(os.getpid()).encode("utf-8"))
        finally:
            os.close(fd)
        return True
    except FileExistsError:
        try:
            pid_text = path.read_text(encoding="utf-8", errors="ignore").strip()
            pid = int(pid_text) if pid_text else 0
        except Exception:
            pid = 0
        if pid and _pid_alive(pid):
            return False
        try:
            path.unlink()
        except Exception:
            return False
        return _acquire_worker_lock()
    except Exception:
        return False


def _normalize_provider_name(value: str) -> str:
    name = (value or "").strip().lower()
    aliases = {
        "chatgpt": "openai",
        "gpt": "openai",
        "openai-compatible": "openai",
        "openai_compatible": "openai",
        "anthropic": "claude",
        "google": "gemini",
        "moonshot": "kimi",
        "xai": "grok",
    }
    return aliases.get(name, name)


def _select_llm_provider(trader: TraderState):
    cfg = get_llm_config()
    preferred = _normalize_provider_name(trader.ai_model)
    if preferred:
        try:
            provider = cfg.get_provider(preferred)
            if provider and str(getattr(provider, "api_key", "") or "").strip():
                return provider
        except Exception:
            pass
    try:
        conf = cfg.get_config()
        providers = conf.providers if conf else []
    except Exception:
        providers = []
    for provider in providers:
        if str(getattr(provider, "api_key", "") or "").strip():
            return provider
    return None


def _build_requests_proxies() -> Optional[Dict[str, str]]:
    proxy = _resolve_socks5_proxy()
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def _call_llm(provider, system_prompt: str, user_prompt: str) -> Tuple[str, str]:
    try:
        import requests
    except Exception as exc:
        return "", f"requests not available: {exc}"

    name = _normalize_provider_name(str(getattr(provider, "name", "") or ""))
    api_key = str(getattr(provider, "api_key", "") or "").strip()
    base_url = str(getattr(provider, "base_url", "") or "").strip()
    model = str(getattr(provider, "model", "") or "").strip()

    if not api_key:
        return "", "missing api_key"
    if not base_url:
        base_url = _DEFAULT_LLM_BASE_URLS.get(name, "")
    if not model:
        model = _DEFAULT_LLM_MODELS.get(name, "")
    if not base_url or not model:
        return "", f"unsupported provider '{name}'"

    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    try:
        resp = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=40,
            proxies=_build_requests_proxies(),
        )
        resp.raise_for_status()
        data = resp.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        return str(content or "").strip(), ""
    except Exception as exc:
        return "", str(exc)


def _strip_code_fences(text: str) -> str:
    return _CODE_FENCE_RE.sub("", (text or "").strip()).strip()


def _parse_decision_response(text: str) -> Tuple[List[Dict[str, Any]], str, str]:
    if not text:
        return [], "", "empty ai response"
    reasoning = ""
    match = _REASON_TAG_RE.search(text)
    if match:
        reasoning = (match.group(1) or "").strip()
    raw = ""
    match = _DECISION_TAG_RE.search(text)
    if match:
        raw = match.group(1)
    if not raw:
        raw = text
    raw = _strip_code_fences(raw)
    raw = raw.strip()
    if not raw:
        return [], reasoning, "empty decision content"
    try:
        parsed = json.loads(raw)
    except Exception as exc:
        return [], reasoning, f"invalid decision json: {exc}"
    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        return [], reasoning, "decision json must be array"
    out = [item for item in parsed if isinstance(item, dict)]
    return out, reasoning, ""


def _build_decision_actions(
    raw_decisions: List[Dict[str, Any]],
    default_symbol: str,
) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    now_iso = _now_iso()
    for item in raw_decisions:
        action = str(item.get("action") or item.get("decision") or "hold").strip()
        symbol = str(item.get("symbol") or default_symbol).strip() or default_symbol
        leverage = int(float(item.get("leverage") or 0) or 0)
        price = float(item.get("price") or item.get("entry_price") or 0.0)
        stop_loss = item.get("stop_loss") or item.get("stop_loss_pct")
        take_profit = item.get("take_profit") or item.get("take_profit_pct")
        confidence = item.get("confidence")
        reasoning = item.get("reasoning")
        actions.append(
            {
                "action": action,
                "symbol": symbol,
                "quantity": float(item.get("quantity") or 0.0),
                "leverage": leverage,
                "price": price,
                "stop_loss": float(stop_loss) if stop_loss is not None else None,
                "take_profit": float(take_profit) if take_profit is not None else None,
                "confidence": float(confidence) if confidence is not None else None,
                "reasoning": str(reasoning or "").strip() or None,
                "order_id": 0,
                "timestamp": now_iso,
                "success": True,
                "error": None,
            }
        )
    if actions:
        return actions
    return [
        {
            "action": "hold",
            "symbol": default_symbol,
            "quantity": 0.0,
            "leverage": 0,
            "price": 0.0,
            "stop_loss": None,
            "take_profit": None,
            "confidence": 50,
            "reasoning": "No actionable decision from AI.",
            "order_id": 0,
            "timestamp": now_iso,
            "success": False,
            "error": "empty decision list",
        }
    ]


def _build_account_snapshot(exchange_type: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    balance_ok, balance, _balance_err = _get_balance(exchange_type)
    pos_ok, positions, _pos_err = _get_positions(exchange_type)
    wallet_balance = 0.0
    available_balance = 0.0
    unrealized = 0.0
    if balance_ok and isinstance(balance, dict):
        try:
            wallet_balance = float(balance.get("total_wallet_balance") or 0.0)
        except Exception:
            wallet_balance = 0.0
        try:
            available_balance = float(balance.get("available_balance") or 0.0)
        except Exception:
            available_balance = 0.0
    if pos_ok and isinstance(positions, list):
        for p in positions:
            try:
                unrealized += float(p.get("unrealized_pnl") or 0.0)
            except Exception:
                continue
    snapshot = {
        "total_balance": wallet_balance,
        "available_balance": available_balance or wallet_balance,
        "total_unrealized_profit": unrealized,
        "position_count": len(positions) if pos_ok else 0,
        "margin_used_pct": 0.0,
    }
    return snapshot, positions if pos_ok else []


def _generate_decision_record(trader: TraderState) -> Dict[str, Any]:
    exchange_type = _exchange_type_from_exchange_id(trader.exchange_id)
    snapshot, positions = _build_account_snapshot(exchange_type)
    candidate_coins = ["BTCUSDT", "ETHUSDT"]
    system_prompt = trader.system_prompt_template.strip() or (
        "You are a crypto futures trading AI. "
        "Return <reasoning> and <decision> JSON array."
    )
    user_prompt = (
        "Account snapshot:\n"
        f"{json.dumps(snapshot, ensure_ascii=True)}\n\n"
        "Positions:\n"
        f"{json.dumps(positions, ensure_ascii=True)}\n\n"
        "Candidates:\n"
        f"{json.dumps(candidate_coins, ensure_ascii=True)}\n\n"
        "Respond with:\n"
        "<reasoning>...</reasoning>\n"
        "<decision>[{\"action\":\"hold\",\"symbol\":\"BTCUSDT\",\"confidence\":50}]</decision>"
    )

    provider = _select_llm_provider(trader)
    ai_response = ""
    ai_error = ""
    if provider:
        ai_response, ai_error = _call_llm(provider, system_prompt, user_prompt)
    else:
        ai_error = "no llm provider configured"

    raw_decisions, reasoning, parse_error = _parse_decision_response(ai_response)
    if not raw_decisions and ai_error:
        reasoning = reasoning or "AI call failed."
    decisions = _build_decision_actions(raw_decisions, candidate_coins[0])
    decision_json = (
        json.dumps(raw_decisions, ensure_ascii=True) if raw_decisions else ""
    )
    if not decision_json:
        decision_json = json.dumps(decisions, ensure_ascii=True)

    error_message = ai_error or parse_error
    success = not bool(error_message)
    execution_log = []
    if ai_error:
        execution_log.append(f"AI call error: {ai_error}")
    if parse_error:
        execution_log.append(f"Decision parse error: {parse_error}")
    if not execution_log:
        execution_log.append("AI decision recorded.")

    cycle_number = int(trader.call_count or 0) + 1
    return {
        "timestamp": _now_iso(),
        "cycle_number": cycle_number,
        "input_prompt": user_prompt,
        "cot_trace": reasoning,
        "decision_json": decision_json,
        "account_state": snapshot,
        "positions": positions,
        "candidate_coins": candidate_coins,
        "decisions": decisions,
        "execution_log": execution_log,
        "success": success,
        "error_message": error_message or None,
    }


def _decision_worker() -> None:
    while True:
        try:
            now = time.time()
            traders = _store.list_traders()
            for trader in traders:
                if not trader.is_running:
                    continue
                interval = max(1, int(trader.scan_interval_minutes or 5)) * 60
                last_run = _DECISION_SCHEDULE.get(trader.trader_id, 0.0)
                if now - last_run < interval:
                    continue
                _DECISION_SCHEDULE[trader.trader_id] = now
                record = _generate_decision_record(trader)
                _store.append_decision(trader.trader_id, record)
                trader.call_count = int(trader.call_count or 0) + 1
                _store.upsert_trader(trader)
        except Exception:
            pass
        time.sleep(5)


def _ensure_decision_worker() -> None:
    global _DECISION_WORKER_STARTED
    if not _DECISION_LOOP_ENABLED:
        return
    with _DECISION_WORKER_GUARD:
        if _DECISION_WORKER_STARTED:
            return
        if not _acquire_worker_lock():
            return
        thread = threading.Thread(target=_decision_worker, daemon=True)
        thread.start()
        _DECISION_WORKER_STARTED = True


def _build_binance_futures_client(ex) -> Tuple[Optional[Any], str]:
    try:
        from binance.client import Client
    except Exception:
        return None, "python-binance not installed"

    try:
        requests_params = None
        proxy = _resolve_socks5_proxy()
        if proxy:
            requests_params = {
                "proxies": {
                    "http": proxy,
                    "https": proxy,
                }
            }
        client = Client(
            str(ex.api_key).strip(),
            str(ex.api_secret).strip(),
            requests_params=requests_params,
            testnet=bool(getattr(ex, "testnet", False)),
        )
        if getattr(ex, "testnet", False):
            client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"
        return client, ""
    except Exception as e:
        return None, str(e)


def _get_positions(exchange_type: str) -> Tuple[bool, List[Dict[str, Any]], str]:
    cfg = get_exchange_config()
    exchange_type = (exchange_type or "").strip().lower() or "binance"

    if exchange_type == "binance":
        ex = cfg.get_exchange("binance")
        if not ex or not ex.enabled:
            return False, [], "Binance not enabled"
        if not (ex.api_key or "").strip() or not (ex.api_secret or "").strip():
            return False, [], "Missing Binance API key/secret"

        client, err = _build_binance_futures_client(ex)
        if not client:
            return False, [], err
        try:
            raw_positions = client.futures_position_information()
        except Exception as e:
            return False, [], str(e)

        positions: List[Dict[str, Any]] = []
        for pos in raw_positions or []:
            try:
                amt = float(pos.get("positionAmt", 0) or 0)
            except Exception:
                continue
            if amt == 0:
                continue

            side = str(pos.get("positionSide") or "").upper()
            if side not in ("LONG", "SHORT"):
                side = "LONG" if amt > 0 else "SHORT"

            def _f(key: str) -> float:
                try:
                    return float(pos.get(key, 0) or 0)
                except Exception:
                    return 0.0

            entry_price = _f("entryPrice")
            mark_price = _f("markPrice") or entry_price
            unrealized_pnl = _f("unRealizedProfit")
            liquidation_price = _f("liquidationPrice")
            leverage = 0.0
            try:
                leverage = float(pos.get("leverage", 0) or 0)
            except Exception:
                leverage = 0.0

            qty = abs(amt)
            pnl_pct = 0.0
            denom = entry_price * qty
            if denom:
                pnl_pct = (unrealized_pnl / denom) * 100

            positions.append(
                {
                    "symbol": str(pos.get("symbol") or ""),
                    "side": side,
                    "entry_price": entry_price,
                    "mark_price": mark_price,
                    "quantity": qty,
                    "leverage": leverage,
                    "unrealized_pnl": unrealized_pnl,
                    "unrealized_pnl_pct": pnl_pct,
                    "liquidation_price": liquidation_price,
                    "margin_used": 0.0,
                }
            )

        return True, positions, ""

    ex = cfg.get_exchange(exchange_type)
    if not ex or not ex.enabled:
        return False, [], f"{exchange_type} not enabled"
    if not (ex.api_key or "").strip() or not (ex.api_secret or "").strip():
        return False, [], f"Missing {exchange_type} API key/secret"

    executor = CCXTExecutor(
        exchange_id=exchange_type,
        api_key=str(ex.api_key or "").strip(),
        api_secret=str(ex.api_secret or "").strip(),
        passphrase=str(ex.passphrase or "").strip(),
        testnet=bool(ex.testnet),
        base_url=ex.base_url,
        default_type="swap",
    )
    data = _run_async(executor.fetch_positions())
    if not data.get("success"):
        return False, [], str(data.get("error") or "Failed")

    positions: List[Dict[str, Any]] = []
    for pos in data.get("positions") or []:
        if not isinstance(pos, dict):
            continue
        positions.append(
            {
                "symbol": str(pos.get("symbol") or ""),
                "side": str(pos.get("side") or "").upper(),
                "entry_price": float(pos.get("entry_price") or 0.0),
                "mark_price": float(pos.get("mark_price") or 0.0),
                "quantity": float(pos.get("quantity") or 0.0),
                "leverage": float(pos.get("leverage") or 0.0),
                "unrealized_pnl": float(pos.get("unrealized_pnl") or 0.0),
                "unrealized_pnl_pct": float(pos.get("unrealized_pnl_pct") or 0.0),
                "liquidation_price": float(pos.get("liquidation_price") or 0.0),
                "margin_used": float(pos.get("margin_used") or 0.0),
            }
        )
    return True, positions, ""


def _get_balance(exchange_type: str) -> Tuple[bool, Dict[str, float], str]:
    cfg = get_exchange_config()
    exchange_type = (exchange_type or "").strip().lower() or "binance"

    if exchange_type == "binance":
        ex = cfg.get_exchange("binance")
        if not ex or not ex.enabled:
            return False, {}, "Binance not enabled"
        if not (ex.api_key or "").strip() or not (ex.api_secret or "").strip():
            return False, {}, "Missing Binance API key/secret"

        client, err = _build_binance_futures_client(ex)
        if not client:
            return False, {}, err
        try:
            account = client.futures_account()
        except Exception as e:
            return False, {}, str(e)

        def _f(key: str) -> float:
            try:
                return float(account.get(key, 0) or 0)
            except Exception:
                return 0.0

        total_wallet = _f("totalWalletBalance")
        available = _f("availableBalance")
        unrealized = _f("totalUnrealizedProfit")
        return True, {
            "total_wallet_balance": total_wallet,
            "available_balance": available,
            "total_unrealized_profit": unrealized,
            "total_equity": total_wallet + unrealized,
        }, ""

    return False, {}, f"Balance not supported for {exchange_type}"


# ---------------------------------------------------------------------------
# Auth (demo)
# ---------------------------------------------------------------------------


@nofx_bp.route("/api/login", methods=["POST"])
def nofx_login():
    data = request.get_json() or {}
    email = str(data.get("email") or "").strip()
    password = str(data.get("password") or "").strip()
    if not email or not password:
        return jsonify({"error": "Missing email/password"}), 400
    return jsonify({"requires_otp": True, "user_id": email, "message": "OTP"})


@nofx_bp.route("/api/verify-otp", methods=["POST"])
def nofx_verify_otp():
    data = request.get_json() or {}
    user_id = str(data.get("user_id") or "").strip()
    otp_code = str(data.get("otp_code") or "").strip()
    if not user_id or not otp_code:
        return jsonify({"error": "Missing user_id/otp_code"}), 400
    return jsonify(
        {
            "token": f"demo-{uuid.uuid4().hex}",
            "user_id": user_id,
            "email": user_id,
            "message": "Login success",
        }
    )


@nofx_bp.route("/api/admin-login", methods=["POST"])
def nofx_admin_login():
    data = request.get_json() or {}
    password = str(data.get("password") or "").strip()
    if not password:
        return jsonify({"error": "Missing password"}), 400
    return jsonify(
        {
            "token": f"admin-{uuid.uuid4().hex}",
            "user_id": "admin",
            "email": "admin@localhost",
            "message": "Login success",
        }
    )


@nofx_bp.route("/api/logout", methods=["POST"])
def nofx_logout():
    return jsonify({"message": "Logged out"})


@nofx_bp.route("/api/register", methods=["POST"])
def nofx_register():
    data = request.get_json() or {}
    email = str(data.get("email") or "").strip()
    password = str(data.get("password") or "").strip()
    if not email or not password:
        return jsonify({"error": "Missing email/password"}), 400
    return jsonify(
        {
            "user_id": email,
            "otp_secret": "DEMO-OTP-SECRET",
            "qr_code_url": "",
            "message": "Registered",
        }
    )


@nofx_bp.route("/api/complete-registration", methods=["POST"])
def nofx_complete_registration():
    data = request.get_json() or {}
    user_id = str(data.get("user_id") or "").strip()
    otp_code = str(data.get("otp_code") or "").strip()
    if not user_id or not otp_code:
        return jsonify({"error": "Missing user_id/otp_code"}), 400
    return jsonify(
        {
            "token": f"demo-{uuid.uuid4().hex}",
            "user_id": user_id,
            "email": user_id,
            "message": "Registration complete",
        }
    )


@nofx_bp.route("/api/reset-password", methods=["POST"])
def nofx_reset_password():
    data = request.get_json() or {}
    email = str(data.get("email") or "").strip()
    new_password = str(data.get("new_password") or "").strip()
    otp_code = str(data.get("otp_code") or "").strip()
    if not email or not new_password or not otp_code:
        return jsonify({"error": "Missing fields"}), 400
    return jsonify({"message": "Password reset"})


# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Crypto (compat)
# ---------------------------------------------------------------------------

@nofx_bp.route("/api/crypto/config", methods=["GET"])
def crypto_config():
    return jsonify({"transport_encryption": False})


@nofx_bp.route("/api/crypto/public-key", methods=["GET"])
def crypto_public_key():
    return jsonify({"transport_encryption": False, "public_key": ""})


@nofx_bp.route("/api/crypto/decrypt", methods=["POST"])
def crypto_decrypt():
    return jsonify({"error": "transport_encryption disabled"}), 400
# Models
# ---------------------------------------------------------------------------


@nofx_bp.route("/api/supported-models", methods=["GET"])
def supported_models():
    cfg = get_llm_config()
    providers = list(getattr(cfg, "SUPPORTED_PROVIDERS", []))
    out: List[Dict[str, Any]] = []
    for name in providers:
        out.append(
            {
                "id": name,
                "name": name.upper(),
                "provider": name,
                "enabled": False,
            }
        )
    return jsonify(out)


@nofx_bp.route("/api/models", methods=["GET", "PUT"])
def models():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err

    cfg = get_llm_config()

    if request.method == "GET":
        conf = cfg.get_config()
        providers = conf.providers if conf else []
        items: List[Dict[str, Any]] = []
        for p in providers:
            items.append(
                {
                    "id": p.name,
                    "name": (p.model or p.name).strip() or p.name,
                    "provider": p.name,
                    "enabled": bool((p.api_key or "").strip()),
                    "customApiUrl": p.base_url or "",
                    "customModelName": p.model or "",
                }
            )
        return jsonify(items)

    data = request.get_json() or {}
    models_map = data.get("models")
    if isinstance(models_map, list):
        normalized: Dict[str, Dict[str, Any]] = {}
        for item in models_map:
            if not isinstance(item, dict):
                continue
            key = (
                item.get("id")
                or item.get("provider")
                or item.get("name")
                or ""
            )
            key = str(key).strip().lower()
            if not key:
                continue
            normalized[key] = item
        models_map = normalized
    elif isinstance(models_map, dict):
        pass
    elif isinstance(data, dict) and data and all(isinstance(v, dict) for v in data.values()):
        models_map = data
    else:
        models_map = {}
    if not isinstance(models_map, dict):
        return jsonify({"error": "models must be an object"}), 400

    aliases = {
        "gpt": "openai",
        "chatgpt": "openai",
        "openai-compatible": "openai",
        "openai_compatible": "openai",
        "claude": "anthropic",
        "google": "gemini",
        "xai": "grok",
        "moonshot": "kimi",
    }
    errors: List[str] = []

    for model_id, item in models_map.items():
        if not isinstance(item, dict):
            continue
        name = (
            str(item.get("id") or item.get("provider") or model_id or "")
            .strip()
            .lower()
        )
        if not name:
            continue
        if "/" in name:
            name = name.split("/", 1)[0].strip()
        if ":" in name:
            name = name.split(":", 1)[0].strip()
        name = aliases.get(name, name)

        if name not in getattr(cfg, "SUPPORTED_PROVIDERS", []):
            errors.append(f"Unsupported model '{name}'")
            continue

        enabled = item.get("enabled", True)
        if isinstance(enabled, str):
            enabled = enabled.strip().lower() not in {"false", "0", "no", "off"}
        api_key = item.get("api_key")
        if api_key is None:
            api_key = item.get("apiKey")
        base_url = item.get("custom_api_url")
        if base_url is None:
            base_url = item.get("customApiUrl")
        if base_url is None:
            base_url = item.get("base_url")
        if base_url is None:
            base_url = item.get("baseUrl")
        model_name = item.get("custom_model_name")
        if model_name is None:
            model_name = item.get("customModelName")
        if model_name is None:
            model_name = item.get("model")
        if enabled is None:
            enabled = bool(str(api_key or "").strip())
        enabled = bool(enabled)
        clear_api_key = (not enabled) or (api_key is not None and not str(api_key).strip())

        ok = cfg.update_provider_settings(
            name,
            api_key=(
                str(api_key).strip()
                if (api_key is not None and str(api_key).strip())
                else None
            ),
            model=(
                str(model_name).strip()
                if (model_name is not None and str(model_name).strip())
                else None
            ),
            base_url=str(base_url).strip() if base_url is not None else None,
            clear_api_key=clear_api_key,
        )
        if not ok:
            provider = cfg.get_provider(name)
            if provider is None:
                errors.append(f"Failed to update model '{name}'")
                continue
            # Allow any API key format for NOFX compatibility.
            api_key_str = str(api_key).strip() if api_key is not None else ""
            if not enabled or (api_key is not None and not api_key_str):
                provider.api_key = ""
            elif api_key is not None:
                provider.api_key = api_key_str
            if model_name is not None and str(model_name).strip():
                provider.model = str(model_name).strip()
            if base_url is not None:
                base_url_str = str(base_url).strip()
                provider.base_url = base_url_str or None

    if errors:
        return jsonify({"error": "; ".join(errors)}), 400

    cfg.save()
    return jsonify({"message": "OK"})


@nofx_bp.route("/api/prompt-templates", methods=["GET"])
def prompt_templates():
    return jsonify(
        {
            "templates": [
                {"name": "default"},
                {"name": "conservative"},
                {"name": "aggressive"},
                {"name": "scalping"},
            ]
        }
    )


# ---------------------------------------------------------------------------
# Exchanges
# ---------------------------------------------------------------------------


@nofx_bp.route("/api/supported-exchanges", methods=["GET"])
def supported_exchanges():
    cfg = get_exchange_config()
    templates = getattr(cfg, "SUPPORTED_EXCHANGES", []) or []
    out: List[Dict[str, Any]] = []
    for item in templates:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "id": "",
                "exchange_type": str(item.get("exchange_type") or ""),
                "account_name": "",
                "name": str(item.get("name") or ""),
                "type": item.get("type") or "cex",
                "enabled": False,
            }
        )
    return jsonify(out)


@nofx_bp.route("/api/exchanges", methods=["GET", "PUT", "POST"])
def exchanges():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err

    cfg = get_exchange_config()

    if request.method == "GET":
        safe = cfg.get_safe_config()
        items: List[Dict[str, Any]] = []
        for ex in safe.get("exchanges", []):
            if not isinstance(ex, dict):
                continue
            exchange_type = str(ex.get("exchange_type") or "")
            items.append(
                {
                    "id": exchange_type,
                    "exchange_type": exchange_type,
                    "account_name": "default",
                    "name": str(ex.get("name") or exchange_type),
                    "type": ex.get("type") or "cex",
                    "enabled": bool(ex.get("enabled", False)),
                    "testnet": bool(ex.get("testnet", False)),
                }
            )
        return jsonify(items)

    if request.method == "POST":
        data = request.get_json() or {}
        exchange_type = str(data.get("exchange_type") or "").strip().lower()
        if not exchange_type:
            return jsonify({"error": "Missing exchange_type"}), 400

        api_key = _normalize_secret(data.get("api_key"))
        api_secret = _normalize_secret(data.get("secret_key"))
        passphrase = _normalize_secret(data.get("passphrase"))

        template = _exchange_template(exchange_type, cfg)
        if template and (template.get("type") or "").lower() == "cex":
            if not api_key or not api_secret:
                return jsonify({"error": "Missing API key/secret"}), 400
        if exchange_type in {"okx", "bitget"} and not passphrase:
            return jsonify({"error": "Missing passphrase"}), 400

        ok = cfg.update_exchange(
            exchange_type,
            enabled=bool(data.get("enabled", True)),
            testnet=(
                bool(data.get("testnet", False)) if "testnet" in data else None
            ),
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
        )
        if not ok:
            return jsonify({"error": f"Failed to create exchange '{exchange_type}'"}), 400
        cfg.save()
        return jsonify({"id": exchange_type})

    data = request.get_json() or {}
    ex_map = data.get("exchanges") or {}
    if not isinstance(ex_map, dict):
        return jsonify({"error": "exchanges must be an object"}), 400

    for exchange_type, item in ex_map.items():
        if not isinstance(item, dict):
            continue
        exchange_type = str(exchange_type or "").strip().lower()
        if not exchange_type:
            continue

        enabled = bool(item.get("enabled", True))
        api_key = item.get("api_key")
        secret_key = item.get("secret_key")
        passphrase = item.get("passphrase")
        testnet = item.get("testnet")

        clear_api_key = (not enabled) or (api_key is not None and not str(api_key).strip())
        clear_api_secret = (not enabled) or (secret_key is not None and not str(secret_key).strip())
        clear_passphrase = (not enabled) or (passphrase is not None and not str(passphrase).strip())

        ok = cfg.update_exchange(
            exchange_type,
            enabled=enabled,
            testnet=bool(testnet) if testnet is not None else None,
            api_key=(
                str(api_key).strip()
                if (api_key is not None and str(api_key).strip())
                else None
            ),
            api_secret=(
                str(secret_key).strip()
                if (secret_key is not None and str(secret_key).strip())
                else None
            ),
            passphrase=(
                str(passphrase).strip()
                if (passphrase is not None and str(passphrase).strip())
                else None
            ),
            clear_api_key=clear_api_key,
            clear_api_secret=clear_api_secret,
            clear_passphrase=clear_passphrase,
        )
        if not ok:
            return jsonify({"error": f"Failed to update exchange '{exchange_type}'"}), 400

    cfg.save()
    return jsonify({"message": "OK"})


@nofx_bp.route("/api/exchanges/<exchange_id>", methods=["DELETE"])
def delete_exchange(exchange_id: str):
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    cfg = get_exchange_config()
    exchange_type = _exchange_type_from_exchange_id(exchange_id)
    ok = cfg.update_exchange(
        exchange_type,
        enabled=False,
        clear_api_key=True,
        clear_api_secret=True,
        clear_passphrase=True,
    )
    if not ok:
        return jsonify({"error": "Not found"}), 404
    cfg.save()
    return jsonify({"message": "Deleted"})


# ---------------------------------------------------------------------------
# Traders
# ---------------------------------------------------------------------------


@nofx_bp.route("/api/my-traders", methods=["GET"])
def my_traders():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    return jsonify([t.to_trader_info() for t in _store.list_traders()])


@nofx_bp.route("/api/traders", methods=["GET", "POST"])
def traders():
    if request.method == "GET":
        return jsonify(
            [t.to_trader_info() for t in _store.list_traders() if t.show_in_competition]
        )

    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err

    data = request.get_json() or {}
    name = str(data.get("name") or "").strip()
    model_id = str(data.get("ai_model_id") or "").strip().lower()
    exchange_id = str(data.get("exchange_id") or "").strip()
    if not name or not model_id or not exchange_id:
        return jsonify({"error": "Missing fields"}), 400

    now = _now_iso()
    trader = TraderState(
        trader_id=uuid.uuid4().hex,
        trader_name=name,
        ai_model=model_id,
        exchange_id=exchange_id,
        is_running=False,
        show_in_competition=bool(data.get("show_in_competition", True)),
        scan_interval_minutes=int(data.get("scan_interval_minutes") or 5),
        initial_balance=float(data.get("initial_balance") or 1000.0),
        is_cross_margin=bool(data.get("is_cross_margin", True)),
        strategy_id=data.get("strategy_id"),
        created_at=now,
        updated_at=now,
    )
    _store.upsert_trader(trader)
    return jsonify(trader.to_trader_info())


@nofx_bp.route("/api/traders/<trader_id>", methods=["PUT", "DELETE"])
def trader_update_delete(trader_id: str):
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err

    if request.method == "DELETE":
        ok = _store.delete_trader(trader_id)
        if not ok:
            return jsonify({"error": "Not found"}), 404
        return jsonify({"message": "Deleted"})

    trader = _store.get_trader(trader_id)
    if trader is None:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json() or {}
    name = str(data.get("name") or "").strip()
    model_id = str(data.get("ai_model_id") or "").strip().lower()
    exchange_id = str(data.get("exchange_id") or "").strip()
    if name:
        trader.trader_name = name
    if model_id:
        trader.ai_model = model_id
    if exchange_id:
        trader.exchange_id = exchange_id
    if "scan_interval_minutes" in data:
        trader.scan_interval_minutes = int(data.get("scan_interval_minutes") or 5)
    if "is_cross_margin" in data:
        trader.is_cross_margin = bool(data.get("is_cross_margin", True))
    if "show_in_competition" in data:
        trader.show_in_competition = bool(data.get("show_in_competition", True))
    if "initial_balance" in data and data.get("initial_balance") is not None:
        trader.initial_balance = float(data.get("initial_balance") or 1000.0)
    if "strategy_id" in data:
        trader.strategy_id = data.get("strategy_id")

    _store.upsert_trader(trader)
    return jsonify(trader.to_trader_info())


@nofx_bp.route("/api/traders/<trader_id>/start", methods=["POST"])
def trader_start(trader_id: str):
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    trader = _store.get_trader(trader_id)
    if trader is None:
        return jsonify({"error": "Not found"}), 404
    trader.is_running = True
    trader.start_time = trader.start_time or _now_iso()
    _store.upsert_trader(trader)
    _ensure_decision_worker()
    return jsonify({"message": "Started"})


@nofx_bp.route("/api/traders/<trader_id>/stop", methods=["POST"])
def trader_stop(trader_id: str):
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    trader = _store.get_trader(trader_id)
    if trader is None:
        return jsonify({"error": "Not found"}), 404
    trader.is_running = False
    _store.upsert_trader(trader)
    return jsonify({"message": "Stopped"})


@nofx_bp.route("/api/traders/<trader_id>/competition", methods=["PUT"])
def trader_competition(trader_id: str):
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    trader = _store.get_trader(trader_id)
    if trader is None:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json() or {}
    trader.show_in_competition = bool(data.get("show_in_competition", True))
    _store.upsert_trader(trader)
    return jsonify({"message": "OK"})


@nofx_bp.route("/api/traders/<trader_id>/prompt", methods=["PUT"])
def trader_prompt(trader_id: str):
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    trader = _store.get_trader(trader_id)
    if trader is None:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json() or {}
    trader.custom_prompt = str(data.get("custom_prompt") or "")
    _store.upsert_trader(trader)
    return jsonify({"message": "OK"})


@nofx_bp.route("/api/traders/<trader_id>/config", methods=["GET"])
def trader_config(trader_id: str):
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    trader = _store.get_trader(trader_id)
    if trader is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(trader.to_config())


@nofx_bp.route("/api/trader/<trader_id>/config", methods=["GET"])
def public_trader_config(trader_id: str):
    trader = _store.get_trader(trader_id)
    if trader is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(trader.to_config())


@nofx_bp.route("/api/traders/<trader_id>/close-position", methods=["POST"])
def trader_close_position(trader_id: str):
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err

    trader = _store.get_trader(trader_id)
    if trader is None:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json() or {}
    symbol = str(data.get("symbol") or "").strip()
    side = str(data.get("side") or "").strip().upper()
    if not symbol or side not in {"LONG", "SHORT"}:
        return jsonify({"error": "Invalid symbol/side"}), 400

    exchange_type = _exchange_type_from_exchange_id(trader.exchange_id)
    cfg = get_exchange_config()
    ex = cfg.get_exchange(exchange_type)
    if not ex or not ex.enabled:
        return jsonify({"error": f"Exchange not enabled: {exchange_type}"}), 400

    if exchange_type == "binance":
        return jsonify(
            {
                "message": (
                    "Binance close-position is not implemented in compat mode. "
                    "Use Bybit/OKX or the native ValueScan executor."
                )
            }
        )

    executor = CCXTExecutor(
        exchange_id=exchange_type,
        api_key=str(ex.api_key or "").strip(),
        api_secret=str(ex.api_secret or "").strip(),
        passphrase=str(ex.passphrase or "").strip(),
        testnet=bool(ex.testnet),
        base_url=ex.base_url,
        default_type="swap",
    )
    # CCXTExecutor.close_position is best-effort and infers direction from current positions.
    result = _run_async(executor.close_position(symbol))
    if not result.get("success"):
        return jsonify({"error": str(result.get("error") or "Failed")}), 500
    return jsonify({"message": "Closed"})


# ---------------------------------------------------------------------------
# Runtime endpoints
# ---------------------------------------------------------------------------


@nofx_bp.route("/api/status", methods=["GET"])
def system_status():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    trader = _store.get_trader(_resolve_trader_id()) or _store.get_trader("default")
    if trader is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(trader.to_system_status())


@nofx_bp.route("/api/positions", methods=["GET"])
def positions():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    trader = _store.get_trader(_resolve_trader_id()) or _store.get_trader("default")
    if trader is None:
        return jsonify([])
    exchange_type = _exchange_type_from_exchange_id(trader.exchange_id)
    ok, pos, _err = _get_positions(exchange_type)
    if not ok:
        return jsonify([])
    return jsonify(pos)


@nofx_bp.route("/api/account", methods=["GET"])
def account():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    trader = _store.get_trader(_resolve_trader_id()) or _store.get_trader("default")
    if trader is None:
        return jsonify({"error": "Not found"}), 404

    exchange_type = _exchange_type_from_exchange_id(trader.exchange_id)
    balance_ok, balance, _balance_err = _get_balance(exchange_type)
    ok, pos, _err = _get_positions(exchange_type)
    unrealized = sum(float(p.get("unrealized_pnl") or 0.0) for p in pos) if ok else 0.0
    if balance_ok and (not ok or abs(unrealized) < 1e-9):
        try:
            unrealized = float(balance.get("total_unrealized_profit") or 0.0)
        except Exception:
            unrealized = 0.0
    position_count = len(pos) if ok else 0

    realized_total = 0.0
    if PERFORMANCE_AVAILABLE:
        try:
            db = get_performance_db()
            trades = db.get_trades(trader_id=trader.trader_id)
            realized_total = sum(t.realized_pnl for t in trades)
        except Exception:
            realized_total = 0.0

    initial_balance = float(trader.initial_balance or 0.0)
    effective_initial_balance = initial_balance
    wallet_balance = 0.0
    available_balance = 0.0

    if balance_ok:
        try:
            wallet_balance = float(balance.get("total_wallet_balance") or 0.0)
        except Exception:
            wallet_balance = 0.0
        try:
            available_balance = float(balance.get("available_balance") or 0.0)
        except Exception:
            available_balance = 0.0
        if available_balance <= 0:
            available_balance = wallet_balance

        cfg = get_exchange_config()
        ex = cfg.get_exchange(exchange_type) if cfg else None
        is_testnet = bool(getattr(ex, "testnet", False)) if ex else False
        if (
            is_testnet
            and wallet_balance > 0
            and (initial_balance <= 0 or abs(initial_balance - 1000.0) < 1e-6)
        ):
            effective_initial_balance = wallet_balance

    if balance_ok and wallet_balance > 0:
        total_equity = wallet_balance + unrealized
        total_pnl = total_equity - effective_initial_balance
    else:
        total_pnl = realized_total + unrealized
        total_equity = initial_balance + total_pnl
        wallet_balance = initial_balance + realized_total
        available_balance = wallet_balance

    total_pnl_pct = (
        (total_pnl / effective_initial_balance) * 100
        if effective_initial_balance
        else 0.0
    )
    return jsonify(
        {
            "total_equity": total_equity,
            "wallet_balance": wallet_balance,
            "unrealized_profit": unrealized,
            "available_balance": available_balance,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "initial_balance": float(effective_initial_balance),
            "daily_pnl": 0.0,
            "position_count": position_count,
            "margin_used": 0.0,
            "margin_used_pct": 0.0,
        }
    )


@nofx_bp.route("/api/decisions", methods=["GET"])
def decisions():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    return jsonify(_store.list_decisions(_resolve_trader_id()))


@nofx_bp.route("/api/decisions/latest", methods=["GET"])
def latest_decisions():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    trader_id = _resolve_trader_id()
    try:
        limit = int(request.args.get("limit", 5))
    except Exception:
        limit = 5
    items = list(reversed(_store.list_decisions(trader_id)))[: max(0, min(50, limit))]
    return jsonify(items)


@nofx_bp.route("/api/statistics", methods=["GET"])
def statistics():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    items = _store.list_decisions(_resolve_trader_id())
    total_cycles = len(items)
    successful_cycles = sum(1 for x in items if bool(x.get("success")))
    failed_cycles = total_cycles - successful_cycles
    return jsonify(
        {
            "total_cycles": total_cycles,
            "successful_cycles": successful_cycles,
            "failed_cycles": failed_cycles,
            "total_open_positions": 0,
            "total_close_positions": 0,
        }
    )


@nofx_bp.route("/api/equity-history", methods=["GET"])
def equity_history():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    if not PERFORMANCE_AVAILABLE:
        return jsonify([])
    trader = _store.get_trader(_resolve_trader_id()) or _store.get_trader("default")
    if trader is None:
        return jsonify([])
    try:
        db = get_performance_db()
        trades = db.get_trades(trader_id=trader.trader_id)
        points = MetricsCalculator.calculate_cumulative_pnl(trades, trader.trader_id)
        out = []
        cycle = 0
        for p in points:
            cycle += 1
            equity = float(trader.initial_balance) + float(p.cumulative_pnl)
            pnl = float(p.cumulative_pnl)
            pnl_pct = (pnl / trader.initial_balance) * 100 if trader.initial_balance else 0.0
            out.append(
                {
                    "timestamp": time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime(p.timestamp / 1000.0)
                    ),
                    "total_equity": equity,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "cycle_number": cycle,
                }
            )
        return jsonify(out)
    except Exception:
        return jsonify([])


@nofx_bp.route("/api/equity-history-batch", methods=["POST"])
def equity_history_batch():
    data = request.get_json() or {}
    trader_ids = data.get("trader_ids") or []
    if not isinstance(trader_ids, list):
        return jsonify({"error": "trader_ids must be a list"}), 400

    result: Dict[str, Any] = {}
    for tid in trader_ids:
        tid_str = str(tid or "").strip()
        if not tid_str:
            continue
        trader = _store.get_trader(tid_str)
        if trader is None or not PERFORMANCE_AVAILABLE:
            result[tid_str] = []
            continue
        try:
            db = get_performance_db()
            trades = db.get_trades(trader_id=trader.trader_id)
            points = MetricsCalculator.calculate_cumulative_pnl(trades, trader.trader_id)
            out = []
            cycle = 0
            for p in points:
                cycle += 1
                equity = float(trader.initial_balance) + float(p.cumulative_pnl)
                pnl = float(p.cumulative_pnl)
                pnl_pct = (pnl / trader.initial_balance) * 100 if trader.initial_balance else 0.0
                out.append(
                    {
                        "timestamp": time.strftime(
                            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(p.timestamp / 1000.0)
                        ),
                        "total_equity": equity,
                        "pnl": pnl,
                        "pnl_pct": pnl_pct,
                        "cycle_number": cycle,
                    }
                )
            result[tid_str] = out
        except Exception:
            result[tid_str] = []
    return jsonify(result)


@nofx_bp.route("/api/top-traders", methods=["GET"])
def top_traders():
    if not PERFORMANCE_AVAILABLE:
        return jsonify([])
    try:
        db = get_performance_db()
        trader_ids = db.get_trader_ids_with_trades()
        rankings = []
        for tid in trader_ids:
            trades = db.get_trades(trader_id=tid)
            summary = MetricsCalculator.calculate_summary(trades)
            rankings.append(
                {
                    "trader_id": tid,
                    "trader_name": tid,
                    "total_pnl": summary.total_pnl,
                    "win_rate": summary.win_rate,
                    "total_trades": summary.total_trades,
                }
            )
        rankings.sort(key=lambda x: float(x.get("total_pnl") or 0.0), reverse=True)
        return jsonify(rankings[:20])
    except Exception:
        return jsonify([])


@nofx_bp.route("/api/competition", methods=["GET"])
def competition():
    traders_list = [t for t in _store.list_traders() if t.show_in_competition]
    rows = []
    for t in traders_list:
        exchange_type = _exchange_type_from_exchange_id(t.exchange_id)
        ok, pos, _err = _get_positions(exchange_type)
        unrealized = sum(float(p.get("unrealized_pnl") or 0.0) for p in pos) if ok else 0.0
        position_count = len(pos) if ok else 0

        realized_total = 0.0
        if PERFORMANCE_AVAILABLE:
            try:
                db = get_performance_db()
                trades = db.get_trades(trader_id=t.trader_id)
                realized_total = sum(tr.realized_pnl for tr in trades)
            except Exception:
                realized_total = 0.0

        total_pnl = realized_total + unrealized
        total_equity = float(t.initial_balance) + total_pnl
        total_pnl_pct = (total_pnl / t.initial_balance) * 100 if t.initial_balance else 0.0

        rows.append(
            {
                "trader_id": t.trader_id,
                "trader_name": t.trader_name,
                "ai_model": t.ai_model,
                "exchange": exchange_type.upper(),
                "total_equity": total_equity,
                "total_pnl": total_pnl,
                "total_pnl_pct": total_pnl_pct,
                "position_count": position_count,
                "margin_used_pct": 0.0,
                "is_running": bool(t.is_running),
            }
        )

    rows.sort(key=lambda x: float(x.get("total_equity") or 0.0), reverse=True)
    return jsonify({"traders": rows, "count": len(rows)})


@nofx_bp.route("/api/server-ip", methods=["GET"])
def server_ip():
    return jsonify({"server_ip": request.host.split(":")[0], "local_ip": "127.0.0.1"})


# ---------------------------------------------------------------------------
# Backtest (stub)
# ---------------------------------------------------------------------------


def _backtest_default_run(run_id: str) -> Dict[str, Any]:
    now = _now_iso()
    return {
        "run_id": run_id,
        "label": "",
        "user_id": "demo",
        "last_error": "",
        "version": 1,
        "state": "idle",
        "created_at": now,
        "updated_at": now,
        "summary": {
            "symbol_count": 0,
            "decision_tf": "5m",
            "processed_bars": 0,
            "progress_pct": 0,
            "equity_last": 0,
            "max_drawdown_pct": 0,
            "liquidated": False,
            "liquidation_note": "",
        },
    }


@nofx_bp.route("/api/backtest/runs", methods=["GET"])
def backtest_runs():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    payload = _store.load()
    backtests = payload.get("backtests") or {}
    if not isinstance(backtests, dict):
        backtests = {}
    items = [v for v in backtests.values() if isinstance(v, dict)]
    return jsonify({"total": len(items), "items": items})


@nofx_bp.route("/api/backtest/start", methods=["POST"])
def backtest_start():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    run_id = uuid.uuid4().hex
    payload = _store.load()
    backtests = payload.setdefault("backtests", {})
    if not isinstance(backtests, dict):
        payload["backtests"] = {}
        backtests = payload["backtests"]
    backtests[run_id] = _backtest_default_run(run_id)
    _store.save(payload)
    return jsonify(backtests[run_id])


@nofx_bp.route("/api/backtest/pause", methods=["POST"])
@nofx_bp.route("/api/backtest/resume", methods=["POST"])
@nofx_bp.route("/api/backtest/stop", methods=["POST"])
def backtest_simple_state():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    data = request.get_json() or {}
    run_id = str(data.get("run_id") or "").strip()
    if not run_id:
        return jsonify({"error": "Missing run_id"}), 400
    payload = _store.load()
    backtests = payload.get("backtests") or {}
    item = backtests.get(run_id) if isinstance(backtests, dict) else None
    if not isinstance(item, dict):
        return jsonify({"error": "Not found"}), 404
    item["updated_at"] = _now_iso()
    _store.save(payload)
    return jsonify(item)


@nofx_bp.route("/api/backtest/label", methods=["POST"])
def backtest_label():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    data = request.get_json() or {}
    run_id = str(data.get("run_id") or "").strip()
    label = str(data.get("label") or "")
    payload = _store.load()
    backtests = payload.get("backtests") or {}
    item = backtests.get(run_id) if isinstance(backtests, dict) else None
    if not isinstance(item, dict):
        return jsonify({"error": "Not found"}), 404
    item["label"] = label
    item["updated_at"] = _now_iso()
    _store.save(payload)
    return jsonify(item)


@nofx_bp.route("/api/backtest/delete", methods=["POST"])
def backtest_delete():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    data = request.get_json() or {}
    run_id = str(data.get("run_id") or "").strip()
    payload = _store.load()
    backtests = payload.get("backtests") or {}
    if isinstance(backtests, dict) and run_id in backtests:
        del backtests[run_id]
        _store.save(payload)
    return jsonify({"message": "OK"})


@nofx_bp.route("/api/backtest/status", methods=["GET"])
def backtest_status():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    run_id = str(request.args.get("run_id") or "").strip()
    if not run_id:
        return jsonify({"error": "Missing run_id"}), 400
    payload = _store.load()
    backtests = payload.get("backtests") or {}
    item = backtests.get(run_id) if isinstance(backtests, dict) else None
    if not isinstance(item, dict):
        return jsonify({"error": "Not found"}), 404
    return jsonify(
        {
            "run_id": run_id,
            "state": item.get("state", "idle"),
            "progress_pct": 0,
            "processed_bars": 0,
            "current_time": int(time.time()),
            "decision_cycle": 0,
            "equity": 0,
            "unrealized_pnl": 0,
            "realized_pnl": 0,
            "note": "",
            "last_error": item.get("last_error", ""),
            "last_updated_iso": _now_iso(),
        }
    )


@nofx_bp.route("/api/backtest/equity", methods=["GET"])
def backtest_equity():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    return jsonify([])


@nofx_bp.route("/api/backtest/trades", methods=["GET"])
def backtest_trades():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    return jsonify([])


@nofx_bp.route("/api/backtest/metrics", methods=["GET"])
def backtest_metrics():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    return jsonify(
        {
            "total_trades": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "total_pnl_pct": 0,
            "max_drawdown_pct": 0,
            "sharpe": 0,
            "profit_factor": 0,
            "avg_trade_pnl": 0,
            "avg_trade_duration": 0,
        }
    )


@nofx_bp.route("/api/backtest/trace", methods=["GET"])
def backtest_trace():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    return jsonify({})


@nofx_bp.route("/api/backtest/decisions", methods=["GET"])
def backtest_decisions():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    return jsonify([])


@nofx_bp.route("/api/backtest/export", methods=["GET"])
def backtest_export():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    content = json.dumps({"message": "Not implemented"}, indent=2).encode("utf-8")
    return Response(
        content,
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=backtest-export.json"},
    )


# ---------------------------------------------------------------------------
# Strategies (minimal CRUD)
# ---------------------------------------------------------------------------


def _default_strategy_config() -> Dict[str, Any]:
    return {
        "coin_source": {
            "source_type": "static",
            "static_coins": ["BTCUSDT", "ETHUSDT"],
            "use_coin_pool": False,
            "coin_pool_limit": 50,
            "use_oi_top": False,
            "oi_top_limit": 50,
        },
        "indicators": {
            "klines": {
                "primary_timeframe": "5m",
                "primary_count": 120,
                "enable_multi_timeframe": False,
            },
            "enable_raw_klines": True,
            "enable_ema": True,
            "enable_macd": True,
            "enable_rsi": True,
            "enable_atr": False,
            "enable_volume": True,
            "enable_oi": False,
            "enable_funding_rate": False,
        },
        "custom_prompt": "",
        "risk_control": {
            "max_positions": 3,
            "position_pct": 10,
            "max_leverage": 5,
            "stop_loss_pct": 2.0,
            "take_profit_pct": 4.0,
        },
        "prompt_sections": {},
    }


def _ensure_default_strategy(payload: Dict[str, Any]) -> None:
    strategies = payload.setdefault("strategies", {})
    if not isinstance(strategies, dict):
        payload["strategies"] = {}
        strategies = payload["strategies"]
    if "default" in strategies:
        return
    now = _now_iso()
    strategies["default"] = {
        "id": "default",
        "user_id": "demo",
        "name": "Default Strategy",
        "description": "Built-in default strategy",
        "is_active": True,
        "is_default": True,
        "config": _default_strategy_config(),
        "created_at": now,
        "updated_at": now,
    }


@nofx_bp.route("/api/strategies", methods=["GET", "POST"])
def strategies():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    payload = _store.load()
    _ensure_default_strategy(payload)

    if request.method == "GET":
        strategies_map = payload.get("strategies") or {}
        items = [v for v in strategies_map.values() if isinstance(v, dict)]
        return jsonify({"strategies": items})

    data = request.get_json() or {}
    name = str(data.get("name") or "").strip() or "Untitled"
    desc = str(data.get("description") or "")
    config = data.get("config") if isinstance(data.get("config"), dict) else _default_strategy_config()
    sid = uuid.uuid4().hex
    now = _now_iso()
    payload["strategies"][sid] = {
        "id": sid,
        "user_id": "demo",
        "name": name,
        "description": desc,
        "is_active": False,
        "is_default": False,
        "config": config,
        "created_at": now,
        "updated_at": now,
    }
    _store.save(payload)
    return jsonify(payload["strategies"][sid])


@nofx_bp.route("/api/strategies/default-config", methods=["GET"])
def strategies_default_config():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    return jsonify(_default_strategy_config())


@nofx_bp.route("/api/strategies/active", methods=["GET"])
def strategies_active():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    payload = _store.load()
    _ensure_default_strategy(payload)
    strategies_map = payload.get("strategies") or {}
    for v in strategies_map.values():
        if isinstance(v, dict) and v.get("is_active"):
            return jsonify(v)
    return jsonify(strategies_map.get("default"))


@nofx_bp.route("/api/strategies/<strategy_id>", methods=["GET", "PUT", "DELETE"])
def strategy_item(strategy_id: str):
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    payload = _store.load()
    _ensure_default_strategy(payload)
    strategies_map = payload.get("strategies") or {}
    item = strategies_map.get(strategy_id) if isinstance(strategies_map, dict) else None
    if not isinstance(item, dict):
        return jsonify({"error": "Not found"}), 404

    if request.method == "GET":
        return jsonify(item)

    if request.method == "DELETE":
        if item.get("is_default"):
            return jsonify({"error": "Cannot delete default strategy"}), 400
        del strategies_map[strategy_id]
        _store.save(payload)
        return jsonify({"message": "Deleted"})

    data = request.get_json() or {}
    if "name" in data:
        item["name"] = str(data.get("name") or item.get("name") or "")
    if "description" in data:
        item["description"] = str(data.get("description") or item.get("description") or "")
    if "config" in data and isinstance(data.get("config"), dict):
        item["config"] = data.get("config")
    item["updated_at"] = _now_iso()
    _store.save(payload)
    return jsonify(item)


@nofx_bp.route("/api/strategies/<strategy_id>/activate", methods=["POST"])
def strategy_activate(strategy_id: str):
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    payload = _store.load()
    _ensure_default_strategy(payload)
    strategies_map = payload.get("strategies") or {}
    if not isinstance(strategies_map, dict) or strategy_id not in strategies_map:
        return jsonify({"error": "Not found"}), 404
    for v in strategies_map.values():
        if isinstance(v, dict):
            v["is_active"] = False
    strategies_map[strategy_id]["is_active"] = True
    strategies_map[strategy_id]["updated_at"] = _now_iso()
    _store.save(payload)
    return jsonify(strategies_map[strategy_id])


@nofx_bp.route("/api/strategies/<strategy_id>/duplicate", methods=["POST"])
def strategy_duplicate(strategy_id: str):
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    payload = _store.load()
    _ensure_default_strategy(payload)
    strategies_map = payload.get("strategies") or {}
    item = strategies_map.get(strategy_id) if isinstance(strategies_map, dict) else None
    if not isinstance(item, dict):
        return jsonify({"error": "Not found"}), 404
    sid = uuid.uuid4().hex
    now = _now_iso()
    strategies_map[sid] = {
        **item,
        "id": sid,
        "name": f"{item.get('name','Strategy')} (Copy)",
        "is_active": False,
        "is_default": False,
        "created_at": now,
        "updated_at": now,
    }
    _store.save(payload)
    return jsonify(strategies_map[sid])


# ---------------------------------------------------------------------------
# Debates (stub + SSE)
# ---------------------------------------------------------------------------


@nofx_bp.route("/api/debates", methods=["GET", "POST"])
def debates():
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err

    payload = _store.load()
    debates_map = payload.setdefault("debates", {})
    if not isinstance(debates_map, dict):
        payload["debates"] = {}
        debates_map = payload["debates"]

    if request.method == "GET":
        return jsonify([v for v in debates_map.values() if isinstance(v, dict)])

    data = request.get_json() or {}
    did = uuid.uuid4().hex
    now = _now_iso()
    debates_map[did] = {
        "id": did,
        "user_id": "demo",
        "name": str(data.get("name") or "Debate"),
        "strategy_id": str(data.get("strategy_id") or "default"),
        "status": "pending",
        "symbol": str(data.get("symbol") or "BTCUSDT"),
        "interval_minutes": int(data.get("interval_minutes") or 5),
        "prompt_variant": str(data.get("prompt_variant") or "balanced"),
        "trader_id": data.get("trader_id"),
        "max_rounds": int(data.get("max_rounds") or 3),
        "current_round": 0,
        "final_decision": None,
        "final_decisions": None,
        "auto_execute": bool(data.get("auto_execute", False)),
        "created_at": now,
        "updated_at": now,
        "participants": [],
        "messages": [],
        "votes": [],
    }
    _store.save(payload)
    return jsonify(debates_map[did])


@nofx_bp.route("/api/debates/personalities", methods=["GET"])
def debate_personalities():
    return jsonify(
        [
            {
                "id": "balanced",
                "name": "Balanced",
                "emoji": "⚖️",
                "color": "#F0B90B",
                "description": "Balanced analysis",
            },
            {
                "id": "aggressive",
                "name": "Aggressive",
                "emoji": "🔥",
                "color": "#F6465D",
                "description": "Higher risk",
            },
            {
                "id": "conservative",
                "name": "Conservative",
                "emoji": "🛡️",
                "color": "#0ECB81",
                "description": "Lower risk",
            },
        ]
    )


@nofx_bp.route("/api/debates/<debate_id>", methods=["GET", "DELETE"])
def debate_item(debate_id: str):
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    payload = _store.load()
    debates_map = payload.get("debates") or {}
    item = debates_map.get(debate_id) if isinstance(debates_map, dict) else None
    if not isinstance(item, dict):
        return jsonify({"error": "Not found"}), 404
    if request.method == "DELETE":
        del debates_map[debate_id]
        _store.save(payload)
        return jsonify({"message": "Deleted"})
    return jsonify(item)


@nofx_bp.route("/api/debates/<debate_id>/start", methods=["POST"])
@nofx_bp.route("/api/debates/<debate_id>/cancel", methods=["POST"])
@nofx_bp.route("/api/debates/<debate_id>/execute", methods=["POST"])
def debate_action(debate_id: str):
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    payload = _store.load()
    debates_map = payload.get("debates") or {}
    item = debates_map.get(debate_id) if isinstance(debates_map, dict) else None
    if not isinstance(item, dict):
        return jsonify({"error": "Not found"}), 404
    item["updated_at"] = _now_iso()
    _store.save(payload)
    return jsonify(item)


@nofx_bp.route("/api/debates/<debate_id>/messages", methods=["GET"])
def debate_messages(debate_id: str):
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    payload = _store.load()
    debates_map = payload.get("debates") or {}
    item = debates_map.get(debate_id) if isinstance(debates_map, dict) else None
    if not isinstance(item, dict):
        return jsonify({"error": "Not found"}), 404
    return jsonify(item.get("messages") or [])


@nofx_bp.route("/api/debates/<debate_id>/votes", methods=["GET"])
def debate_votes(debate_id: str):
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err
    payload = _store.load()
    debates_map = payload.get("debates") or {}
    item = debates_map.get(debate_id) if isinstance(debates_map, dict) else None
    if not isinstance(item, dict):
        return jsonify({"error": "Not found"}), 404
    return jsonify(item.get("votes") or [])


@nofx_bp.route("/api/debates/<debate_id>/stream", methods=["GET"])
def debate_stream(debate_id: str):
    token = (request.args.get("token") or "").strip()
    if not token:
        return jsonify({"error": "Unauthorized"}), 401

    def gen():
        yield "event: ping\ndata: {}\n\n"
        while True:
            time.sleep(10)
            yield "event: ping\ndata: {}\n\n"

    return Response(gen(), mimetype="text/event-stream")

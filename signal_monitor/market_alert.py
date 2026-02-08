#!/usr/bin/env python3
"""
市场异动警报模块
- 衍生品信号检测（资金费率、持仓量）
- 情绪极值检测（恐惧贪婪指数）
- 组合信号识别（接针/逃顶模型）
- 美股开盘信号
"""

from __future__ import annotations

import json
import os
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from logger import logger
except Exception:
    import logging
    logger = logging.getLogger(__name__)

try:
    from telegram import send_telegram_message
except Exception:
    send_telegram_message = None

try:
    from ai_signal_analysis import analyze_signal
except Exception:
    analyze_signal = None

try:
    from fundamentals_sources import build_macro_brief
except Exception:
    def build_macro_brief(max_items: int = 2) -> List[str]:
        return []

# 时区
BEIJING_TZ = timezone(timedelta(hours=8))
NY_TZ = timezone(timedelta(hours=-5))  # 美东标准时间

# 配置文件路径
CONFIG_PATH = Path(__file__).parent / "market_alert_config.json"

# 全局状态
_RUNNING = False
_THREADS: List[threading.Thread] = []
_SESSION: Optional[requests.Session] = None


@dataclass
class MarketSnapshot:
    """市场快照数据"""
    symbol: str
    price: float
    price_change_pct: float = 0.0
    funding_rate: float = 0.0
    open_interest: float = 0.0
    oi_change_pct: float = 0.0
    fear_greed_index: int = 50
    timestamp: float = field(default_factory=time.time)


@dataclass
class AnomalySignal:
    """异动信号"""
    signal_type: str
    severity: str  # "warning", "alert", "critical"
    direction: str  # "bullish", "bearish", "neutral"
    description: str
    triggers: List[str] = field(default_factory=list)


class MarketDataCache:
    """市场数据缓存，用于计算变化率"""

    def __init__(self, window_minutes: int = 15):
        self._window_sec = window_minutes * 60
        self._price_history: Dict[str, List[Tuple[float, float]]] = {}
        self._oi_history: Dict[str, List[Tuple[float, float]]] = {}
        self._lock = threading.Lock()

    def add_snapshot(self, symbol: str, price: float, oi: float) -> None:
        now = time.time()
        with self._lock:
            # 价格历史
            if symbol not in self._price_history:
                self._price_history[symbol] = []
            self._price_history[symbol].append((now, price))
            self._price_history[symbol] = [
                (t, p) for t, p in self._price_history[symbol]
                if now - t <= self._window_sec
            ]
            # OI历史
            if symbol not in self._oi_history:
                self._oi_history[symbol] = []
            self._oi_history[symbol].append((now, oi))
            self._oi_history[symbol] = [
                (t, o) for t, o in self._oi_history[symbol]
                if now - t <= self._window_sec
            ]

    def get_price_change_pct(self, symbol: str) -> float:
        with self._lock:
            history = self._price_history.get(symbol, [])
            if len(history) < 2:
                return 0.0
            old_price = history[0][1]
            new_price = history[-1][1]
            if old_price == 0:
                return 0.0
            return ((new_price - old_price) / old_price) * 100

    def get_oi_change_pct(self, symbol: str) -> float:
        with self._lock:
            history = self._oi_history.get(symbol, [])
            if len(history) < 2:
                return 0.0
            old_oi = history[0][1]
            new_oi = history[-1][1]
            if old_oi == 0:
                return 0.0
            return ((new_oi - old_oi) / old_oi) * 100


class AlertDeduplicator:
    """警报去重器"""

    def __init__(self, cooldown_seconds: int = 300):
        self._cooldown = cooldown_seconds
        self._sent: Dict[str, float] = {}
        self._lock = threading.Lock()

    def should_send(self, alert_key: str) -> bool:
        now = time.time()
        with self._lock:
            last_sent = self._sent.get(alert_key, 0)
            return (now - last_sent) >= self._cooldown

    def mark_sent(self, alert_key: str) -> None:
        with self._lock:
            self._sent[alert_key] = time.time()


# 全局实例
_CACHE = MarketDataCache()
_DEDUP = AlertDeduplicator()


def load_config() -> Dict[str, Any]:
    """加载配置"""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[MarketAlert] 加载配置失败: {e}")
    return {"enabled": False}


def _get_session() -> requests.Session:
    global _SESSION
    if _SESSION is not None:
        return _SESSION
    session = requests.Session()
    proxy = os.getenv("NOFX_PROXY") or os.getenv("HTTP_PROXY")
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}
    try:
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
        )
    except TypeError:
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            method_whitelist=["GET"],
        )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    _SESSION = session
    return session


# ==================== 数据获取 ====================

def fetch_binance_ticker(symbol: str) -> Optional[Dict]:
    """获取Binance现货行情"""
    try:
        session = _get_session()
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT"
        resp = session.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.debug(f"[MarketAlert] Binance ticker失败: {e}")
    return None


def fetch_binance_funding_rate(symbol: str) -> Optional[float]:
    """获取Binance合约资金费率"""
    try:
        session = _get_session()
        url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}USDT&limit=1"
        resp = session.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return float(data[0].get("fundingRate", 0))
    except Exception as e:
        logger.debug(f"[MarketAlert] Binance funding rate失败: {e}")
    return None


def fetch_binance_open_interest(symbol: str) -> Optional[float]:
    """获取Binance合约持仓量"""
    try:
        session = _get_session()
        url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}USDT"
        resp = session.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return float(data.get("openInterest", 0))
    except Exception as e:
        logger.debug(f"[MarketAlert] Binance OI失败: {e}")
    return None


def fetch_fear_greed_index() -> Optional[int]:
    """获取恐惧贪婪指数"""
    try:
        session = _get_session()
        url = "https://api.alternative.me/fng/?limit=1"
        resp = session.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("data"):
                return int(data["data"][0].get("value", 50))
    except Exception as e:
        logger.debug(f"[MarketAlert] Fear&Greed失败: {e}")
    return None


def fetch_us_market_data(symbol: str = "SPY") -> Optional[Dict]:
    """获取美股数据 (多数据源)"""
    # 尝试 Finnhub (免费API)
    data = _fetch_finnhub(symbol)
    if data:
        return data

    # 尝试 Yahoo Finance
    data = _fetch_yahoo_finance(symbol)
    if data:
        return data

    return None


def fetch_us_market_batch(symbols: List[str]) -> Dict[str, Dict]:
    """批量获取美股数据"""
    results = {}
    for symbol in symbols:
        data = fetch_us_market_data(symbol)
        if data:
            results[symbol] = data
        time.sleep(0.2)  # 避免限流
    return results


def fetch_vix(symbol: str = "^VIX") -> Optional[float]:
    """获取VIX恐慌指数"""
    # 尝试 Yahoo Finance
    data = _fetch_yahoo_finance(symbol)
    if data:
        return data.get("current")
    return None


def analyze_us_market_impact(
    market_data: Dict[str, Dict],
    vix: Optional[float],
    categories: Optional[Dict[str, List[str]]] = None,
) -> Dict:
    """分析美股数据，构建AI分析payload"""
    # 分类汇总
    categories = categories or {
        "indices": ["SPY", "QQQ", "DIA", "IWM"],
        "tech": ["NVDA", "AAPL", "MSFT", "GOOGL", "META", "AMZN", "TSLA"],
        "crypto_stocks": ["COIN", "MSTR", "MARA", "RIOT"],
        "macro": ["GLD", "TLT"],
    }

    summary = {}
    for cat, symbols in categories.items():
        cat_data = []
        for sym in symbols:
            if sym in market_data:
                cat_data.append({
                    "symbol": sym,
                    "change_pct": market_data[sym].get("change_pct", 0),
                })
        if cat_data:
            avg_change = sum(d["change_pct"] for d in cat_data) / len(cat_data)
            summary[cat] = {
                "stocks": cat_data,
                "avg_change": round(avg_change, 2),
            }

    return {
        "us_market_summary": summary,
        "vix": vix,
        "timestamp": datetime.now(NY_TZ).isoformat(),
    }


def _fetch_finnhub(symbol: str) -> Optional[Dict]:
    """Finnhub 免费 API"""
    try:
        session = _get_session()
        # Finnhub 免费 API key
        api_key = os.getenv("NOFX_FINNHUB_API_KEY") or "ctdj3t1r01qhb4a7lmagctdj3t1r01qhb4a7lmb0"
        if not api_key:
            return None
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}"
        resp = session.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            current = data.get("c")  # current price
            previous_close = data.get("pc")  # previous close
            change_pct = data.get("dp")  # percent change

            if current and previous_close:
                return {
                    "symbol": symbol,
                    "current": current,
                    "previous_close": previous_close,
                    "change_pct": change_pct if change_pct else ((current - previous_close) / previous_close) * 100,
                    "source": "finnhub",
                }
    except Exception as e:
        logger.debug(f"[MarketAlert] Finnhub failed for {symbol}: {e}")
    return None


def _fetch_yahoo_finance(symbol: str) -> Optional[Dict]:
    """Yahoo Finance API"""
    try:
        session = _get_session()
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m&range=1d"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }
        resp = session.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            result = data.get("chart", {}).get("result", [])
            if result:
                meta = result[0].get("meta", {})
                current = meta.get("regularMarketPrice")
                previous_close = meta.get("previousClose") or meta.get("chartPreviousClose")

                if current and previous_close:
                    return {
                        "symbol": symbol,
                        "current": current,
                        "previous_close": previous_close,
                        "change_pct": ((current - previous_close) / previous_close) * 100,
                        "source": "yahoo",
                    }
    except Exception as e:
        logger.debug(f"[MarketAlert] Yahoo Finance failed for {symbol}: {e}")
    return None


def _get_metal_symbol_map(config: Dict[str, Any]) -> Dict[str, str]:
    metals_cfg = config.get("metals", {})
    symbol_map = metals_cfg.get("yahoo_symbol_map", {})
    return symbol_map if isinstance(symbol_map, dict) else {}


def _is_metal_symbol(symbol: str, config: Dict[str, Any]) -> bool:
    metals_cfg = config.get("metals", {})
    if not metals_cfg.get("enabled", False):
        return False
    symbols = metals_cfg.get("symbols", [])
    return symbol in symbols


def fetch_market_snapshot(symbol: str, config: Dict[str, Any]) -> Optional[MarketSnapshot]:
    """获取完整市场快照"""
    if _is_metal_symbol(symbol, config):
        symbol_map = _get_metal_symbol_map(config)
        yahoo_symbol = symbol_map.get(symbol, symbol)
        data = _fetch_yahoo_finance(yahoo_symbol)
        if not data:
            return None
        price = float(data.get("current", 0))
        if price <= 0:
            return None
        funding_rate = 0.0
        oi = 0.0
        fgi = 50
    else:
        ticker = fetch_binance_ticker(symbol)
        if not ticker:
            return None
        price = float(ticker.get("lastPrice", 0))
        funding_rate = fetch_binance_funding_rate(symbol) or 0.0
        oi = fetch_binance_open_interest(symbol) or 0.0
        fgi = fetch_fear_greed_index() or 50

    # 更新缓存并计算变化率
    _CACHE.add_snapshot(symbol, price, oi)
    price_change = _CACHE.get_price_change_pct(symbol)
    oi_change = _CACHE.get_oi_change_pct(symbol)

    return MarketSnapshot(
        symbol=symbol,
        price=price,
        price_change_pct=price_change,
        funding_rate=funding_rate,
        open_interest=oi,
        oi_change_pct=oi_change,
        fear_greed_index=fgi,
    )


def _get_price_change_threshold(config: Dict[str, Any]) -> float:
    price_cfg = config.get("price", {})
    try:
        return float(price_cfg.get("short_term_change_pct", 3.0))
    except Exception:
        return 3.0


def _get_oi_change_threshold(config: Dict[str, Any]) -> float:
    deriv_cfg = config.get("derivatives", {})
    try:
        return float(deriv_cfg.get("oi_change_threshold_pct", 5.0))
    except Exception:
        return 5.0


def _get_volatility_spike_threshold(config: Dict[str, Any]) -> float:
    base = _get_price_change_threshold(config)
    combo_cfg = config.get("combo_signals", {})
    try:
        multiplier = float(combo_cfg.get("needle_catch_volatility_multiplier", 1.5))
    except Exception:
        multiplier = 1.5
    if multiplier < 1:
        multiplier = 1.0
    return max(base, base * multiplier)




def _get_metals_volatility_threshold(config: Dict[str, Any]) -> float:
    metals_cfg = config.get("metals", {})
    try:
        return float(metals_cfg.get("volatility_threshold_pct", 1.5))
    except Exception:
        return 1.5


def _sentiment_price_gate(snapshot: MarketSnapshot, config: Dict[str, Any]) -> bool:
    threshold = _get_price_change_threshold(config)
    min_move = max(1.5, threshold * 0.5)
    return abs(snapshot.price_change_pct) >= min_move


# ==================== 信号检测 ====================

def detect_derivatives_signals(snapshot: MarketSnapshot, config: Dict) -> List[AnomalySignal]:
    """检测衍生品异动信号"""
    signals = []
    deriv_cfg = config.get("derivatives", {})

    fr = snapshot.funding_rate
    fr_neg = deriv_cfg.get("funding_rate_extreme_negative", -0.01)
    fr_pos = deriv_cfg.get("funding_rate_extreme_positive", 0.03)
    price_threshold = _get_price_change_threshold(config)
    oi_threshold = _get_oi_change_threshold(config)

    price_change = snapshot.price_change_pct
    oi_change = snapshot.oi_change_pct

    # 轧空预警: 价格跌 + 费率极负
    if price_change < -price_threshold and fr < fr_neg:
        signals.append(AnomalySignal(
            signal_type="short_squeeze_warning",
            severity="alert",
            direction="bullish",
            description="轧空预警: 做空拥挤，可能反转上涨",
            triggers=[
                f"价格变动: {price_change:.2f}%",
                f"资金费率: {fr*100:.4f}% (极度负值)",
            ]
        ))

    # 多头过热: 价格涨 + 费率极高
    if price_change > price_threshold and fr > fr_pos:
        signals.append(AnomalySignal(
            signal_type="long_crowded",
            severity="alert",
            direction="bearish",
            description="多头过热: FOMO过度，主力可能收割",
            triggers=[
                f"价格变动: +{price_change:.2f}%",
                f"资金费率: {fr*100:.4f}% (极高)",
            ]
        ))

    # 上涨无力: 价格涨 + OI跌
    if price_change > price_threshold and oi_change < -oi_threshold:
        signals.append(AnomalySignal(
            signal_type="weak_rally",
            severity="warning",
            direction="bearish",
            description="上涨无力: 空头平仓推动，非新资金入场",
            triggers=[
                f"价格变动: +{price_change:.2f}%",
                f"持仓量变化: {oi_change:.2f}%",
            ]
        ))

    # 强空信号: 价格跌 + OI涨
    if price_change < -price_threshold and oi_change > oi_threshold:
        signals.append(AnomalySignal(
            signal_type="strong_short",
            severity="alert",
            direction="bearish",
            description="强空信号: 主力开空打压，趋势可能延续",
            triggers=[
                f"价格变动: {price_change:.2f}%",
                f"持仓量变化: +{oi_change:.2f}%",
            ]
        ))

    return signals


def detect_sentiment_signals(snapshot: MarketSnapshot, config: Dict) -> List[AnomalySignal]:
    """检测情绪极值信号"""
    signals = []
    sent_cfg = config.get("sentiment", {})

    fgi = snapshot.fear_greed_index
    fear_extreme = sent_cfg.get("fear_extreme", 20)
    greed_extreme = sent_cfg.get("greed_extreme", 80)

    if not _sentiment_price_gate(snapshot, config):
        return signals

    if fgi <= fear_extreme:
        signals.append(AnomalySignal(
            signal_type="extreme_fear",
            severity="warning",
            direction="bullish",
            description="极度恐惧: 市场恐慌，潜在底部",
            triggers=[f"恐惧贪婪指数: {fgi}"]
        ))

    if fgi >= greed_extreme:
        signals.append(AnomalySignal(
            signal_type="extreme_greed",
            severity="warning",
            direction="bearish",
            description="极度贪婪: 市场狂热，潜在顶部",
            triggers=[f"恐惧贪婪指数: {fgi}"]
        ))

    return signals


def detect_combo_signals(snapshot: MarketSnapshot, signals: List[AnomalySignal], config: Dict) -> List[AnomalySignal]:
    """检测组合信号（接针/逃顶模型）"""
    combo_signals = []
    combo_cfg = config.get("combo_signals", {})

    price_change = snapshot.price_change_pct
    fr = snapshot.funding_rate
    fgi = snapshot.fear_greed_index
    oi_change = snapshot.oi_change_pct
    price_threshold = _get_price_change_threshold(config)
    oi_threshold = _get_oi_change_threshold(config)
    volatility_threshold = _get_volatility_spike_threshold(config)
    is_metal = _is_metal_symbol(snapshot.symbol, config)
    if is_metal:
        volatility_threshold = _get_metals_volatility_threshold(config)
    deriv_cfg = config.get("derivatives", {})
    fr_neg = float(deriv_cfg.get("funding_rate_extreme_negative", -0.01))
    fr_pos = float(deriv_cfg.get("funding_rate_extreme_positive", 0.03))
    fr_extreme = max(abs(fr_neg), abs(fr_pos))

    # 接针机会模型: 波动显著放大
    needle_enabled = combo_cfg.get("needle_catch")
    if needle_enabled is None:
        needle_enabled = combo_cfg.get("bottom_fishing", True)
    if needle_enabled:
        if abs(price_change) >= volatility_threshold:
            vol_ratio = abs(price_change) / max(volatility_threshold, 0.1)
            has_oi_spike = (not is_metal) and abs(oi_change) >= oi_threshold
            has_funding_extreme = (not is_metal) and abs(fr) >= fr_extreme
            direction = "bullish" if price_change > 0 else "bearish" if price_change < 0 else "neutral"
            severity = "critical" if (vol_ratio >= 1.8 or abs(oi_change) >= oi_threshold * 1.5 or has_funding_extreme) else "alert"
            price_label = "上涨" if price_change > 0 else "下跌" if price_change < 0 else "持平"
            triggers = [
                f"波动幅度: {price_change:+.2f}% (阈值 {volatility_threshold:.2f}%)",
                f"涨跌方向: {price_label} {price_change:+.2f}%",
            ]
            if has_oi_spike:
                triggers.append(f"持仓变化: {oi_change:+.2f}% (阈值 {oi_threshold:.2f}%)")
            if has_funding_extreme:
                triggers.append(f"资金费率极端: {fr*100:.4f}%")
            if not has_oi_spike and not has_funding_extreme:
                if is_metal:
                    triggers.append("数据源: 现货/期货/宏观")
                else:
                    triggers.append(f"资金费率: {fr*100:.4f}%")
                    triggers.append(f"持仓变化: {oi_change:+.2f}%")

            combo_signals.append(AnomalySignal(
                signal_type="needle_catch",
                severity=severity,
                direction=direction,
                description="接针机会: 波动显著放大",
                triggers=triggers,
            ))
    if combo_cfg.get("top_escape", True):
        if price_change > price_threshold and oi_change < -oi_threshold and fgi > 75:
            combo_signals.append(AnomalySignal(
                signal_type="top_escape",
                severity="critical",
                direction="bearish",
                description="🔥 逃顶信号: 多条件共振，止盈/做空机会",
                triggers=[
                    f"价格上涨: +{price_change:.2f}%",
                    f"持仓量下降: {oi_change:.2f}% (主力平多)",
                    f"贪婪指数: {fgi}",
                ]
            ))

    return combo_signals


def detect_all_signals(snapshot: MarketSnapshot, config: Dict) -> List[AnomalySignal]:
    """检测所有信号"""
    signals = []
    signals.extend(detect_derivatives_signals(snapshot, config))
    signals.extend(detect_sentiment_signals(snapshot, config))
    signals.extend(detect_combo_signals(snapshot, signals, config))
    return signals


# ==================== 美股开盘检测 ====================

def is_us_market_open_window(check_after_open_minutes: int = 5) -> bool:
    """判断是否在美股开盘分钟窗口内"""
    now = datetime.now(NY_TZ)
    # 美股开盘时间 9:30 AM ET
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_open_end = market_open + timedelta(minutes=max(1, check_after_open_minutes))

    # 检查是否是交易日（周一到周五）
    if now.weekday() >= 5:
        return False

    return market_open <= now <= market_open_end


_US_MARKET_ALERTED_TODAY = False


def check_us_market_open(config: Dict) -> Optional[str]:
    """检查美股开盘信号，包含AI分析"""
    global _US_MARKET_ALERTED_TODAY

    us_cfg = config.get("us_market", {})
    if not us_cfg.get("enabled", False):
        return None
    check_after_open_minutes = int(us_cfg.get("check_after_open_minutes", 5))

    # 检查是否已经发送过今日警报
    now = datetime.now(NY_TZ)
    if now.hour == 0 and now.minute < 5:
        _US_MARKET_ALERTED_TODAY = False

    if _US_MARKET_ALERTED_TODAY:
        return None

    if not is_us_market_open_window(check_after_open_minutes):
        return None

    # 加密市场快照
    crypto_symbols = config.get("symbols", [])
    crypto_symbols = [s for s in crypto_symbols if s and not _is_metal_symbol(s, config)]
    # 去重并限制长度，避免消息过长
    seen = set()
    crypto_symbols = [s for s in crypto_symbols if not (s in seen or seen.add(s))][:6]
    crypto_rows: List[Tuple[str, float, float]] = []
    for sym in crypto_symbols:
        ticker = fetch_binance_ticker(sym)
        if not ticker:
            continue
        try:
            price = float(ticker.get("lastPrice", 0) or 0)
            change_pct = float(ticker.get("priceChangePercent", 0) or 0)
        except Exception:
            continue
        if price > 0:
            crypto_rows.append((sym, price, change_pct))

    # 获取分类配置
    categories = us_cfg.get("categories", {
        "indices": ["SPY", "QQQ"],
        "tech": [],
        "crypto_stocks": [],
        "macro": [],
    })

    # 批量获取所有标的数据
    all_symbols = []
    for syms in categories.values():
        all_symbols.extend(syms)

    market_data = fetch_us_market_batch(all_symbols)
    if not market_data:
        return None

    # 获取VIX
    vix_symbol = us_cfg.get("vix_symbol", "^VIX")
    vix = fetch_vix(vix_symbol)

    # 构建消息
    lines = []

    # 判断整体方向（基于指数）
    indices = categories.get("indices", [])
    idx_changes = [market_data[s]["change_pct"] for s in indices if s in market_data]
    avg_change = sum(idx_changes) / len(idx_changes) if idx_changes else 0

    if avg_change > 0.5:
        emoji, direction = "📈", "上涨"
    elif avg_change < -0.5:
        emoji, direction = "📉", "下跌"
    else:
        emoji, direction = "➡️", "平开"

    lines.append(f"{emoji} <b>美股今日开盘{direction}</b>")
    lines.append("")

    if crypto_rows:
        lines.append("<b>🪙 加密市场</b>")
        for sym, price, chg in crypto_rows:
            sign = "+" if chg > 0 else ""
            lines.append(f"  {sym}: {sign}{chg:.2f}%  ${price:,.2f}")
        lines.append("")

    # 分板块展示
    cat_names = {
        "indices": "📊 大盘指数",
        "tech": "💻 科技龙头",
        "crypto_stocks": "🪙 加密概念股",
        "macro": "🏦 宏观指标",
    }

    for cat_key, cat_label in cat_names.items():
        syms = categories.get(cat_key, [])
        cat_data = [(s, market_data[s]["change_pct"]) for s in syms if s in market_data]
        if cat_data:
            lines.append(f"<b>{cat_label}</b>")
            for sym, chg in cat_data:
                sign = "+" if chg > 0 else ""
                lines.append(f"  {sym}: {sign}{chg:.2f}%")
            lines.append("")

    # VIX
    if vix:
        vix_label = "🔴 高波动" if vix > 20 else "🟢 低波动" if vix < 15 else "🟡 中等"
        lines.append(f"<b>📉 VIX恐慌指数:</b> {vix:.1f} ({vix_label})")
        lines.append("")

    lines.append(f"⏰ {now.strftime('%Y-%m-%d %H:%M')} ET")

    message = "\n".join(lines)

    # AI分析
    if us_cfg.get("ai_analysis_enabled", False) and analyze_signal:
        try:
            impact_data = analyze_us_market_impact(market_data, vix, categories=categories)
            ai_result = analyze_signal("US_MARKET", signal_payload={"us_market": impact_data})
            if ai_result and ai_result.get("analysis"):
                analysis = ai_result["analysis"]
                message += f"\n\n<b>🤖 AI分析 (对加密市场影响):</b>\n{analysis}"
        except Exception as e:
            logger.warning(f"[MarketAlert] AI分析失败: {e}")

    _US_MARKET_ALERTED_TODAY = True
    return message


# ==================== 警报格式化与发送 ====================

def format_alert_message(symbol: str, snapshot: MarketSnapshot, signal: AnomalySignal) -> str:
    """格式化警报消息"""
    severity_emoji = {"warning": "⚠️", "alert": "🚨", "critical": "🔥"}.get(signal.severity, "📢")
    direction_emoji = {"bullish": "↑", "bearish": "↓", "neutral": "→"}.get(signal.direction, "")

    lines = [
        f"{severity_emoji} <b>市场异动警报: ${symbol}</b>",
        "",
        f"<b>信号类型:</b> {signal.description}",
        f"<b>方向:</b> {signal.direction.upper()} {direction_emoji}",
        "",
        "<b>触发条件:</b>",
    ]

    for trigger in signal.triggers:
        lines.append(f"• {trigger}")

    lines.extend([
        "",
        "<b>市场快照:</b>",
        f"最新价格: ${snapshot.price:,.2f}",
        f"资金费率: {snapshot.funding_rate*100:.4f}%",
        f"恐惧贪婪指数: {snapshot.fear_greed_index}",
        "",
    ])

    macro_lines = build_macro_brief(max_items=2)
    if macro_lines:
        lines.append("<b>基本面:</b>")
        for item in macro_lines:
            safe_item = str(item).replace("<", "").replace(">", "")
            lines.append(f"• {safe_item}")
        lines.append("")

    lines.append(f"🕒 {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)")

    return "\n".join(lines)


def send_alert(message: str, symbol: Optional[str] = None, anomaly_signal: Optional[AnomalySignal] = None) -> bool:
    """发送警报到Telegram，可选附带AI分析"""
    if send_telegram_message is None:
        logger.warning("[MarketAlert] Telegram模块未加载")
        return False

    try:
        # 如果有异动信号且AI分析可用，进行AI分析
        if anomaly_signal and analyze_signal and symbol:
            signal_payload = {
                "anomaly": {
                    "type": anomaly_signal.signal_type,
                    "direction": anomaly_signal.direction,
                    "severity": anomaly_signal.severity,
                    "description": anomaly_signal.description,
                    "triggers": anomaly_signal.triggers,
                }
            }
            try:
                ai_result = analyze_signal(symbol, signal_payload=signal_payload)
                if ai_result and ai_result.get("analysis"):
                    analysis = ai_result["analysis"]
                    direction = ai_result.get("direction", "none")
                    direction_label = {"long": "看涨", "short": "看跌"}.get(direction, "中性")
                    message += f"\n\n<b>AI分析 [{direction_label}]:</b>\n{analysis}"
            except Exception as e:
                logger.warning(f"[MarketAlert] AI分析失败: {e}")

        send_telegram_message(message, parse_mode="HTML")
        logger.info(f"[MarketAlert] 警报已发送: {symbol or 'US Market'}")
        return True
    except Exception as e:
        logger.error(f"[MarketAlert] 发送警报失败: {e}")
        return False


# ==================== 主循环 ====================

def _anomaly_monitor_loop(config: Dict) -> None:
    """异动监控主循环"""
    symbols = config.get("symbols", ["BTC", "ETH"])
    metals_cfg = config.get("metals", {})
    if metals_cfg.get("enabled", False):
        metals = metals_cfg.get("symbols", [])
        if metals:
            symbols = list(dict.fromkeys(list(symbols) + list(metals)))
    interval = config.get("poll_interval_seconds", 30)
    cooldown = config.get("cooldown_seconds", 300)

    global _DEDUP
    _DEDUP = AlertDeduplicator(cooldown)

    logger.info(f"[MarketAlert] 异动监控启动, 币种: {symbols}, 间隔: {interval}s")

    while _RUNNING:
        for symbol in symbols:
            try:
                snapshot = fetch_market_snapshot(symbol, config)
                if not snapshot:
                    continue

                signals = detect_all_signals(snapshot, config)

                for signal in signals:
                    alert_key = f"{symbol}:{signal.signal_type}"
                    if _DEDUP.should_send(alert_key):
                        message = format_alert_message(symbol, snapshot, signal)
                        send_symbol = None if _is_metal_symbol(symbol, config) else symbol
                        if send_alert(message, send_symbol, anomaly_signal=signal):
                            _DEDUP.mark_sent(alert_key)

            except Exception as e:
                logger.error(f"[MarketAlert] 监控异常 {symbol}: {e}")

        time.sleep(interval)


def _us_market_monitor_loop(config: Dict) -> None:
    """美股开盘监控循环"""
    logger.info("[MarketAlert] 美股开盘监控启动")

    while _RUNNING:
        try:
            message = check_us_market_open(config)
            if message:
                send_alert(message)
        except Exception as e:
            logger.error(f"[MarketAlert] 美股监控异常: {e}")

        time.sleep(30)


def start_market_alert_scheduler() -> None:
    """启动市场警报调度器"""
    global _RUNNING, _THREADS, _CACHE

    config = load_config()
    if not config.get("enabled", False):
        logger.info("[MarketAlert] 市场警报功能未启用")
        return

    price_cfg = config.get("price", {})
    try:
        window_minutes = int(price_cfg.get("window_minutes", 15))
    except Exception:
        window_minutes = 15
    _CACHE = MarketDataCache(window_minutes=window_minutes)

    _RUNNING = True

    # 启动异动监控线程
    t1 = threading.Thread(target=_anomaly_monitor_loop, args=(config,), daemon=True)
    t1.start()
    _THREADS.append(t1)

    # 启动美股监控线程
    if config.get("us_market", {}).get("enabled", False):
        t2 = threading.Thread(target=_us_market_monitor_loop, args=(config,), daemon=True)
        t2.start()
        _THREADS.append(t2)

    logger.info("[MarketAlert] 市场警报调度器已启动")


def stop_market_alert_scheduler() -> None:
    """停止市场警报调度器"""
    global _RUNNING
    _RUNNING = False
    logger.info("[MarketAlert] 市场警报调度器已停止")


# ==================== 测试入口 ====================

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        config = load_config()
        # 测试模式
        print("=== 测试市场快照获取 ===")
        snapshot = fetch_market_snapshot("BTC", config)
        if snapshot:
            print(f"BTC价格: ${snapshot.price:,.2f}")
            print(f"资金费率: {snapshot.funding_rate*100:.4f}%")
            print(f"恐惧指数: {snapshot.fear_greed_index}")

        print("\n=== 测试美股数据 ===")
        us_data = fetch_us_market_data("SPY")
        if us_data:
            print(f"SPY: {us_data}")
    else:
        # 启动调度器
        start_market_alert_scheduler()
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            stop_market_alert_scheduler()

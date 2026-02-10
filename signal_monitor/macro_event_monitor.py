#!/usr/bin/env python3
"""
宏观经济数据发布监控模块
- 监控重要经济数据发布时间（CPI、非农、利率决议等）
- 数据发布后第一时间调用AI进行宏观分析
- 发送分析结果到Telegram
"""

import html
import json
import os
import time
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path

import requests

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
    from macro_data import load_macro_data
except Exception:
    load_macro_data = None
try:
    from fundamentals_sources import fetch_macro_snapshot, _parse_macro_time
except Exception:
    fetch_macro_snapshot = None
    _parse_macro_time = None

# 时区
BEIJING_TZ = timezone(timedelta(hours=8))
NY_TZ = timezone(timedelta(hours=-5))

# 重要经济数据关键词
IMPORTANT_EVENTS = [
    "CPI", "Consumer Price Index", "通胀",
    "Non-Farm", "NFP", "非农", "就业",
    "FOMC", "Fed", "利率", "Interest Rate",
    "GDP", "国内生产总值",
    "PCE", "个人消费支出",
    "PPI", "生产者价格指数",
    "Retail Sales", "零售销售",
    "Unemployment", "失业率",
    "PMI", "采购经理指数",
]

# 配置文件路径
CONFIG_PATH = Path(__file__).parent / "macro_event_config.json"
AI_TIMEOUT_SECONDS = int(os.getenv("NOFX_MACRO_AI_TIMEOUT", "120"))

# 已处理的事件缓存
_PROCESSED_EVENTS: Dict[str, float] = {}
_LOCK = threading.Lock()


def load_config() -> Dict[str, Any]:
    """加载配置"""
    defaults = {
        "enabled": True,
        "check_interval_seconds": 60,
        "pre_event_minutes": 5,  # 提前多少分钟提醒
        "post_event_minutes": 10,  # 数据发布后多少分钟内触发分析
        "cooldown_hours": 4,  # 同一事件冷却时间
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),
    }
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return {**defaults, **json.load(f)}
        except Exception:
            pass
    return defaults


def is_important_event(event_name: str) -> bool:
    """判断是否为重要经济事件"""
    name_lower = event_name.lower()
    for keyword in IMPORTANT_EVENTS:
        if keyword.lower() in name_lower:
            return True
    return False


def get_event_importance(event: Dict[str, Any]) -> int:
    """获取事件重要性等级 (1-3)"""
    # 尝试从事件数据中获取重要性
    importance = event.get("importance") or event.get("impact") or event.get("level")
    if isinstance(importance, int):
        return min(max(importance, 1), 3)
    if isinstance(importance, str):
        importance_lower = importance.lower()
        if "high" in importance_lower or "3" in importance_lower:
            return 3
        if "medium" in importance_lower or "2" in importance_lower:
            return 2
    return 1


def parse_event_time(event: Dict[str, Any]) -> Optional[datetime]:
    """解析事件时间"""
    for key in ("time", "timestamp", "ts", "date", "datetime", "release_time", "releaseTime"):
        value = event.get(key)
        if value is None:
            continue
        if _parse_macro_time:
            try:
                dt = _parse_macro_time(value)
                if dt:
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt.astimezone(timezone.utc)
            except Exception:
                pass

        if isinstance(value, (int, float)):
            ts = float(value)
            if ts > 1e12:
                ts /= 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc)

        if isinstance(value, str):
            value = value.strip().replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(value)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                pass
    return None


def _coerce_items(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("items", "data", "events", "calendar", "releases"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def get_upcoming_important_events() -> List[Dict[str, Any]]:
    """获取即将发布的重要经济事件"""
    macro_items: List[Dict[str, Any]] = []
    if fetch_macro_snapshot:
        try:
            snapshot = fetch_macro_snapshot()
            macro = snapshot.get("macro") if isinstance(snapshot, dict) else {}
            if isinstance(macro, dict):
                macro_items.extend(_coerce_items(macro.get("calendar")))
                macro_items.extend(_coerce_items(macro.get("recent_releases")))
        except Exception as exc:
            logger.warning(f"[MacroEvent] Macro snapshot fetch failed: {exc}")
    if not macro_items and load_macro_data:
        try:
            macro_data = load_macro_data()
            calendar = macro_data.get("calendar", {}) if isinstance(macro_data, dict) else {}
            recent = macro_data.get("recent_releases", {}) if isinstance(macro_data, dict) else {}
            macro_items.extend(_coerce_items(calendar))
            macro_items.extend(_coerce_items(recent))
        except Exception:
            macro_items = []
    if not macro_items:
        return []

    try:
        now = datetime.now(timezone.utc)
        config = load_config()
        pre_minutes = config.get("pre_event_minutes", 5)
        post_minutes = config.get("post_event_minutes", 10)

        upcoming = []
        seen_keys = set()
        for event in macro_items:
            event_name = event.get("name") or event.get("event") or event.get("title") or ""
            if not is_important_event(event_name):
                continue

            event_time = parse_event_time(event)
            if not event_time:
                continue

            # 检查是否在时间窗口内（发布前5分钟到发布后10分钟）
            delta_minutes = (event_time - now).total_seconds() / 60
            if -post_minutes <= delta_minutes <= pre_minutes:
                event_key = f"{event_name}_{event_time.strftime('%Y%m%d%H%M')}"
                if event_key in seen_keys:
                    continue
                seen_keys.add(event_key)
                event["_parsed_time"] = event_time
                event["_delta_minutes"] = delta_minutes
                event["_importance"] = get_event_importance(event)
                upcoming.append(event)

        # 按时间排序
        upcoming.sort(key=lambda x: x["_parsed_time"])
        return upcoming

    except Exception as e:
        logger.error(f"[MacroEvent] Error getting upcoming events: {e}")
        return []


def fetch_latest_economic_data(event_name: str) -> Dict[str, Any]:
    """获取最新的经济数据（从外部API）"""
    # 这里可以接入实际的经济数据API
    # 例如：Trading Economics, Investing.com, etc.
    # 目前返回占位数据
    return {
        "event": event_name,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "note": "实际数据需要接入外部API"
    }


def build_macro_analysis_prompt(event: Dict[str, Any], market_data: Dict[str, Any]) -> str:
    """构建宏观分析提示词"""
    event_name = event.get("name") or event.get("event") or event.get("title") or "未知事件"
    event_time = event.get("_parsed_time", datetime.now(timezone.utc))

    # 获取预期值和前值
    forecast = event.get("forecast") or event.get("expected") or "未知"
    previous = event.get("previous") or event.get("prior") or "未知"
    actual = event.get("actual") or "待公布"

    prompt = f"""# 重要经济数据发布分析

## 事件信息
- 事件名称: {event_name}
- 发布时间: {event_time.strftime("%Y-%m-%d %H:%M")} UTC
- 预期值: {forecast}
- 前值: {previous}
- 实际值: {actual}

## 当前市场数据
{json.dumps(market_data, ensure_ascii=False, indent=2)}

## 分析框架（按权重）
总要求：围绕加密市场整体与大盘方向进行全面分析，并单独补充BTC/ETH类别，不得将其作为大盘代理。

### 1. 数据解读（权重30%）
- 该数据的含义和重要性
- 与预期和前值的对比分析
- 数据背后反映的经济状况

### 2. 市场影响预判（权重25%）
- 对美元指数的影响
- 对美股（纳斯达克、标普500）的影响
- 对加密货币整体市场（总市值、成交量、涨跌幅、主导率结构）的影响
- 对黄金的影响

### 3. 加密市场联动分析（权重25%）
- 结合恐惧贪婪指数与总市值/成交量变化判断情绪
- 分析主流币与山寨币的相对强弱与轮动结构
- 预判资金在大盘与板块间的流向变化
- 单独说明BTC/ETH类别的相对强弱（不代表大盘）

### 4. 交易建议（权重20%）
- 短期（1-24小时）操作建议
- 需要关注的关键价位
- 风险提示

请用简洁专业的语言回答，重点突出对加密货币整体市场与大盘的影响。
"""
    return prompt


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _fetch_global_market_snapshot() -> Dict[str, Any]:
    """获取加密市场整体指标快照（总市值/成交量/主导率）"""
    url = "https://api.coingecko.com/api/v3/global"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return {}
        payload = resp.json()
    except Exception:
        return {}

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return {}

    total_market_cap = _safe_float((data.get("total_market_cap") or {}).get("usd"))
    total_volume = _safe_float((data.get("total_volume") or {}).get("usd"))
    market_cap_change = _safe_float(data.get("market_cap_change_percentage_24h_usd"))
    dominance = data.get("market_cap_percentage") if isinstance(data.get("market_cap_percentage"), dict) else {}

    return {
        "total_market_cap": total_market_cap,
        "total_volume_24h": total_volume,
        "market_cap_change_24h": market_cap_change,
        "dominance": {
            "btc": _safe_float(dominance.get("btc")),
            "eth": _safe_float(dominance.get("eth")),
        },
    }


def get_current_market_snapshot() -> Dict[str, Any]:
    """获取当前市场快照"""
    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # 加密市场整体指标
    global_market = _fetch_global_market_snapshot()
    if global_market:
        snapshot["global_market"] = global_market

    # 尝试获取恐惧贪婪指数
    try:
        resp = requests.get(
            "https://api.alternative.me/fng/",
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("data"):
                fng = data["data"][0]
                snapshot["fear_greed_index"] = {
                    "value": int(fng.get("value", 50)),
                    "classification": fng.get("value_classification", "Neutral"),
                }
    except Exception:
        pass

    return snapshot


def call_ai_analysis(prompt: str) -> Optional[str]:
    """调用AI进行分析"""
    try:
        from ai_api_utils import (
            build_payload, resolve_protocol_and_url,
            parse_compatible_content, parse_responses_body,
            AI_PROTOCOL_RESPONSES
        )

        # 读取AI配置
        config_path = Path(__file__).parent / "ai_signal_config.json"
        if not config_path.exists():
            logger.error("[MacroEvent] AI config not found")
            return None

        with open(config_path, "r", encoding="utf-8") as f:
            ai_config = json.load(f)

        api_key = ai_config.get("api_key", "")
        api_url = ai_config.get("api_url", "")
        model = ai_config.get("model", "")

        if not api_key or not api_url:
            logger.error("[MacroEvent] AI config incomplete")
            return None

        system_prompt = "你是一位资深的宏观经济分析师和加密货币交易专家，要求多维度全面分析，擅长解读经济数据对市场的影响。"

        protocol, resolved_url = resolve_protocol_and_url(
            api_url, ai_config.get("api_protocol", "auto")
        )

        payload = build_payload(
            protocol, resolved_url, model,
            system_prompt, prompt,
            max_tokens=2000, temperature=0.3, stream=False
        )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        resp = requests.post(resolved_url, headers=headers, json=payload, timeout=AI_TIMEOUT_SECONDS)

        if resp.status_code == 200:
            if protocol == AI_PROTOCOL_RESPONSES:
                return parse_responses_body(resp.text)
            else:
                return parse_compatible_content(resp.json())
        else:
            logger.error(f"[MacroEvent] AI API error: {resp.status_code} - {resp.text[:200]}")
            return None

    except Exception as e:
        logger.error(f"[MacroEvent] AI analysis error: {e}")
        return None


def _escape_html(text: str) -> str:
    return html.escape(text or "", quote=False)


def _build_fallback_analysis(event: Dict[str, Any], market_data: Dict[str, Any]) -> str:
    """Fallback summary when AI analysis fails."""
    event_name = event.get("name") or event.get("event") or event.get("title") or "未知事件"
    lines = [
        f"AI 分析暂时不可用，先给出基础快照供参考：",
        f"事件: {event_name}",
    ]

    global_market = market_data.get("global_market")
    if isinstance(global_market, dict):
        total_cap = global_market.get("total_market_cap")
        total_vol = global_market.get("total_volume_24h")
        cap_change = global_market.get("market_cap_change_24h")
        dominance = global_market.get("dominance") or {}
        if total_cap:
            lines.append(f"总市值: ${total_cap:,.0f}")
        if total_vol:
            lines.append(f"24H成交量: ${total_vol:,.0f}")
        if cap_change is not None:
            lines.append(f"总市值24H变化: {cap_change:+.2f}%")
        if isinstance(dominance, dict):
            btc_dom = dominance.get("btc")
            eth_dom = dominance.get("eth")
            if btc_dom is not None or eth_dom is not None:
                lines.append(
                    "主导率: "
                    + ", ".join(
                        part
                        for part in [
                            f"BTC {btc_dom:.2f}%" if isinstance(btc_dom, (int, float)) else None,
                            f"ETH {eth_dom:.2f}%" if isinstance(eth_dom, (int, float)) else None,
                        ]
                        if part
                    )
                )

    fgi = market_data.get("fear_greed_index")
    if fgi:
        lines.append(f"恐惧贪婪指数: {fgi.get('value')} ({fgi.get('classification', 'Neutral')})")

    return "\n".join(lines)


def format_analysis_message(event: Dict[str, Any], analysis: str) -> str:
    """格式化分析消息"""
    event_name = event.get("name") or event.get("event") or event.get("title") or "未知事件"
    event_time = event.get("_parsed_time", datetime.now(timezone.utc))
    importance = event.get("_importance", 1)

    importance_emoji = "🔴" if importance >= 3 else "🟡" if importance >= 2 else "🟢"

    message = f"""📊 <b>重要经济数据发布</b>

{importance_emoji} <b>{event_name}</b>
⏰ 发布时间: {event_time.strftime("%Y-%m-%d %H:%M")} UTC

<b>📈 AI 宏观分析</b>

{analysis}

<i>⚠️ 以上分析仅供参考，不构成投资建议</i>
"""
    return message


def process_event(event: Dict[str, Any]) -> bool:
    """处理单个事件"""
    event_name = event.get("name") or event.get("event") or event.get("title") or ""
    event_time = event.get("_parsed_time")

    if not event_name or not event_time:
        return False

    # 生成事件唯一标识
    event_key = f"{event_name}_{event_time.strftime('%Y%m%d%H%M')}"

    # 检查是否已处理
    config = load_config()
    cooldown_hours = config.get("cooldown_hours", 4)

    with _LOCK:
        last_processed = _PROCESSED_EVENTS.get(event_key, 0)
        if time.time() - last_processed < cooldown_hours * 3600:
            return False
        _PROCESSED_EVENTS[event_key] = time.time()

    logger.info(f"[MacroEvent] Processing event: {event_name}")

    # 获取市场快照
    market_data = get_current_market_snapshot()

    # 构建提示词
    prompt = build_macro_analysis_prompt(event, market_data)

    # 调用AI分析
    analysis = call_ai_analysis(prompt)

    if not analysis:
        logger.error(f"[MacroEvent] Failed to get AI analysis for: {event_name}")
        analysis = _build_fallback_analysis(event, market_data)

    # 格式化消息
    message = format_analysis_message(event, _escape_html(analysis))

    # 发送到Telegram
    if send_telegram_message:
        try:
            send_telegram_message(message)
            logger.info(f"[MacroEvent] Sent analysis for: {event_name}")
            return True
        except Exception as e:
            logger.error(f"[MacroEvent] Failed to send message: {e}")
            return False
    else:
        logger.warning("[MacroEvent] Telegram not available")
        print(message)
        return True


def check_and_process_events():
    """检查并处理即将发布的事件"""
    events = get_upcoming_important_events()

    for event in events:
        delta_minutes = event.get("_delta_minutes", 0)

        # 如果数据已经发布（delta < 0），立即触发分析
        if delta_minutes <= 0:
            process_event(event)


def start_monitor():
    """启动监控"""
    config = load_config()
    if not config.get("enabled", True):
        logger.info("[MacroEvent] Monitor disabled")
        return

    interval = config.get("check_interval_seconds", 60)
    logger.info(f"[MacroEvent] Starting monitor, interval={interval}s")

    while True:
        try:
            check_and_process_events()
        except Exception as e:
            logger.error(f"[MacroEvent] Monitor error: {e}")

        time.sleep(interval)


def start_monitor_background():
    """在后台启动监控"""
    thread = threading.Thread(target=start_monitor, daemon=True)
    thread.start()
    return thread

# 别名，供调度器调用
start_macro_event_monitor = start_monitor_background


# 手动触发分析（用于测试）
def trigger_analysis_for_event(event_name: str):
    """手动触发某个事件的分析"""
    event = {
        "name": event_name,
        "_parsed_time": datetime.now(timezone.utc),
        "_importance": 3,
    }
    return process_event(event)


if __name__ == "__main__":
    # 测试
    print("Testing macro event monitor...")

    # 获取即将发布的重要事件
    events = get_upcoming_important_events()
    print(f"Found {len(events)} upcoming important events")

    for event in events:
        print(f"  - {event.get('name')} at {event.get('_parsed_time')}")

    # 手动触发CPI分析测试
    # trigger_analysis_for_event("US CPI (YoY)")

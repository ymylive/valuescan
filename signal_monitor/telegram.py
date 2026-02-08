"""
Telegram 消息发送模块
负责格式化消息并发送到 Telegram Bot
"""

import json
import time
import os
import glob
import threading
import queue
from pathlib import Path
from datetime import datetime, timezone, timedelta
import requests
from logger import logger
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from binance_alpha_cache import is_binance_alpha_symbol

# 尝试导入通知开关，如果不存在则使用默认值
try:
    from config import ENABLE_TELEGRAM
except ImportError:
    ENABLE_TELEGRAM = True  # 默认启用

# AI 简评开关从 JSON 配置文件读取
def _get_ai_signal_enabled() -> bool:
    """从 JSON 配置文件获取 AI 简评启用状态"""
    try:
        from ai_signal_analysis import get_ai_signal_config
        config = get_ai_signal_config()
        return config.get("enabled", True)
    except Exception:
        return True  # 默认启用

try:
    from config import LANGUAGE
except ImportError:
    LANGUAGE = "zh"

# 尝试导入自动删除图表配置
try:
    from config import AUTO_DELETE_CHARTS
except ImportError:
    AUTO_DELETE_CHARTS = True  # 默认启用

# 北京时区 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))
_PRO_CHART_LOCK = threading.Lock()
_ASYNC_QUEUE_PUT_TIMEOUT = float(os.getenv("NOFX_ASYNC_QUEUE_TIMEOUT", "2"))
_ASYNC_QUEUE_WARN_INTERVAL = float(os.getenv("NOFX_ASYNC_QUEUE_WARN_INTERVAL", "10"))
_AI_ANALYSIS_QUEUE_SIZE = int(os.getenv("NOFX_AI_ANALYSIS_QUEUE_SIZE", "100"))
_CHART_QUEUE_SIZE = int(os.getenv("NOFX_CHART_QUEUE_SIZE", "50"))
_AI_ANALYSIS_QUEUE = queue.Queue(maxsize=_AI_ANALYSIS_QUEUE_SIZE)
_CHART_QUEUE = queue.Queue(maxsize=_CHART_QUEUE_SIZE)
_WORKERS_STARTED = False
_WORKER_INIT_LOCK = threading.Lock()
_AI_ANALYSIS_MAX_RETRIES = max(1, int(os.getenv("NOFX_AI_ANALYSIS_RETRY", "2")))
_AI_ANALYSIS_RETRY_DELAY = float(os.getenv("NOFX_AI_ANALYSIS_RETRY_DELAY", "2"))
_CHART_MAX_RETRIES = max(1, int(os.getenv("NOFX_CHART_RETRY", "2")))
_CHART_RETRY_DELAY = float(os.getenv("NOFX_CHART_RETRY_DELAY", "3"))


def _queue_worker(task_queue, label):
    while True:
        task = task_queue.get()
        if task is None:
            task_queue.task_done()
            break
        func, args, kwargs = task
        try:
            func(*args, **kwargs)
        except Exception as exc:
            logger.warning(f"[AsyncQueue] {label} task failed: {exc}")
        finally:
            task_queue.task_done()


def _ensure_async_workers():
    global _WORKERS_STARTED
    if _WORKERS_STARTED:
        return
    with _WORKER_INIT_LOCK:
        if _WORKERS_STARTED:
            return
        threading.Thread(
            target=_queue_worker,
            args=(_AI_ANALYSIS_QUEUE, "AI Analysis"),
            daemon=True,
            name="ai-analysis-worker",
        ).start()
        threading.Thread(
            target=_queue_worker,
            args=(_CHART_QUEUE, "Chart"),
            daemon=True,
            name="chart-worker",
        ).start()
        _WORKERS_STARTED = True


def _enqueue_task(task_queue, label, func, *args, **kwargs):
    warned_at = None
    while True:
        try:
            task_queue.put((func, args, kwargs), timeout=_ASYNC_QUEUE_PUT_TIMEOUT)
            return True
        except queue.Full:
            now = time.time()
            if warned_at is None or (now - warned_at) >= _ASYNC_QUEUE_WARN_INTERVAL:
                logger.warning(
                    f"[AsyncQueue] {label} queue full (size={task_queue.qsize()}). "
                    "Waiting to enqueue to avoid drop."
                )
                warned_at = now


def _get_telegram_proxies():
    """
    Resolve proxy settings for Telegram API requests.
    """
    import os

    proxies = {}

    telegram_proxy = os.getenv("NOFX_TELEGRAM_PROXY") or os.getenv("TELEGRAM_PROXY")
    if telegram_proxy:
        proxies["http"] = telegram_proxy
        proxies["https"] = telegram_proxy

    http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")

    if http_proxy and not proxies:
        proxies["http"] = http_proxy
    if https_proxy and not proxies:
        proxies["https"] = https_proxy

    if not proxies:
        try:
            from config import HTTP_PROXY as CONFIG_HTTP_PROXY
            if CONFIG_HTTP_PROXY:
                proxies["http"] = CONFIG_HTTP_PROXY
                proxies["https"] = CONFIG_HTTP_PROXY
        except ImportError:
            pass

    return proxies or None


def _post_telegram(url, **kwargs):
    proxies = _get_telegram_proxies()
    try:
        if proxies:
            return requests.post(url, proxies=proxies, **kwargs)
        return requests.post(url, **kwargs)
    except requests.exceptions.ProxyError as exc:
        if proxies:
            logger.warning("Telegram proxy failed, retrying without proxy: %s", exc)
            return requests.post(url, **kwargs)
        raise




def _load_market_alert_config():
    cfg_path = Path(__file__).with_name("market_alert_config.json")
    if not cfg_path.exists():
        return {}
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _get_metals_config():
    cfg = {
        "enabled": False,
        "symbols": ["XAUUSD", "XAGUSD"],
        "yahoo_symbol_map": {
            "XAUUSD": "GC=F",
            "XAGUSD": "SI=F",
        },
    }
    file_cfg = _load_market_alert_config()
    metals_cfg = file_cfg.get("metals", {}) if isinstance(file_cfg, dict) else {}
    if isinstance(metals_cfg, dict):
        if "enabled" in metals_cfg:
            cfg["enabled"] = bool(metals_cfg.get("enabled"))
        if isinstance(metals_cfg.get("symbols"), list) and metals_cfg.get("symbols"):
            cfg["symbols"] = [str(s).upper() for s in metals_cfg["symbols"]]
        if isinstance(metals_cfg.get("yahoo_symbol_map"), dict):
            cfg["yahoo_symbol_map"].update({str(k).upper(): str(v) for k, v in metals_cfg["yahoo_symbol_map"].items()})
    return cfg


def _is_metal_symbol(symbol: str) -> bool:
    sym = str(symbol or "").upper().replace("$", "").strip()
    cfg = _get_metals_config()
    symbols = cfg.get("symbols") if isinstance(cfg, dict) else []
    return sym in set([str(s).upper() for s in symbols])


def _render_simple_candles(symbol: str, klines: list):
    try:
        import pandas as pd
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from io import BytesIO
    except Exception:
        return None
    cleaned = _normalize_klines_for_chart(klines)
    df = pd.DataFrame(cleaned)
    if df.empty:
        return None
    fig, ax = plt.subplots(figsize=(8, 4))
    prices = df[["open", "high", "low", "close"]]
    price_min = prices.min().min()
    price_max = prices.max().max()
    for i, row in df.iterrows():
        is_up = row["close"] >= row["open"]
        color = "#2ecc71" if is_up else "#e74c3c"
        ax.plot([i, i], [row["low"], row["high"]], color=color, linewidth=1)
        body_bottom = min(row["open"], row["close"])
        body_height = abs(row["close"] - row["open"])
        if body_height <= 0:
            body_height = (price_max - price_min) * 0.001 if price_max > price_min else 0.001
        rect = mpatches.Rectangle((i - 0.3, body_bottom), 0.6, body_height, facecolor=color, edgecolor=color, alpha=0.9)
        ax.add_patch(rect)
    ax.set_title(f"{symbol} Chart")
    ax.grid(True, linestyle="--", alpha=0.2)
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=140)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _limit_klines_for_chart(klines: list, limit: int) -> list:
    if not isinstance(klines, list) or not klines:
        return []
    if limit <= 0:
        return klines
    if all(isinstance(item, dict) and isinstance(item.get("ts"), (int, float)) for item in klines):
        klines = sorted(klines, key=lambda item: item.get("ts", 0))
    return klines[-limit:]


def _normalize_klines_for_chart(klines: list) -> list:
    if not isinstance(klines, list) or not klines:
        return []
    cleaned = []
    for item in klines:
        if not isinstance(item, dict):
            continue
        try:
            o = float(item.get("open"))
            h = float(item.get("high"))
            l = float(item.get("low"))
            c = float(item.get("close"))
        except Exception:
            continue
        ts = item.get("ts")
        try:
            ts_val = int(ts) if ts is not None else None
        except Exception:
            ts_val = None
        hi = max(h, o, c)
        lo = min(l, o, c)
        cleaned.append({
            "ts": ts_val,
            "open": o,
            "high": hi,
            "low": lo,
            "close": c,
            "volume": item.get("volume", 0) or 0,
        })
    if not cleaned:
        return []
    if all(isinstance(row.get("ts"), int) for row in cleaned):
        cleaned.sort(key=lambda row: row.get("ts", 0))
    total = len(cleaned)
    if total >= 20:
        downs = sum(1 for row in cleaned if row["close"] < row["open"])
        ups = sum(1 for row in cleaned if row["close"] > row["open"])
        first_open = cleaned[0]["open"]
        last_close = cleaned[-1]["close"]
        net_change = 0.0
        if first_open:
            net_change = (last_close - first_open) / first_open
        if downs / total > 0.9 and net_change > 0.01:
            cleaned = [_swap_open_close(row) for row in cleaned]
        elif ups / total > 0.9 and net_change < -0.01:
            cleaned = [_swap_open_close(row) for row in cleaned]
    return cleaned


def _swap_open_close(row: dict) -> dict:
    o = row.get("open")
    c = row.get("close")
    h = row.get("high")
    l = row.get("low")
    row["open"], row["close"] = c, o
    try:
        hi = max(float(h), float(o), float(c))
        lo = min(float(l), float(o), float(c))
        row["high"] = hi
        row["low"] = lo
    except Exception:
        pass
    return row


def _generate_metals_chart(symbol: str):
    base = str(symbol or "").upper().replace("$", "").strip()
    try:
        from metals_chart_generator import generate_metals_chart
        chart = generate_metals_chart(base)
        if chart:
            return chart
    except Exception:
        pass
    latest_quote = {}
    try:
        from market_data_sources import fetch_market_snapshot
        latest_quote = fetch_market_snapshot(base, force_refresh=True) or {}
    except Exception:
        latest_quote = {}
    quote = latest_quote
    try:
        price = float(quote.get("price", 0) or 0)
    except Exception:
        price = 0.0
    if price <= 0:
        return None
    change_pct = float(quote.get("price_change_percent", 0) or 0)
    prev = price / (1 + change_pct / 100) if change_pct else price
    high = float(quote.get("high_24h", price) or price)
    low = float(quote.get("low_24h", price) or price)
    volume = float(quote.get("volume_24h", 0) or 0)
    klines = [{
        "ts": int(time.time()) * 1000,
        "open": prev,
        "high": high,
        "low": low,
        "close": price,
        "volume": volume,
    }]
    return _render_simple_candles(base, klines)


def _generate_snapshot_chart(symbol: str):
    base = str(symbol or "").upper().replace("$", "").strip()
    try:
        from market_data_sources import fetch_market_snapshot
        quote = fetch_market_snapshot(base) or {}
    except Exception:
        quote = {}
    try:
        price = float(quote.get("price", 0) or 0)
    except Exception:
        price = 0.0
    if price <= 0:
        return None
    change_pct = float(quote.get("price_change_percent", 0) or 0)
    prev = price / (1 + change_pct / 100) if change_pct else price
    high = float(quote.get("high_24h", price) or price)
    low = float(quote.get("low_24h", price) or price)
    volume = float(quote.get("volume_24h", 0) or 0)
    klines = [{
        "ts": int(time.time()) * 1000,
        "open": prev,
        "high": high,
        "low": low,
        "close": price,
        "volume": volume,
    }]
    return _render_simple_candles(base, klines)

def cleanup_chart_files():
    """
    清理可能生成的临时图表文件
    虽然主要使用内存生成，但为了防止残留文件，执行清理
    """
    if not AUTO_DELETE_CHARTS:
        logger.debug("Auto-delete charts disabled; skipping cleanup.")
        return

    try:
        # 清理 output 目录下的 png 文件
        files = glob.glob("output/chart_*.png")
        files.extend(glob.glob("output/test_chart_*.png"))
        files.extend(glob.glob("*.png"))  # 当前目录
        
        for f in files:
            try:
                os.remove(f)
                logger.debug(f"Deleted temp file: {f}")
            except Exception as e:
                logger.warning(f"Failed to delete temp file {f}: {e}")
                
    except Exception as e:
        logger.warning(f"Chart cleanup error: {e}")


def get_binance_futures_link(symbol: str) -> str:
    """
    生成Binance合约链接
    
    **Feature: coin-search, Property 5: Binance Link Format**
    **Validates: Requirements 5.1, 5.2, 5.3**
    
    Args:
        symbol: 币种符号（如 BTC, ETH）
    
    Returns:
        str: Binance合约页面URL
    """
    if not symbol:
        return ""
    # 确保符号大写并添加USDT后缀
    clean_symbol = symbol.upper().strip()
    if not clean_symbol.endswith('USDT'):
        clean_symbol = f"{clean_symbol}USDT"
    return f"https://www.binance.com/zh-CN/futures/{clean_symbol}"


def format_binance_link_html(symbol: str) -> str:
    """
    格式化Binance链接为HTML超链接
    
    **Feature: coin-search, Property 5: Binance Link Format**
    **Validates: Requirements 5.1, 5.2, 5.3**
    
    Args:
        symbol: 币种符号
    
    Returns:
        str: HTML格式的超链接
    """
    if not symbol:
        return ""
    url = get_binance_futures_link(symbol)
    return f'<a href="{url}">📊 Binance合约</a>'


def get_beijing_time_str(timestamp_ms, format_str='%H:%M:%S'):
    """
    将时间戳转换为北京时间字符串
    
    Args:
        timestamp_ms: 毫秒级时间戳
        format_str: 时间格式字符串，默认为 '%H:%M:%S'
    
    Returns:
        str: 格式化后的北京时间字符串（带UTC+8标识）
    """
    if not timestamp_ms:
        return 'N/A'
    dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=BEIJING_TZ)
    return dt.strftime(format_str) + ' (UTC+8)'


def send_telegram_message(
    message_text,
    pin_message=False,
    symbol=None,
    parse_mode="HTML",
    reply_to_message_id=None,
):
    """
    发送消息到 Telegram

    Args:
        message_text: 要发送的消息文本（支持 HTML 格式）
        pin_message: 是否置顶该消息（默认 False）
        symbol: 币种符号，用于生成Binance合约链接（可选）
        parse_mode: 解析模式（HTML/Markdown/None）

    Returns:
        dict: 发送成功返回包含 message_id 的字典，失败返回 None
    """
    # 检查是否启用 Telegram 通知
    if not ENABLE_TELEGRAM:
        logger.info("    Telegram notifications disabled; skipping.")
        return {"success": True, "message_id": None}  # 返回成功状态以便继续后续流程

    if not TELEGRAM_BOT_TOKEN:
        logger.warning("   Telegram bot token missing; skipping.")
        return None
    if not TELEGRAM_CHAT_ID:
        logger.warning("   Telegram chat ID missing; skipping.")
        return None

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    buttons = []

    # Add Binance futures link when symbol is available.
    if symbol:
        binance_url = get_binance_futures_link(symbol)
        buttons.append({
            "text": "Binance Futures",
            "url": binance_url
        })
    inline_keyboard = {"inline_keyboard": [buttons]} if buttons else None

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message_text,
        "disable_web_page_preview": True,
    }
    if inline_keyboard:
        payload["reply_markup"] = inline_keyboard
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id

    # 配置代理

    try:
        response = _post_telegram(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info("   Telegram message sent.")
            
            result = response.json()
            message_id = result.get('result', {}).get('message_id')

            # 如果需要置顶消息
            if pin_message and message_id:
                _pin_telegram_message(message_id)

            return {"success": True, "message_id": message_id}
        else:
            logger.error(f"   Telegram message failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"   Telegram message error: {e}")
        return None


def send_telegram_photo(photo_data, caption=None, pin_message=False):
    """
    发送图片到 Telegram

    Args:
        photo_data: 图片数据（bytes）
        caption: 图片说明文字（支持 HTML 格式，可选）
        pin_message: 是否置顶该消息（默认 False）

    Returns:
        bool: 发送成功返回 True，否则返回 False
    """
    # 检查是否启用 Telegram 通知
    if not ENABLE_TELEGRAM:
        logger.info("    Telegram notifications disabled; skipping.")
        return True

    if not TELEGRAM_BOT_TOKEN:
        logger.warning("   Telegram bot token missing; skipping.")
        return False
    if not TELEGRAM_CHAT_ID:
        logger.warning("   Telegram chat ID missing; skipping.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"

    # 构建多部分表单数据
    files = {
        'photo': ('chart.png', photo_data, 'image/png')
    }

    data = {
        'chat_id': TELEGRAM_CHAT_ID,
    }

    if caption:
        data['caption'] = caption
        data['parse_mode'] = 'HTML'

    # 配置代理

    try:
        response = _post_telegram(url, data=data, files=files, timeout=30)
        if response.status_code == 200:
            logger.info("   Telegram photo sent.")

            # 如果需要置顶消息
            if pin_message:
                result = response.json()
                message_id = result.get('result', {}).get('message_id')
                if message_id:
                    _pin_telegram_message(message_id)

            cleanup_chart_files()  # 发送后清理临时文件
            return True
        else:
            logger.error(f"   Telegram photo failed: {response.status_code} - {response.text}")
            cleanup_chart_files()  # 失败也要清理
            return False
    except Exception as e:
        logger.error(f"   Telegram photo error: {e}")
        cleanup_chart_files()  # 异常也要清理
        return False


def edit_message_with_photo(message_id, photo_data, caption=None):
    """
    编辑已发送的消息，将其替换为图片消息（支持429重试）

    Args:
        message_id: 要编辑的消息ID
        photo_data: 图片数据（bytes）
        caption: 图片说明文字（支持 HTML 格式，可选）

    Returns:
        bool: 编辑成功返回 True，否则返回 False
    """
    # 检查是否启用 Telegram 通知
    if not ENABLE_TELEGRAM:
        logger.info("    Telegram notifications disabled; skipping.")
        return True

    if not TELEGRAM_BOT_TOKEN:
        logger.warning("   Telegram bot token missing; skipping.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageMedia"

    # 构建多部分表单数据
    files = {
        'media': ('chart.png', photo_data, 'image/png')
    }

    # 构建媒体对象
    media_data = {
        "type": "photo",
        "media": "attach://media"
    }
    
    if caption:
        media_data["caption"] = caption
        media_data["parse_mode"] = "HTML"

    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'message_id': message_id,
        'media': json.dumps(media_data)
    }

    max_retries = 3
    base_delay = 2  # 基础延迟秒数

    for attempt in range(max_retries):
        try:
            # 添加随机延迟避免并发冲突
            if attempt > 0:
                delay = base_delay + (attempt * 2)  # 递增延迟: 2, 4, 6秒
                logger.info(f"    Waiting {delay}s before retry ({attempt + 1}/{max_retries})")
                time.sleep(delay)

            response = _post_telegram(url, data=data, files=files, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"   Telegram message updated (ID: {message_id})")
                cleanup_chart_files()
                return True
            elif response.status_code == 429:
                # 处理速率限制
                try:
                    error_data = response.json()
                    retry_after = error_data.get('parameters', {}).get('retry_after', 10)
                    logger.warning(f"   Telegram rate limit, retry in {retry_after}s ({attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:  # 不是最后一次尝试
                        time.sleep(retry_after + 1)  # 多等1秒确保安全
                        continue
                except:
                    # JSON解析失败，使用默认延迟
                    logger.warning(f"   Telegram rate limit, retry in 10s ({attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(10)
                        continue
                
                logger.error(f"   Telegram rate limit failed: 429 - {response.text}")
                cleanup_chart_files()
                return False
            else:
                logger.error(f"   Telegram edit failed: {response.status_code} - {response.text}")
                if attempt < max_retries - 1:
                    continue  # 其他错误也重试
                cleanup_chart_files()
                return False
                
        except Exception as e:
            logger.error(f"   Telegram edit error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(base_delay)
                continue
            cleanup_chart_files()
            return False

    return False


def _pin_telegram_message(message_id):
    """
    置顶 Telegram 消息（内部函数）

    Args:
        message_id: 要置顶的消息ID

    Returns:
        bool: 置顶成功返回 True，否则返回 False
    """
    if not TELEGRAM_BOT_TOKEN:
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/pinChatMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "message_id": message_id,
        "disable_notification": False  # 发送通知提醒用户
    }


    try:
        response = _post_telegram(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info(f"Telegram message pinned (ID: {message_id})")
            return True
        else:
            logger.warning(f"Telegram pin failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.warning(f"Telegram pin error: {e}")
        return False


def _get_binance_alpha_badge(symbol):
    """
    获取币安Alpha标识

    Args:
        symbol: 币种符号

    Returns:
        str: 如果在币安Alpha交集中返回标识，否则返回空字符串
    """
    if not symbol:
        return ""

    try:
        if is_binance_alpha_symbol(symbol):
            return " 🔥 <b>币安Alpha</b>"
    except Exception as e:
        logger.debug(f"检查币安Alpha失败: {e}")

    return ""


def _get_recommendation_direction(msg_type, content):
    """Determine direction from signal metadata only.
    Returns: "BULLISH" / "BEARISH" / None
    """
    if not isinstance(msg_type, int):
        return None
    funds_type = content.get("fundsMovementType") if isinstance(content, dict) else None

    # 核心信号：Alpha/FOMO 偏多
    if msg_type in (109, 110, 113):
        return "BULLISH"

    # 风险/出逃类偏空
    if msg_type in (111, 112):
        return "BEARISH"

    # 资金异动（108）按资金类型区分
    if msg_type == 108:
        if funds_type in (4, 6, 7):
            return "BEARISH"
        if funds_type in (1, 2, 3, 5):
            return "BULLISH"

    # 资金异常（114）带涨幅时通常为止盈提示
    if msg_type == 114:
        ext_field = content.get("extField", {}) if isinstance(content, dict) else {}
        gains = ext_field.get("gains", 0) if isinstance(ext_field, dict) else 0
        if gains and gains >= 20:
            return "BEARISH"
        return "BULLISH"

    # AI 追踪/风险（100）由 predictType 决定
    if msg_type == 100:
        predict_type = content.get("predictType", 0) if isinstance(content, dict) else 0
        bullish_types = {3, 5, 8, 22, 23, 28}
        bearish_types = {1, 2, 4, 7, 16, 17, 19, 24, 29, 30, 31}
        if predict_type in bullish_types:
            return "BULLISH"
        if predict_type in bearish_types:
            return "BEARISH"

    return None


def _get_recommendation_line(msg_type, content):
    if msg_type in (112, 113):
        return None
    direction = _get_recommendation_direction(msg_type, content)
    if direction == "BULLISH":
        return "Recommendation: <b>Bullish</b> (based on signals)"
    if direction == "BEARISH":
        return "Recommendation: <b>Bearish</b> (based on signals)"
    return None

def format_message_for_telegram(item):
    """
    格式化消息为 Telegram HTML 格式

    Args:
        item: 消息数据字典

    Returns:
        str: 格式化后的 HTML 消息文本
    """
    from message_types import MESSAGE_TYPE_MAP, TRADE_TYPE_MAP, FUNDS_MOVEMENT_MAP

    msg_type = item.get('type', 'N/A')
    msg_type_name = MESSAGE_TYPE_MAP.get(msg_type, 'N/A') if isinstance(msg_type, int) else 'N/A'

    # 解析 content 字段
    content = {}
    symbol = None
    if 'content' in item and item['content']:
        try:
            content = json.loads(item['content'])
            symbol = content.get('symbol')
        except json.JSONDecodeError:
            pass

    # 根据消息类型使用不同的格式
    if msg_type == 100:  # 下跌风险 - 特殊格式
        formatted_message = _format_risk_alert(item, content, msg_type_name)
    else:  # 其他类型 - 通用格式
        formatted_message = _format_general_message(item, content, msg_type, msg_type_name)

    # 插入方向性推荐（看涨/看跌）
    recommendation_line = _get_recommendation_line(msg_type, content)
    if recommendation_line:
        lines = formatted_message.split('\n')
        if not any("推荐" in ln for ln in lines[:3]):
            insert_at = 2 if len(lines) >= 2 else 1
            lines.insert(insert_at, recommendation_line)
            formatted_message = '\n'.join(lines)

    # 统一添加币安Alpha标识（如果币种在交集中）
    if symbol and _get_binance_alpha_badge(symbol):
        # 在第一行标题后添加币安Alpha标识
        lines = formatted_message.split('\n')
        if lines:
            # 找到第一个包含 ${symbol} 的行（标题行）
            for i, line in enumerate(lines):
                if f'${symbol}' in line and '<b>' in line:
                    lines[i] = line.rstrip('</b>') + ' 🔥 币安Alpha</b>' if line.endswith('</b>') else line + ' 🔥 <b>币安Alpha</b>'
                    break
            formatted_message = '\n'.join(lines)

    return formatted_message


def _format_risk_alert(item, content, msg_type_name):
    """
    格式化 AI 追踪告警（type 100）
    根据 predictType 区分不同场景：
    - predictType 2: 主力出逃（风险增加）
    - predictType 4: 主力减持风险
    - predictType 5: AI 开始追踪潜力代币
    - predictType 7: 风险增加，主力大量减持
    - predictType 8: 下跌趋势减弱，追踪结束
    - predictType 16: 追踪后涨幅达到盈利目标（10%+，上涨止盈）
    - predictType 17: 达到最大涨幅后回调止盈（15%+回调）
    - predictType 19: 追踪后跌幅达到止损位（15%+，下跌止盈）
    - predictType 24: 价格高点风险（疑似顶部）
    - predictType 28: 主力增持加速（上涨机会）
    - predictType 29: 主力持仓减少加速
    - predictType 30: 追踪后涨幅5-10%（保护本金）
    - predictType 31: 追踪后跌幅5-15%（保护本金）
    """
    from message_types import TRADE_TYPE_MAP, FUNDS_MOVEMENT_MAP

    symbol = content.get('symbol', 'N/A')
    price = content.get('price', 'N/A')
    change_24h = content.get('percentChange24h', 0)
    predict_type = content.get('predictType', 0)
    risk_decline = content.get('riskDecline', 0)
    gains = content.get('gains', 0)
    rebound = content.get('rebound', 0)
    scoring = content.get('scoring', 0)

    # 根据 predictType 判断场景
    if predict_type == 2:
        # 主力出逃（风险增加）
        emoji = "🔴"
        title = f"<b>${symbol} 主力出逃警示</b>"
        tag = "#主力出逃"
        
        message_parts = [
            f"{emoji} {title}",
            f"━━━━━━━━━",
            f"⚠️ 疑似主力<b>大量减持</b>",
            f"📉 <b>风险增加</b>，建议止盈",
            f"💵 现价: <b>${price}</b>",
        ]
        
        if change_24h:
            change_emoji = "📈" if change_24h >= 0 else "📉"
            change_text = "涨幅" if change_24h >= 0 else "跌幅"
            message_parts.append(f"{change_emoji} 24H{change_text}: <code>{change_24h:+.2f}%</code>")
        
        # 显示追踪期涨跌幅
        if gains and gains > 0:
            message_parts.append(f"📈 追踪涨幅: <code>+{gains:.2f}%</code>")
        if content.get('decline', 0) > 0:
            decline = content.get('decline', 0)
            message_parts.append(f"📉 回调幅度: <code>-{decline:.2f}%</code>")
        
        if scoring:
            message_parts.append(f"🎯 AI评分: <b>{int(scoring)}</b>")
        
        message_parts.extend([
            f"",
            f"💡 风险警示:",
            f"   • 🔴 <b>主力疑似出逃</b>",
            f"   • 📉 价格可能进入调整期",
            f"   • 💰 <b>建议大部分止盈</b>",
            f"   • 🛡️ 保护已有利润",
            f"   • ⛔ 不建议继续追高",
            f"",
            f"{tag}",
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])
    
    elif predict_type == 24:
        # 价格高点风险（疑似顶部）
        emoji = "📍"
        title = f"<b>${symbol} 价格高点警示</b>"
        tag = "#下跌风险"
        
        message_parts = [
            f"{emoji} {title}",
            f"━━━━━━━━━",
            f"⚠️ AI捕获疑似价格<b>高点</b>，注意回调风险",
            f"💵 现价: <b>${price}</b>",
        ]
        
        if change_24h:
            change_emoji = "📈" if change_24h >= 0 else "📉"
            change_text = "涨幅" if change_24h >= 0 else "跌幅"
            message_parts.append(f"{change_emoji} 24H{change_text}: <code>{change_24h:+.2f}%</code>")
            
            # 如果涨幅较大，额外提示
            if change_24h > 10:
                message_parts.append(f"🔥 短期涨幅较大，回调风险增加")
        
        if scoring:
            score_int = int(scoring)
            message_parts.append(f"🎯 AI评分: <b>{score_int}</b>")
        
        message_parts.extend([
            f"",
            f"💡 风险提示:",
            f"   • ⚠️ <b>疑似价格顶部区域</b>",
            f"   • 📉 可能面临回调压力",
            f"   • 🛑 不建议追高，谨慎买入",
            f"   • 💰 已持仓可考虑分批减仓",
            f"   • 👀 AI 开始实时追踪走势",
            f"",
            f"{tag}",
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])
    
    elif predict_type == 5:
        # AI 开始追踪潜力代币
        emoji = "🔍"
        title = f"<b>${symbol} AI 开始追踪</b>"
        tag = "#观察代币"
        
        message_parts = [
            f"{emoji} {title}",
            f"━━━━━━━━━",
            f"🤖 AI捕获潜力代币，开始实时追踪",
            f"💵 现价: <b>${price}</b>",
        ]
        
        if change_24h:
            change_emoji = "📈" if change_24h >= 0 else "📉"
            change_text = "涨幅" if change_24h >= 0 else "跌幅"
            message_parts.append(f"{change_emoji} 24H{change_text}: <code>{change_24h:+.2f}%</code>")
        
        if scoring:
            # 根据评分给出不同的评价
            score_int = int(scoring)
            if score_int >= 70:
                score_desc = "⭐⭐⭐ 高分"
            elif score_int >= 60:
                score_desc = "⭐⭐ 中上"
            elif score_int >= 50:
                score_desc = "⭐ 中等"
            else:
                score_desc = "观察中"
            message_parts.append(f"🎯 AI评分: <b>{score_int}</b> ({score_desc})")
        
        message_parts.extend([
            f"",
            f"💡 提示:",
            f"   • 🔍 AI 已开始实时监控",
            f"   • 📊 关注后续价格和资金动态",
            f"   • 🎯 等待更明确的入场信号",
            f"   • ⚠️ 追踪≠建议买入，注意风险",
            f"",
            f"{tag}",
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])
    
    elif predict_type == 7:
        # 风险增加，主力大量减持
        emoji = "⚠️"
        title = f"<b>${symbol} 风险增加警示</b>"
        tag = "#下跌风险"
        
        message_parts = [
            f"{emoji} {title}",
            f"━━━━━━━━━",
            f"🚨 疑似主力<b>大量减持</b>",
            f"📉 价格有下跌风险",
            f"💵 现价: <b>${price}</b>",
        ]
        
        if change_24h:
            change_emoji = "📈" if change_24h >= 0 else "📉"
            change_text = "涨幅" if change_24h >= 0 else "跌幅"
            message_parts.append(f"{change_emoji} 24H{change_text}: <code>{change_24h:+.2f}%</code>")
        
        if risk_decline:
            message_parts.append(f"📉 风险跌幅: <code>-{risk_decline:.2f}%</code>")
        if rebound and rebound != 0:
            rebound_emoji = "📈" if rebound > 0 else "📉"
            message_parts.append(f"{rebound_emoji} 短期波动: <code>{rebound:+.2f}%</code>")
        
        if scoring:
            message_parts.append(f"🎯 AI评分: <b>{int(scoring)}</b>")
        
        message_parts.extend([
            f"",
            f"💡 风险提示:",
            f"   • ⚠️ <b>风险等级上升</b>",
            f"   • 📉 主力疑似大量减持",
            f"   • 💰 已持仓建议分批止盈",
            f"   • 🛑 不建议追高或接针",
            f"   • 👀 密切关注后续走势",
            f"",
            f"{tag}",
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])
    
    elif predict_type == 3:
        # 主力增持
        emoji = "💚"
        title = f"<b>AI机会监控</b>"
        tag = "#主力增持"

        message_parts = [
            f"{emoji} {title}",
            f"━━━━━━━━━",
            f"<b>${symbol}</b> 疑似主力增持，注意市场变化",
            f"${symbol} 疑似主力持仓增加，现报<b>${price}</b>，24H涨幅{change_24h:.2f}%，市场情绪乐观，但需注意高抛风险。",
            f"",
            f"🪙 <b>${symbol}</b>",
            f"💼 主力增持",
        ]

        if change_24h:
            change_emoji = "📈" if change_24h >= 0 else "📉"
            change_text = "涨幅" if change_24h >= 0 else "跌幅"
            message_parts.append(f"{change_emoji} 24H{change_text}: <code>{change_24h:+.2f}%</code>")

        if scoring:
            message_parts.append(f"🎯 AI评分: <b>{int(scoring)}</b>")

        message_parts.extend([
            f"",
            f"💡 操作建议:",
            f"   • 📊 市场情绪乐观",
            f"   • ✅ 可关注入场机会",
            f"   • ⚠️ 高位注意风险",
            f"   • 🎯 设置止盈止损",
            f"",
            f"{tag}",
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])

    elif predict_type == 28:
        # 主力增持加速（上涨机会）
        emoji = "🟢"
        title = f"<b>${symbol} 主力增持加速</b>"
        tag = "#主力增持加速"
        
        message_parts = [
            f"{emoji} {title}",
            f"━━━━━━━━━",
            f"✅ 疑似主力<b>大量买入</b>中",
            f"📈 可能有上涨行情",
            f"💵 现价: <b>${price}</b>",
        ]
        
        if change_24h:
            change_emoji = "📈" if change_24h >= 0 else "📉"
            change_text = "涨幅" if change_24h >= 0 else "跌幅"
            message_parts.append(f"{change_emoji} 24H{change_text}: <code>{change_24h:+.2f}%</code>")
        
        # 显示追踪期涨幅和跌幅
        if gains and gains > 0:
            message_parts.append(f"📈 追踪涨幅: <code>+{gains:.2f}%</code>")
        if content.get('decline', 0) > 0:
            decline = content.get('decline', 0)
            message_parts.append(f"📉 回调幅度: <code>-{decline:.2f}%</code>")
        
        if scoring:
            message_parts.append(f"🎯 AI评分: <b>{int(scoring)}</b>")
        
        message_parts.extend([
            f"",
            f"💡 操作建议:",
            f"   • 🚀 <b>市场情绪乐观</b>",
            f"   • 📊 可考虑适当参与",
            f"   • ⚠️ 注意控制仓位",
            f"   • 🎯 设置止盈止损位",
            f"   • 💰 高位注意分批减仓",
            f"",
            f"{tag}",
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])
    
    elif predict_type == 29:
        # 主力持仓减少加速
        emoji = "🚨"
        title = f"<b>${symbol} 主力加速减持</b>"
        tag = "#持仓减少加速"
        
        message_parts = [
            f"{emoji} {title}",
            f"━━━━━━━━━",
            f"⚠️ 疑似主力<b>大量抛售</b>，减持加速",
            f"💵 现价: <b>${price}</b>",
        ]
        
        if change_24h:
            change_emoji = "📈" if change_24h >= 0 else "📉"
            change_text = "涨幅" if change_24h >= 0 else "跌幅"
            message_parts.append(f"{change_emoji} 24H{change_text}: <code>{change_24h:+.2f}%</code>")
        
        if rebound and rebound != 0:
            rebound_emoji = "📈" if rebound > 0 else "📉"
            message_parts.append(f"{rebound_emoji} 短期波动: <code>{rebound:+.2f}%</code>")
        
        if scoring:
            message_parts.append(f"🎯 AI评分: <b>{int(scoring)}</b>")
        
        message_parts.extend([
            f"",
            f"💡 风险警示:",
            f"   • 🚨 <b>高风险！主力加速离场</b>",
            f"   • 📉 价格可能面临大幅下跌",
            f"   • 🛑 已持仓建议及时止损离场",
            f"   • ⛔ 不建议接针，等待企稳",
            f"",
            f"{tag}",
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])
    
    elif predict_type == 4:
        # 主力减持风险
        emoji = "⚠️"
        title = f"<b>${symbol} 疑似主力减持</b>"
        risk_desc = "主力持仓减少，注意市场风险"
        tag = "#主力减持"
        
        message_parts = [
            f"{emoji} {title}",
            f"━━━━━━━━━",
            f"📉 {risk_desc}",
            f"💵 现价: <b>${price}</b>",
            f"📊 24H: <code>{change_24h:+.2f}%</code>",
        ]
        
        if scoring:
            message_parts.append(f"🎯 AI评分: <b>{int(scoring)}</b>")
        
        message_parts.extend([
            f"",
            f"💡 操作建议:",
            f"   • 谨慎追高，等待企稳",
            f"   • 已持仓可考虑减仓观望",
            f"",
            f"{tag}",
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])
    
    elif predict_type == 16:
        # 追踪后涨幅超过20% - 上涨止盈
        emoji = "🎉"
        title = f"<b>${symbol} 上涨止盈信号</b>"
        gains_desc = f"AI追踪后上涨，涨幅已达 <b>{gains:.2f}%</b> 🚀"
        tag = "#上涨止盈"
        
        message_parts = [
            f"{emoji} {title}",
            f"━━━━━━━━━",
            f"✅ {gains_desc}",
            f"💵 现价: <b>${price}</b>",
            f"📈 24H涨幅: <code>+{change_24h:.2f}%</code>",
        ]
        
        if scoring:
            message_parts.append(f"🎯 AI评分: <b>{int(scoring)}</b>")
        
        message_parts.extend([
            f"",
            f"💡 操作建议:",
            f"   • <b>🎯 移动止盈，锁定利润</b>",
            f"   • 📊 可考虑分批止盈离场",
            f"   • 🛡️ 避免回吐过多收益",
            f"   • ⏰ 保持警惕，注意回调风险",
            f"",
            f"{tag}",
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])
    
    elif predict_type == 17:
        # 达到最大涨幅后回调止盈
        emoji = "🟡"
        title = f"<b>${symbol} 回调止盈信号</b>"
        decline = content.get('decline', 0)
        tag = "#回调止盈"
        
        message_parts = [
            f"{emoji} {title}",
            f"━━━━━━━━━",
            f"📈 AI追踪后最大涨幅: <b>+{gains:.2f}%</b>",
            f"📉 当前回调幅度: <b>-{decline:.2f}%</b>",
            f"💵 现价: <b>${price}</b>",
        ]
        
        if change_24h:
            change_emoji = "📈" if change_24h >= 0 else "📉"
            change_text = "涨幅" if change_24h >= 0 else "跌幅"
            message_parts.append(f"{change_emoji} 24H{change_text}: <code>{change_24h:+.2f}%</code>")
        
        if scoring:
            message_parts.append(f"🎯 AI评分: <b>{int(scoring)}</b>")
        
        message_parts.extend([
            f"",
            f"💡 操作建议:",
            f"   • ⚠️ <b>高点回调较大，注意保护利润</b>",
            f"   • 🎯 移动止盈，锁定剩余收益",
            f"   • 📊 可考虑分批止盈离场",
            f"   • 🛡️ 避免继续回吐更多利润",
            f"   • 📉 观察是否企稳或继续下跌",
            f"",
            f"{tag}",
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])
    
    elif predict_type == 19:
        # 追踪后跌幅超过15% - 下跌止盈
        emoji = "🔴"
        title = f"<b>${symbol} 下跌止盈信号</b>"
        risk_desc = f"AI追踪后下跌，跌幅已超过 {risk_decline:.2f}%"
        tag = "#下跌止盈"
        
        message_parts = [
            f"{emoji} {title}",
            f"━━━━━━━━━",
            f"⚠️ {risk_desc}",
            f"💵 现价: <b>${price}</b>",
            f"📉 风险跌幅: <code>-{risk_decline:.2f}%</code>",
        ]
        
        if rebound:
            message_parts.append(f"📈 反弹幅度: <code>{rebound:+.2f}%</code>")
        
        message_parts.extend([
            f"",
            f"💡 操作建议:",
            f"   • <b>移动止盈，保护利润</b>",
            f"   • 避免回吐过多收益",
            f"   • 等待新的入场机会",
            f"",
            f"{tag}",
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])
    
    elif predict_type == 30:
        # 追踪后涨幅5-20% - 保护本金（上涨中的提醒）
        emoji = "💚"
        title = f"<b>${symbol} 盈利保护提醒</b>"
        tag = "#保护本金"
        
        message_parts = [
            f"{emoji} {title}",
            f"━━━━━━━━━",
            f"✅ AI追踪后涨幅达 <b>{gains:.2f}%</b>",
            f"💵 现价: <b>${price}</b>",
        ]
        
        if change_24h:
            change_emoji = "📈" if change_24h >= 0 else "📉"
            change_text = "涨幅" if change_24h >= 0 else "跌幅"
            message_parts.append(f"{change_emoji} 24H{change_text}: <code>{change_24h:+.2f}%</code>")
        
        # 显示回调幅度
        if content.get('decline', 0) > 0:
            decline = content.get('decline', 0)
            message_parts.append(f"📉 回调幅度: <code>-{decline:.2f}%</code>")
        
        if scoring:
            message_parts.append(f"🎯 AI评分: <b>{int(scoring)}</b>")
        
        message_parts.extend([
            f"",
            f"💡 操作建议:",
            f"   • 💰 <b>已有盈利，注意保护本金</b>",
            f"   • 🎯 可设置跟踪止损保护利润",
            f"   • 📊 控制仓位，不要过度追高",
            f"   • ⚠️ 观察能否突破继续上涨",
            f"   • 🛡️ 如回调加大，及时止盈",
            f"",
            f"{tag}",
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])
    
    elif predict_type == 31:
        # 追踪后跌幅5-15% - 保护本金（下跌中的警示）
        emoji = "🟠"
        title = f"<b>${symbol} 本金保护警示</b>"
        risk_desc = f"AI追踪后下跌，跌幅已达 {risk_decline:.2f}%"
        tag = "#保护本金"
        
        message_parts = [
            f"{emoji} {title}",
            f"━━━━━━━━━",
            f"⚠️ {risk_desc}",
            f"💵 现价: <b>${price}</b>",
            f"📉 风险跌幅: <code>-{risk_decline:.2f}%</code>",
        ]
        
        if scoring:
            message_parts.append(f"🎯 AI评分: <b>{int(scoring)}</b>")
        if rebound:
            message_parts.append(f"📈 反弹幅度: <code>{rebound:+.2f}%</code>")
        
        message_parts.extend([
            f"",
            f"💡 操作建议:",
            f"   • <b>注意保护本金</b>",
            f"   • 设置止损位，控制风险",
            f"   • 观察是否企稳反弹",
            f"",
            f"{tag}",
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])
    
    elif predict_type == 8:
        # 下跌趋势减弱，追踪结束
        emoji = "🟢"
        title = f"<b>${symbol} 趋势转变</b>"
        tag = "#追踪结束"

        message_parts = [
            f"{emoji} {title}",
            f"━━━━━━━━━",
            f"📊 价格下跌趋势减弱",
            f"🤖 AI实时追踪已结束",
            f"💵 现价: <b>${price}</b>",
        ]

        if change_24h:
            change_emoji = "📈" if change_24h >= 0 else "📉"
            change_text = "涨幅" if change_24h >= 0 else "跌幅"
            message_parts.append(f"{change_emoji} 24H{change_text}: <code>{change_24h:+.2f}%</code>")

        if risk_decline:
            message_parts.append(f"📉 追踪期跌幅: <code>-{risk_decline:.2f}%</code>")
        if rebound:
            message_parts.append(f"📈 反弹幅度: <code>+{rebound:.2f}%</code>")

        if scoring:
            message_parts.append(f"🎯 AI评分: <b>{int(scoring)}</b>")

        message_parts.extend([
            f"",
            f"💡 提示:",
            f"   • ✅ 下跌趋势有所缓解",
            f"   • 📊 关注是否企稳反弹",
            f"   • ⏰ 可观察后续走势再决策",
            f"   • ⚠️ 仍需注意市场风险",
            f"",
            f"{tag}",
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])

    elif predict_type == 1:
        # 主力出货
        emoji = "🔵"
        title = f"<b>${symbol} 主力出货</b>"
        tag = "#主力出货"

        message_parts = [
            f"{emoji} {title}",
            f"━━━━━━━━━",
            f"📊 检测到主力出货信号",
            f"💵 现价: <b>${price}</b>",
        ]

        if change_24h:
            change_emoji = "📈" if change_24h >= 0 else "📉"
            change_text = "涨幅" if change_24h >= 0 else "跌幅"
            message_parts.append(f"{change_emoji} 24H{change_text}: <code>{change_24h:+.2f}%</code>")

        if scoring:
            message_parts.append(f"🎯 AI评分: <b>{int(scoring)}</b>")

        message_parts.extend([
            f"",
            f"💡 操作建议:",
            f"   • ⚠️ 主力可能在出货",
            f"   • 📉 注意市场风险",
            f"   • 🛑 谨慎追高",
            f"",
            f"{tag}",
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])

    elif predict_type in [6, 18]:
        # AI 追踪结束（退出机会）
        emoji = "🔔"
        title = f"<b>${symbol} AI追踪结束</b>"
        tag = "#追踪结束"

        message_parts = [
            f"{emoji} {title}",
            f"━━━━━━━━━",
            f"🤖 AI实时追踪已结束",
            f"⚠️ 注意市场风险",
            f"💵 现价: <b>${price}</b>",
        ]

        if change_24h:
            change_emoji = "📈" if change_24h >= 0 else "📉"
            change_text = "涨幅" if change_24h >= 0 else "跌幅"
            message_parts.append(f"{change_emoji} 24H{change_text}: <code>{change_24h:+.2f}%</code>")

        if scoring:
            message_parts.append(f"🎯 AI评分: <b>{int(scoring)}</b>")

        # 显示追踪期间的最大涨幅（如果有）
        if gains and gains > 0:
            message_parts.append(f"📈 追踪期最大涨幅: <code>+{gains:.2f}%</code>")

        message_parts.extend([
            f"",
            f"💡 提示:",
            f"   • 🔔 AI监控已结束",
            f"   • 📊 建议关注后续走势",
            f"   • ⚠️ 如有持仓需自行评估风险",
            f"",
            f"{tag}",
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])

    elif predict_type in [22, 23]:
        # 追踪下跌后反弹
        emoji = "🟡"
        title = f"<b>${symbol} 下跌后反弹</b>"
        tag = "#下跌反弹"

        message_parts = [
            f"{emoji} {title}",
            f"━━━━━━━━━",
        ]

        if risk_decline:
            message_parts.append(f"📉 下跌幅度: <code>-{risk_decline:.2f}%</code>")
        if rebound:
            message_parts.append(f"📈 反弹幅度: <code>+{rebound:.2f}%</code>")

        message_parts.append(f"💵 现价: <b>${price}</b>")

        if change_24h:
            change_emoji = "📈" if change_24h >= 0 else "📉"
            change_text = "涨幅" if change_24h >= 0 else "跌幅"
            message_parts.append(f"{change_emoji} 24H{change_text}: <code>{change_24h:+.2f}%</code>")

        if scoring:
            message_parts.append(f"🎯 AI评分: <b>{int(scoring)}</b>")

        message_parts.extend([
            f"",
            f"💡 操作建议:",
            f"   • 📊 触底后出现反弹",
            f"   • ⚠️ 观察反弹是否持续",
            f"   • 🎯 可考虑移动止盈保护利润",
            f"   • 📉 注意二次探底风险",
            f"",
            f"{tag}",
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])

    elif predict_type in [25, 27]:
        # 资金异动（24H内/24H外）
        emoji = "💰"
        time_frame = "24H内" if predict_type == 25 else "24H外"
        title = f"<b>${symbol} {time_frame}资金异动</b>"
        tag = f"#{time_frame}资金异动"

        message_parts = [
            f"{emoji} {title}",
            f"━━━━━━━━━",
            f"💼 检测到{time_frame}出现资金异常流动",
            f"💵 现价: <b>${price}</b>",
        ]

        if change_24h:
            change_emoji = "📈" if change_24h >= 0 else "📉"
            change_text = "涨幅" if change_24h >= 0 else "跌幅"
            message_parts.append(f"{change_emoji} 24H{change_text}: <code>{change_24h:+.2f}%</code>")

        if scoring:
            message_parts.append(f"🎯 AI评分: <b>{int(scoring)}</b>")

        message_parts.extend([
            f"",
            f"💡 操作建议:",
            f"   • 💰 资金活跃度提升",
            f"   • 📊 关注市场行情变化",
            f"   • ⚠️ 注意风险管控",
            f"",
            f"{tag}",
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])

    else:
        # AI追踪结束 - 通用格式
        emoji = "🔔"
        title = f"<b>${symbol} AI追踪结束</b>"
        tag = "#追踪结束"
        
        message_parts = [
            f"{emoji} {title}",
            f"━━━━━━━━━",
            f"🤖 AI实时追踪已结束",
            f"💵 现价: <b>${price}</b>",
        ]
        
        # 根据涨跌显示不同提示
        if change_24h:
            change_emoji = "📈" if change_24h > 0 else "📉"
            message_parts.append(f"{change_emoji} 24H: <code>{change_24h:+.2f}%</code>")
        
        if scoring:
            message_parts.append(f"🎯 AI评分: <b>{int(scoring)}</b>")
        
        if risk_decline:
            message_parts.append(f"📉 追踪期跌幅: <code>-{risk_decline:.2f}%</code>")
        if rebound:
            message_parts.append(f"📈 反弹幅度: <code>{rebound:+.2f}%</code>")
        
        message_parts.extend([
            f"",
            f"💡 提示:",
            f"   • AI追踪监控已结束",
            f"   • 建议关注后续走势变化",
            f"   • 如有持仓请自行评估风险",
            f"",
            f"{tag}",
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])
    
    return "\n".join(message_parts)


def _format_general_message(item, content, msg_type, msg_type_name):
    """
    格式化通用消息（资金异动、Alpha等）
    特别优化 type 111（资金出逃）的提示
    """
    from message_types import TRADE_TYPE_MAP, FUNDS_MOVEMENT_MAP
    
    symbol = content.get('symbol', 'N/A')
    price = content.get('price', 'N/A')
    change_24h = content.get('percentChange24h', 0)
    funds_type = content.get('fundsMovementType', 0)
    
    # Type 114 资金异常 - 特殊格式（包含追踪涨幅信息）
    if msg_type == 114:
        emoji = "💎"
        funds_text = FUNDS_MOVEMENT_MAP.get(funds_type, 'N/A')
        
        # 从 extField 中提取涨幅信息
        ext_field = content.get('extField', {})
        gains = ext_field.get('gains', 0) if isinstance(ext_field, dict) else 0
        
        # 根据涨幅判断消息类型
        if gains > 0:
            # 有涨幅数据 - 上涨止盈提示
            if gains >= 50:
                emoji = "🎉"
                title = f"<b>${symbol} 大幅上涨止盈</b>"
                tag = "#上涨止盈"
            elif gains >= 20:
                emoji = "🎊"
                title = f"<b>${symbol} 上涨止盈</b>"
                tag = "#上涨止盈"
            else:
                emoji = "💰"
                title = f"<b>${symbol} 资金异常</b>"
                tag = "#资金异常"
            
            message_parts = [
                f"{emoji} {title}",
                f"━━━━━━━━━",
            ]
            
            if gains >= 20:
                message_parts.append(f"✅ AI追踪后涨幅达 <b>{gains:.2f}%</b> 🚀")
            
            message_parts.extend([
                f"💼 资金类型: {funds_text}",
                f"💵 现价: <b>${price}</b>",
            ])
            
            if change_24h:
                change_emoji = "📈" if change_24h >= 0 else "📉"
                change_text = "涨幅" if change_24h >= 0 else "跌幅"
                message_parts.append(f"{change_emoji} 24H{change_text}: <code>{change_24h:+.2f}%</code>")
            
            if 'tradeType' in content:
                trade_type = content.get('tradeType')
                trade_text = TRADE_TYPE_MAP.get(trade_type, 'N/A')
                message_parts.append(f"📊 类型: {trade_text}")
            
            # 根据涨幅给出不同建议
            if gains >= 20:
                message_parts.extend([
                    f"",
                    f"💡 操作建议:",
                    f"   • 🎯 <b>移动止盈，锁定利润</b>",
                    f"   • 📊 可考虑分批止盈离场",
                    f"   • 🛡️ 避免回吐过多收益",
                ])
            
            message_parts.extend([
                f"",
                f"{tag}",
                f"━━━━━━━━━",
                f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
            ])
        else:
            # 没有涨幅数据 - 普通资金异常
            title = f"<b>${symbol} 资金异常</b>"
            tag = "#资金异常"
            
            message_parts = [
                f"{emoji} {title}",
                f"━━━━━━━━━",
                f"💼 资金类型: {funds_text}",
                f"💵 现价: <b>${price}</b>",
            ]
            
            if change_24h:
                change_emoji = "📈" if change_24h >= 0 else "📉"
                message_parts.append(f"{change_emoji} 24H: <code>{change_24h:+.2f}%</code>")
            
            if 'tradeType' in content:
                trade_type = content.get('tradeType')
                trade_text = TRADE_TYPE_MAP.get(trade_type, 'N/A')
                message_parts.append(f"📊 类型: {trade_text}")
            
            message_parts.extend([
                f"",
                f"{tag}",
                f"━━━━━━━━━",
                f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
            ])
        
        return "\n".join(message_parts)
    
    # Type 112 FOMO加剧 - 特殊格式（风险信号，注意止盈）
    elif msg_type == 112:
        emoji = "🔥"
        title = f"<b>${symbol} FOMO 情绪加剧</b>"
        funds_text = FUNDS_MOVEMENT_MAP.get(funds_type, 'N/A')
        tag = "#FOMO加剧"

        message_parts = [
            f"{emoji} {title}",
            f"━━━━━━━━━",
            f"⚠️ <b>市场情绪过热，注意止盈</b>",
            f"🌡️ FOMO 情绪达到高位，防范突发回调风险",
            f"💵 现价: <b>${price}</b>",
        ]

        if change_24h:
            change_emoji = "📈" if change_24h >= 0 else "📉"
            change_text = "涨幅" if change_24h >= 0 else "跌幅"
            message_parts.append(f"{change_emoji} 24H{change_text}: <code>{change_24h:+.2f}%</code>")

            # 如果涨幅较大，额外强调风险
            if change_24h > 15:
                message_parts.append(f"🔥 短期涨幅较大，回调风险显著增加")
            elif change_24h > 10:
                message_parts.append(f"⚠️ 短期涨幅偏大，注意获利了结")

        if 'tradeType' in content:
            trade_type = content.get('tradeType')
            trade_text = TRADE_TYPE_MAP.get(trade_type, 'N/A')
            message_parts.append(f"📊 类型: {trade_text}")

        if funds_type:
            message_parts.append(f"💼 资金状态: {funds_text}")

        message_parts.extend([
            f"",
            f"💡 风险提示:",
            f"   • 🔥 <b>FOMO 情绪过热（风险信号）</b>",
            f"   • 📉 市场可能面临突发回调",
            f"   • 💰 <b>已持仓建议分批止盈</b>",
            f"   • 🛑 <b>不建议追高买入</b>",
            f"   • 🎯 可设置移动止损保护利润",
            f"   • ⏰ 密切关注价格走势变化",
            f"",
            f"{tag}",
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])

        return "\n".join(message_parts)

    # Type 111 资金出逃 - 特殊格式
    elif msg_type == 111:
        emoji = "🚨"
        title = f"<b>${symbol} 主力资金已出逃</b>"
        funds_text = FUNDS_MOVEMENT_MAP.get(funds_type, 'N/A')
        tag = "#追踪结束"

        message_parts = [
            f"{emoji} {title}",
            f"━━━━━━━━━",
            f"⚠️ 资金异动实时追踪结束",
            f"💼 疑似主力资金已出逃，资金异动监控结束",
            f"💵 现价: <b>${price}</b>",
        ]

        if change_24h:
            change_emoji = "📈" if change_24h >= 0 else "📉"
            change_text = "涨幅" if change_24h >= 0 else "跌幅"
            message_parts.append(f"{change_emoji} 24H{change_text}: <code>{change_24h:+.2f}%</code>")

        if 'tradeType' in content:
            trade_type = content.get('tradeType')
            trade_text = TRADE_TYPE_MAP.get(trade_type, 'N/A')
            message_parts.append(f"📊 资金类型: {trade_text}")

        message_parts.extend([
            f"",
            f"💡 风险提示:",
            f"   • 🚨 <b>主力资金疑似已撤离</b>",
            f"   • 📉 <b>注意市场风险</b>",
            f"   • 💰 已持仓建议及时止盈/止损",
            f"   • 🛑 观望为主，等待企稳信号",
            f"   • 👀 资金追踪已停止",
            f"",
            f"{tag}",
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])

        return "\n".join(message_parts)
    
    # Type 110 Alpha - 优化格式
    elif msg_type == 110:
        emoji = "⭐"
        funds_text = FUNDS_MOVEMENT_MAP.get(funds_type, 'N/A')
        
        message_parts = [
            f"{emoji} <b>【Alpha】${symbol}</b>",
            f"━━━━━━━━━",
            f"💰 资金状态: {funds_text}",
            f"💵 现价: <b>${price}</b>",
        ]
        
        if change_24h:
            change_emoji = "📈" if change_24h > 0 else "📉"
            message_parts.append(f"{change_emoji} 24H: <code>{change_24h:+.2f}%</code>")
        
        if 'tradeType' in content:
            trade_type = content.get('tradeType')
            trade_text = TRADE_TYPE_MAP.get(trade_type, 'N/A')
            message_parts.append(f"📊 类型: {trade_text}")
        
        message_parts.extend([
            f"",
            f"💡 潜力标的，可关注后续表现",
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])
        
        return "\n".join(message_parts)
    
    # Type 108 资金异动
    elif msg_type == 108:
        emoji = "💰"
        funds_text = FUNDS_MOVEMENT_MAP.get(funds_type, 'N/A')
        
        message_parts = [
            f"{emoji} <b>【资金异动】${symbol}</b>",
            f"━━━━━━━━━",
            f"💼 资金流向: {funds_text}",
            f"💵 现价: <b>${price}</b>",
        ]
        
        if change_24h:
            change_emoji = "📈" if change_24h > 0 else "📉"
            message_parts.append(f"{change_emoji} 24H: <code>{change_24h:+.2f}%</code>")
        
        if 'tradeType' in content:
            trade_type = content.get('tradeType')
            trade_text = TRADE_TYPE_MAP.get(trade_type, 'N/A')
            message_parts.append(f"📊 类型: {trade_text}")
        
        message_parts.extend([
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])
        
        return "\n".join(message_parts)
    
    # 其他类型 - 通用格式
    else:
        type_emoji_map = {
            109: "📢",  # 上下币公告
            113: "🚀"   # FOMO
        }
        emoji = type_emoji_map.get(msg_type, "📋")
        
        message_parts = [
            f"{emoji} <b>【{msg_type_name}】${symbol}</b>",
            f"━━━━━━━━━",
        ]
        
        if price:
            message_parts.append(f"💵 现价: <b>${price}</b>")
        
        if change_24h:
            change_emoji = "📈" if change_24h > 0 else "📉"
            message_parts.append(f"{change_emoji} 24H: <code>{change_24h:+.2f}%</code>")
        
        if 'tradeType' in content:
            trade_type = content.get('tradeType')
            trade_text = TRADE_TYPE_MAP.get(trade_type, 'N/A')
            message_parts.append(f"📊 类型: {trade_text}")
        
        if 'fundsMovementType' in content and funds_type:
            funds_text = FUNDS_MOVEMENT_MAP.get(funds_type, 'N/A')
            message_parts.append(f"💼 资金: {funds_text}")
        
        if 'source' in content:
            message_parts.append(f"📰 来源: {content.get('source', 'N/A')}")
        
        if 'titleSimplified' in content:
            message_parts.append(f"")
            message_parts.append(f"💬 {content.get('titleSimplified', 'N/A')}")

        message_parts.extend([
            f"━━━━━━━━━",
            f"🕐 {get_beijing_time_str(item.get('createTime', 0))}"
        ])

        return "\n".join(message_parts)


def format_confluence_message(symbol, price, alpha_count, fomo_count):
    """
    格式化融合信号消息（Alpha + FOMO）

    Args:
        symbol: 币种符号
        price: 当前价格
        alpha_count: Alpha 信号数量
        fomo_count: FOMO 信号数量

    Returns:
        str: 格式化后的 HTML 消息文本
    """
    from datetime import datetime, timezone, timedelta

    # 北京时区
    BEIJING_TZ = timezone(timedelta(hours=8))
    now = datetime.now(tz=BEIJING_TZ)
    time_str = now.strftime('%H:%M:%S') + ' (UTC+8)'

    # 获取币安Alpha标识
    binance_alpha_badge = _get_binance_alpha_badge(symbol)

    emoji = "🚨"
    title = f"<b>【Alpha + FOMO】${symbol}</b> {binance_alpha_badge}"
    tag = "#Alpha + FOMO"

    message_parts = [
        f"{emoji} {title}",
        f"━━━━━━━━━",
        f"🔥 <b>检测到 Alpha + FOMO 信号！</b>",
        f"⚡ 在2小时内同时出现 Alpha 和 FOMO 信号",
        f"",
        f"💵 当前价格: <b>${price}</b>",
        f"⭐ Alpha 信号: <b>{alpha_count}</b> 条",
        f"🚀 FOMO 信号: <b>{fomo_count}</b> 条",
        f"",
        f"💡 操作建议:",
        f"   • 🎯 <b>高概率入场机会</b>",
        f"   • 📊 Alpha（价值机会）+ FOMO（市场情绪）",
        f"   • ✅ 可考虑适当参与",
        f"   • ⚠️ 注意控制仓位和风险",
        f"   • 🎯 及时设置止盈止损位",
        f"",
        f"{tag}",
        f"━━━━━━━━━",
        f"🕐 {time_str}"
    ]

    return "\n".join(message_parts)


def send_confluence_alert(symbol, price, alpha_count, fomo_count):
    """
    发送融合信号提醒（先发送文字消息，异步生成图表后编辑消息添加图片）

    Args:
        symbol: 币种符号
        price: 当前价格
        alpha_count: Alpha 信号数量
        fomo_count: FOMO 信号数量

    Returns:
        bool: 发送成功返回 True，否则返回 False
    """
    logger.info(f"Confluence signal prepared: ${symbol}")

    # 格式化融合信号消息
    message = format_confluence_message(symbol, price, alpha_count, fomo_count)

    # 先立即发送文字消息（包含Binance合约链接）
    logger.info(f"Sending confluence message: ${symbol}")
    text_result = send_telegram_message(message, pin_message=True, symbol=symbol)
    
    if not text_result or not text_result.get("success"):
        logger.error(f"Confluence message failed: ${symbol}")
        return False

    message_id = text_result.get("message_id")
    if not message_id:
        logger.warning(f"Confluence message missing ID: ${symbol}")
        return True  # 文字消息已发送成功

    # 检查是否启用图表生成
    try:
        import config as signal_config
        enable_chart = getattr(signal_config, "ENABLE_TRADINGVIEW_CHART", True)
    except Exception:
        enable_chart = True

    if enable_chart:
        try:
            if _is_metal_symbol(symbol):
                from metals_chart_generator import generate_metals_chart_async
                generate_async = generate_metals_chart_async
            else:
                from chart_generator import generate_tradingview_chart_async
                generate_async = generate_tradingview_chart_async
            
            # 异步生成图表的回调函数
            def chart_ready_callback(task_id, symbol, chart_data):
                """图表生成完成后的回调 - 编辑已发送的消息添加图片"""
                try:
                    if not chart_data:
                        fallback = _generate_metals_chart(symbol) if _is_metal_symbol(symbol) else _generate_snapshot_chart(symbol)
                        if fallback:
                            chart_data = fallback
                    if chart_data:
                        # 添加小幅随机延迟避免多个编辑请求冲突
                        import random
                        delay = random.uniform(0.5, 2.0)  # 0.5-2秒随机延迟
                        logger.info(f"Waiting {delay:.1f}s before attaching chart: ${symbol} (ID: {task_id})")
                        time.sleep(delay)
                        
                        # 编辑已发送的消息，将其替换为图片消息
                        edit_result = edit_message_with_photo(
                            message_id,
                            chart_data, 
                            caption=message  # 使用完整的融合信号文字作为图片说明
                        )
                        if edit_result:
                            logger.info(f"Chart attached to confluence message: ${symbol}")
                        else:
                            logger.warning(f"Chart attach failed for confluence message: ${symbol}")
                    else:
                        logger.warning(f"No chart data for confluence message: ${symbol}")
                except Exception as e:
                    logger.error(f"  Chart callback error: {e}")
            
            # 提交异步图表生成任务
            task_id = generate_async(symbol, callback=chart_ready_callback)
            logger.info(f"  Async chart task queued: ${symbol} (ID: {task_id})")
            
        except Exception as e:
            logger.warning(f"  Async chart start failed: {e}")

    return True


def edit_message_caption(message_id, caption=None):
    """
    ???????????????HTML???

    Args:
        message_id: ??????ID
        caption: ????????

    Returns:
        bool: ???? True??? False
    """
    if not ENABLE_TELEGRAM:
        logger.info("  Telegram notifications disabled; skip edit caption.")
        return True

    if not TELEGRAM_BOT_TOKEN:
        logger.warning("  Telegram bot token missing; skip edit caption.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageCaption"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "message_id": message_id,
    }
    if caption:
        data["caption"] = caption
        data["parse_mode"] = "HTML"

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = _post_telegram(url, data=data, timeout=30)
        except Exception as e:
            logger.error(f"  Telegram edit caption error: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 + attempt * 2)
                continue
            return False

        if response.status_code == 200:
            logger.info(f"  Telegram caption updated (ID: {message_id})")
            return True
        if response.status_code == 429 and attempt < max_retries - 1:
            try:
                retry_after = response.json().get("parameters", {}).get("retry_after", 5)
            except Exception:
                retry_after = 5
            logger.warning(f"  Telegram rate limit, retry in {retry_after}s")
            time.sleep(retry_after + 1)
            continue
        logger.error(f"  Telegram caption update failed: {response.status_code} - {response.text}")
        if attempt < max_retries - 1 and response.status_code >= 500:
            time.sleep(2 + attempt * 2)
            continue
        return False
    return False


def edit_message_text(message_id, text, parse_mode="HTML"):
    """
    Edit a text-only Telegram message.

    Args:
        message_id: Message ID to edit
        text: New text
        parse_mode: Parse mode (HTML/Markdown/None)
    """
    if not ENABLE_TELEGRAM:
        logger.info("  Telegram notifications disabled; skip edit text.")
        return True

    if not TELEGRAM_BOT_TOKEN:
        logger.warning("  Telegram bot token missing; skip edit text.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "message_id": message_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = _post_telegram(url, json=payload, timeout=20)
        except Exception as e:
            logger.error(f"  Telegram edit text error: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 + attempt * 2)
                continue
            return False

        if response.status_code == 200:
            logger.info(f"  Telegram text updated (ID: {message_id})")
            return True
        if response.status_code == 429 and attempt < max_retries - 1:
            try:
                retry_after = response.json().get("parameters", {}).get("retry_after", 5)
            except Exception:
                retry_after = 5
            logger.warning(f"  Telegram rate limit, retry in {retry_after}s")
            time.sleep(retry_after + 1)
            continue
        logger.error(f"  Telegram text update failed: {response.status_code} - {response.text}")
        if attempt < max_retries - 1 and response.status_code >= 500:
            time.sleep(2 + attempt * 2)
            continue
        return False
    return False


def send_message_with_async_chart(message_text, symbol, pin_message=False, signal_payload=None):
    """
    ???? Pro ???? AI ???????????
    Args:
        message_text: ??????
        symbol: ??
        pin_message: ????
    Returns:
        dict: ????
    """
    logger.info(f"[Telegram] Starting async signal: ${symbol}")

    # 1. ???????
    text_result = send_telegram_message(message_text, pin_message=pin_message, symbol=symbol)

    if not text_result or not text_result.get("success"):
        logger.error(f"[Telegram] Text send failed: ${symbol}")
        return text_result

    message_id = text_result.get("message_id")
    if not message_id:
        logger.warning(f"[Telegram] Missing message ID: ${symbol}")
        return text_result

    state = {
        "analysis": None,
        "levels": [],
        "supports": [],
        "resistances": [],
        "stop_loss": None,
        "take_profit": None,
        "rr": None,
        "entry_decision": None,
        "direction": None,
        "chart_uploaded": False,
        "lock": threading.Lock(),
    }
    caption_limit = int(os.getenv("NOFX_TG_CAPTION_LIMIT", "1024") or 1024)
    text_limit = int(os.getenv("NOFX_TG_TEXT_LIMIT", "4096") or 4096)

    def _sanitize_caption(text):
        if not text:
            return ""
        return text.replace("<", "?").replace(">", "?")

    def _truncate_telegram_text(text, limit):
        if not text:
            return ""
        if len(text) <= limit:
            return text
        if limit <= 3:
            return text[:limit]
        return f"{text[:limit - 3]}..."


    def _build_caption():
        return _sanitize_caption(message_text)

    def _build_analysis_text():
        with state["lock"]:
            analysis = state["analysis"]
            levels = state["levels"]
            supports = state["supports"]
            resistances = state["resistances"]
            stop_loss = state["stop_loss"]
            take_profit = state["take_profit"]
            rr = state["rr"]
            entry_decision = state["entry_decision"]
            direction = state["direction"]
        if not analysis:
            return ""
        analysis = _sanitize_caption(analysis)
        label = "AI\u7b80\u8bc4" if LANGUAGE == "zh" else "AI Brief"
        lines = [f"{label}: {analysis}"]
        if levels:
            level_txt = ", ".join(f"{v:,.4f}" for v in levels[:7])
            if LANGUAGE == "zh":
                lines.append(f"主力位: {level_txt}")
            else:
                lines.append(f"Main Force Levels: {level_txt}")
        elif supports or resistances:
            sup_txt = ", ".join(f"{v:,.4f}" for v in supports[:3]) if supports else "N/A"
            res_txt = ", ".join(f"{v:,.4f}" for v in resistances[:3]) if resistances else "N/A"
            if LANGUAGE == "zh":
                lines.append(f"主力位: S {sup_txt} | R {res_txt}")
            else:
                lines.append(f"Key Levels: S {sup_txt} | R {res_txt}")
        if stop_loss and take_profit:
            rr_txt = f"{rr:.2f}" if isinstance(rr, (int, float)) else "N/A"
            if LANGUAGE == "zh":
                lines.append(f"止损: {stop_loss:,.4f} | 止盈: {take_profit:,.4f} | 盈亏比: {rr_txt}")
            else:
                lines.append(f"SL: {stop_loss:,.4f} | TP: {take_profit:,.4f} | R/R: {rr_txt}")
        if _is_metal_symbol(symbol) and LANGUAGE == "zh":
            if entry_decision == "yes":
                if direction == "long":
                    hint = "偏多参与，严格止损止盈，RR≥2"
                elif direction == "short":
                    hint = "偏空参与，严格止损止盈，RR≥2"
                else:
                    hint = "顺势参与，严格止损止盈，RR≥2"
            else:
                hint = "观望为主，等待更清晰的结构与宏观共振"
            lines.append(f"操作建议: {hint}")
        return "\n".join(lines)

    def _build_caption_with_analysis():
        base = _build_caption()
        analysis_text = _build_analysis_text()
        if not analysis_text:
            return base
        if not base:
            return analysis_text
        return f"{base}\n\n{analysis_text}"



    def start_ai_analysis():
        def run_ai_analysis():
            for attempt in range(1, _AI_ANALYSIS_MAX_RETRIES + 1):
                try:
                    logger.info(
                        f"[Telegram] 启动 AI 信号分析: {symbol} (attempt {attempt}/{_AI_ANALYSIS_MAX_RETRIES})"
                    )
                    try:
                        from ai_signal_analysis import analyze_signal
                    except Exception as exc:
                        logger.warning(f"[Telegram] AI analysis import failed: {exc}")
                        return
                    result = analyze_signal(symbol, signal_payload=signal_payload)
                    if not result:
                        logger.info(f"[Telegram] AI analysis empty: {symbol}, retrying once...")
                        time.sleep(2)
                        result = analyze_signal(symbol, signal_payload=signal_payload)
                    if not result:
                        logger.info(f"[Telegram] AI analysis empty: {symbol}")
                        if attempt < _AI_ANALYSIS_MAX_RETRIES:
                            time.sleep(_AI_ANALYSIS_RETRY_DELAY)
                            continue
                        return
                    analysis = result.get("analysis") if isinstance(result, dict) else str(result)
                    analysis = " ".join(str(analysis).split())
                    logger.info(f"[Telegram] AI result: {analysis[:60]}...")
                    # NOFX API已移除
                    vs_levels = None

                    ai_levels = None
                    has_vs_levels = False
                    if vs_levels and isinstance(vs_levels, dict):
                        has_vs_levels = bool(
                            vs_levels.get("levels") or vs_levels.get("supports") or vs_levels.get("resistances")
                        )
                    if not has_vs_levels:
                        try:
                            from ai_key_levels_cache import get_levels as _get_ai_levels
                        except Exception:
                            try:
                                from signal_monitor.ai_key_levels_cache import get_levels as _get_ai_levels
                            except Exception:
                                _get_ai_levels = None  # type: ignore[assignment]
                        if _get_ai_levels:
                            ai_levels = _get_ai_levels(symbol)
                        if not ai_levels:
                            try:
                                from ai_signal_analysis import generate_ai_key_levels
                            except Exception:
                                from signal_monitor.ai_signal_analysis import generate_ai_key_levels
                            ai_levels = generate_ai_key_levels(symbol)

                    with state["lock"]:
                        state["analysis"] = analysis
                        if has_vs_levels:
                            state["levels"] = vs_levels.get("levels") or []
                            state["supports"] = vs_levels.get("supports") or []
                            state["resistances"] = vs_levels.get("resistances") or []
                        elif ai_levels:
                            supports = ai_levels.get("supports") or []
                            resistances = ai_levels.get("resistances") or []
                            state["supports"] = supports
                            state["resistances"] = resistances
                            state["levels"] = supports + resistances
                        else:
                            state["levels"] = []
                            state["supports"] = []
                            state["resistances"] = []
                        state["stop_loss"] = result.get("stop_loss") if isinstance(result, dict) else None
                        state["take_profit"] = result.get("take_profit") if isinstance(result, dict) else None
                        state["rr"] = result.get("rr") if isinstance(result, dict) else None
                        state["entry_decision"] = result.get("entry_decision") if isinstance(result, dict) else None
                        state["direction"] = result.get("direction") if isinstance(result, dict) else None
                        chart_uploaded = state["chart_uploaded"]
                    caption_text = _build_caption_with_analysis()
                    analysis_text = _build_analysis_text()
                    analysis_overflow = bool(analysis_text) and len(caption_text) > caption_limit
                    if chart_uploaded:
                        logger.info("[Telegram] Updating caption with AI analysis...")
                        if analysis_overflow:
                            caption_text = _truncate_telegram_text(_build_caption(), caption_limit)
                        ok = edit_message_caption(message_id, caption_text)
                        if (not ok or analysis_overflow) and analysis_text:
                            send_telegram_message(
                                analysis_text,
                                parse_mode=None,
                                reply_to_message_id=message_id,
                            )
                    else:
                        logger.info("[Telegram] Updating text with AI analysis...")
                        ok = False
                        if len(caption_text) <= text_limit:
                            ok = edit_message_text(message_id, caption_text)
                        if (not ok or len(caption_text) > text_limit) and analysis_text:
                            send_telegram_message(
                                analysis_text,
                                parse_mode=None,
                                reply_to_message_id=message_id,
                            )
                    return
                except Exception as e:
                    if attempt < _AI_ANALYSIS_MAX_RETRIES:
                        logger.warning(
                            f"[Telegram] AI 分析失败: {e} (retrying in {_AI_ANALYSIS_RETRY_DELAY}s)"
                        )
                        time.sleep(_AI_ANALYSIS_RETRY_DELAY)
                        continue
                    logger.warning(f"[Telegram] AI analysis failed: {e}")

        _ensure_async_workers()
        if not _enqueue_task(_AI_ANALYSIS_QUEUE, "AI Analysis", run_ai_analysis):
            run_ai_analysis()

    # 2. ???? Pro ??
    try:
        import config as signal_config
        enable_pro_chart = getattr(signal_config, "ENABLE_PRO_CHART", True)
    except Exception:
        enable_pro_chart = True

    # 3. ?????????
    if enable_pro_chart:
        def generate_and_edit_chart():
            for attempt in range(1, _CHART_MAX_RETRIES + 1):
                alarm_active = False
                try:
                    from chart_pro_v10 import generate_chart_v10
                    from ai_key_levels_cache import wait_for_levels
                    logger.info(f"[Telegram] Pro chart start: ${symbol} (attempt {attempt}/{_CHART_MAX_RETRIES})")



                    import signal

                    def timeout_handler(signum, frame):
                        raise TimeoutError(f"Chart generation exceeded 30s: ${symbol}")

                    try:
                        signal.signal(signal.SIGALRM, timeout_handler)
                        signal.alarm(30)
                        alarm_active = True
                    except Exception:
                        alarm_active = False

                    try:
                        from ai_key_levels_config import get_ai_levels_config
                        wait_enabled = get_ai_levels_config().get("enabled", False)
                    except Exception:
                        wait_enabled = False
                    if wait_enabled:
                        wait_for_levels(symbol, timeout_sec=8, poll_sec=0.3)
                    with _PRO_CHART_LOCK:
                        if _is_metal_symbol(symbol):
                            chart_data = _generate_metals_chart(symbol)
                        else:
                            chart_data = generate_chart_v10(symbol, "1h", 200)
                            if not chart_data:
                                chart_data = _generate_snapshot_chart(symbol)

                    if chart_data:
                        logger.info(f"[Telegram] Pro chart generated: {len(chart_data)} bytes, ${symbol}")
                        analysis_text = _build_analysis_text()
                        full_caption = _build_caption_with_analysis()
                        analysis_overflow = bool(analysis_text) and len(full_caption) > caption_limit
                        caption_text = full_caption
                        if caption_text and len(caption_text) > caption_limit:
                            caption_text = _truncate_telegram_text(_build_caption(), caption_limit)
                        edit_result = edit_message_with_photo(
                            message_id,
                            chart_data,
                            caption=caption_text,
                        )
                        if edit_result:
                            logger.info(f"[Telegram] Chart uploaded: ${symbol}")
                            with state["lock"]:
                                state["chart_uploaded"] = True
                            if analysis_overflow and analysis_text:
                                send_telegram_message(
                                    analysis_text,
                                    parse_mode=None,
                                    reply_to_message_id=message_id,
                                )
                            return
                        logger.warning(f"[Telegram] Chart upload failed: ${symbol}")
                        if analysis_text:
                            send_telegram_message(
                                analysis_text,
                                parse_mode=None,
                                reply_to_message_id=message_id,
                            )
                        del chart_data
                    else:
                        logger.warning(f"[Telegram] Pro chart missing: ${symbol}")
                except TimeoutError as e:
                    logger.error(f"[Telegram] Chart generation error: {e}")
                except Exception as e:
                    logger.error(f"[Telegram] Chart generation error: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                finally:
                    if alarm_active:
                        try:
                            signal.alarm(0)
                        except Exception:
                            pass

                if attempt < _CHART_MAX_RETRIES:
                    time.sleep(_CHART_RETRY_DELAY)
                    continue
                return

        _ensure_async_workers()
        if not _enqueue_task(_CHART_QUEUE, "Chart", generate_and_edit_chart):
            generate_and_edit_chart()
        logger.info(f"[Telegram] Chart generation queued (async): ${symbol}")
        if _get_ai_signal_enabled():
            start_ai_analysis()
    else:
        with state["lock"]:
            state["chart_uploaded"] = True
        if _get_ai_signal_enabled():
            start_ai_analysis()

    return text_result

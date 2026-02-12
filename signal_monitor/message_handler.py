"""
消息处理模块
负责消息的解析、打印和处理逻辑
"""

import hashlib
import json
import os
import time
import threading
from datetime import datetime, timezone, timedelta
from logger import logger
from message_types import MESSAGE_TYPE_MAP, TRADE_TYPE_MAP, FUNDS_MOVEMENT_MAP
from telegram import send_telegram_message, format_message_for_telegram, send_confluence_alert
from database import (
    is_message_processed,
    mark_message_processed,
    is_message_fingerprint_processed,
    mark_message_fingerprint_processed,
)
from signal_tracker import get_signal_tracker

# 北京时区 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))
STARTUP_TIME = time.time()

# 尝试从 config.py 读取配置，环境变量优先
try:
    import config as signal_config
    STARTUP_SIGNAL_MAX_AGE_SECONDS = int(os.getenv("NOFX_STARTUP_SIGNAL_MAX_AGE_SECONDS") or getattr(signal_config, "STARTUP_SIGNAL_MAX_AGE_SECONDS", 600))
    SIGNAL_MAX_AGE_SECONDS = int(os.getenv("NOFX_SIGNAL_MAX_AGE_SECONDS") or getattr(signal_config, "SIGNAL_MAX_AGE_SECONDS", 600))
except ImportError:
    STARTUP_SIGNAL_MAX_AGE_SECONDS = int(os.getenv("NOFX_STARTUP_SIGNAL_MAX_AGE_SECONDS", "600"))
    SIGNAL_MAX_AGE_SECONDS = int(os.getenv("NOFX_SIGNAL_MAX_AGE_SECONDS", "600"))

STARTUP_FILTER_SECONDS = int(
    os.getenv("NOFX_STARTUP_FILTER_SECONDS", str(STARTUP_SIGNAL_MAX_AGE_SECONDS))
)

def _get_message_id(item):
    """Best-effort message id extraction (supports multiple signal response shapes)."""
    if not isinstance(item, dict):
        return None
    for key in ("id", "msgId", "messageId", "message_id", "msg_id"):
        v = item.get(key)
        if v is None:
            continue
        if isinstance(v, (int, float)):
            try:
                return str(int(v))
            except Exception:
                continue
        if isinstance(v, str) and v.strip():
            return v.strip()
    return _build_fallback_message_id(item)


def _build_fallback_message_id(item):
    if not isinstance(item, dict):
        return None
    parts = []
    msg_type = _get_message_type(item)
    if msg_type is not None:
        parts.append(str(msg_type))
    ts_ms = _get_message_timestamp_ms(item)
    if ts_ms:
        parts.append(str(ts_ms))
    title = item.get("title")
    if title:
        parts.append(str(title))
    symbol = _extract_symbol_from_item(item)
    if symbol:
        parts.append(str(symbol))
    if not parts:
        content = item.get("content") or item.get("message")
        if content:
            parts.append(str(content))
    if not parts:
        return None
    base = "|".join(parts)
    digest = hashlib.sha1(base.encode("utf-8", errors="ignore")).hexdigest()[:16]
    return f"fallback_{digest}"


def _normalize_symbol(value):
    if not value:
        return ""
    text = str(value).upper().replace("$", "").strip()
    for suffix in ("USDT", "USD", "USDC", "PERP", "-PERP", "_PERP"):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
    return text.strip()


def _get_message_fingerprint(item):
    if not isinstance(item, dict):
        return None
    msg_type = _get_message_type(item)
    symbol = _normalize_symbol(_extract_symbol_from_item(item))
    ts_ms = _get_message_timestamp_ms(item)
    time_bucket = int(ts_ms // 60000) if ts_ms else 0
    title = item.get("title") or ""
    content = item.get("content") or item.get("message") or ""
    if isinstance(content, dict):
        try:
            content_text = json.dumps(content, ensure_ascii=False, sort_keys=True)
        except Exception:
            content_text = str(content)
    else:
        content_text = str(content)
    content_text = content_text.strip() or str(title)
    if not content_text:
        return None
    base = f"{msg_type}|{symbol}|{time_bucket}|{content_text[:200]}"
    digest = hashlib.sha1(base.encode("utf-8", errors="ignore")).hexdigest()[:16]
    return f"fp_{digest}"


def _get_message_type(item):
    if not isinstance(item, dict):
        return None
    v = item.get("type")
    if v is None:
        v = item.get("messageType")
    return v


def _extract_message_items(response_data):
    """
    Extract the list of message items from common signal API payload shapes.
    Returns a list (possibly empty).
    """
    if isinstance(response_data, list):
        return response_data
    if not isinstance(response_data, dict):
        return []

    data = response_data.get("data")
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []

    # Common pagination container keys
    for key in ("list", "records", "rows", "items", "messages", "data"):
        v = data.get(key)
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            for sub_key in ("list", "records", "rows", "items", "data"):
                sub_v = v.get(sub_key)
                if isinstance(sub_v, list):
                    return sub_v

    return []


def _get_message_timestamp_ms(item):
    if not isinstance(item, dict):
        return None
    for key in ("createTime", "createdTime", "create_time", "timestamp"):
        v = item.get(key)
        if v is None:
            continue
        try:
            value = float(v)
        except (TypeError, ValueError):
            continue
        if value <= 0:
            continue
        # seconds -> ms, ms stays ms
        if value > 1e11:
            return int(value)
        return int(value * 1000)
    return None


def _extract_symbol_from_item(item):
    if not isinstance(item, dict):
        return None
    symbol = item.get("symbol")
    if symbol:
        return symbol
    content = item.get("content")
    if not content:
        return None
    try:
        parsed = json.loads(content)
    except Exception:
        return None
    return parsed.get("symbol")


def _startup_filter_enabled():
    if STARTUP_SIGNAL_MAX_AGE_SECONDS <= 0 or STARTUP_FILTER_SECONDS <= 0:
        return False
    return (time.time() - STARTUP_TIME) <= STARTUP_FILTER_SECONDS


def _filter_items_by_age(items, max_age_seconds, seen_ids=None):
    now_ms = int(time.time() * 1000)
    cutoff_ms = now_ms - (max_age_seconds * 1000)
    filtered_items = []
    skipped_old = 0

    for item in items:
        ts_ms = _get_message_timestamp_ms(item)
        if ts_ms and ts_ms < cutoff_ms:
            skipped_old += 1
            msg_id = _get_message_id(item)
            fingerprint = _get_message_fingerprint(item)
            msg_type = _get_message_type(item)
            title = item.get("title")
            symbol = _extract_symbol_from_item(item)
            content = item.get("content") or item.get("message") or title
            if msg_id and not is_message_processed(msg_id):
                mark_message_processed(msg_id, msg_type, symbol, title, ts_ms, content)
            if fingerprint and not is_message_fingerprint_processed(fingerprint):
                mark_message_fingerprint_processed(
                    fingerprint, msg_id, msg_type, symbol, ts_ms, content
                )
            if seen_ids is not None:
                if msg_id:
                    seen_ids.add(msg_id)
                if fingerprint:
                    seen_ids.add(fingerprint)
            continue
        filtered_items.append(item)

    return filtered_items, skipped_old


def get_beijing_time_str(timestamp_ms, format_str='%Y-%m-%d %H:%M:%S'):
    """
    将时间戳转换为北京时间字符串
    
    Args:
        timestamp_ms: 毫秒级时间戳
        format_str: 时间格式字符串，默认为 '%Y-%m-%d %H:%M:%S'
    
    Returns:
        str: 格式化后的北京时间字符串（带UTC+8标识）
    """
    if not timestamp_ms:
        return 'N/A'
    dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=BEIJING_TZ)
    return dt.strftime(format_str) + ' (UTC+8)'


def get_message_type_name(msg_type):
    """
    获取消息类型名称
    
    Args:
        msg_type: 消息类型代码
    
    Returns:
        str: 消息类型名称
    """
    return MESSAGE_TYPE_MAP.get(msg_type, 'N/A')


def get_trade_type_text(trade_type):
    """
    获取交易类型文本
    
    Args:
        trade_type: 交易类型代码
    
    Returns:
        str: 交易类型文本
    """
    return TRADE_TYPE_MAP.get(trade_type, 'N/A')


def get_funds_movement_text(funds_type):
    """
    获取资金流向文本
    
    Args:
        funds_type: 资金流向类型代码
    
    Returns:
        str: 资金流向文本
    """
    return FUNDS_MOVEMENT_MAP.get(funds_type, 'N/A')


def print_message_details(item, idx=None):
    """
    打印单条消息的详细信息到控制台
    
    Args:
        item: 消息数据字典
        idx: 消息序号（可选）
    """
    msg_type = _get_message_type(item) if isinstance(item, dict) else None
    if msg_type is None:
        msg_type = 'N/A'
    msg_type_name = get_message_type_name(msg_type) if isinstance(msg_type, int) else 'N/A'
    
    # 打印基本信息
    if idx is not None:
        logger.info(f"  [{idx}] {item.get('title', 'N/A')} - {msg_type} {msg_type_name}")
    else:
        logger.info(f"  {item.get('title', 'N/A')} - {msg_type} {msg_type_name}")
    
    logger.info(f"      类型代码: {msg_type}")
    logger.info(f"      ID: {_get_message_id(item) or 'N/A'}")
    logger.info(f"      已读: {'是' if item.get('isRead') else '否'}")
    logger.info(f"      创建时间: {get_beijing_time_str(item.get('createTime', 0))}")
    
    # 解析 content 字段
    if 'content' in item and item['content']:
        try:
            content = json.loads(item['content'])
            if 'symbol' in content:
                logger.info(f"      币种: ${content.get('symbol', 'N/A')}")
            if 'price' in content:
                logger.info(f"      价格: {content.get('price', 'N/A')}")
            if 'percentChange24h' in content:
                logger.info(f"      24h涨跌: {content.get('percentChange24h', 'N/A')}%")
            if 'tradeType' in content:
                trade_type = content.get('tradeType')
                trade_text = get_trade_type_text(trade_type)
                logger.info(f"      交易类型: {trade_type} {trade_text}")
            if 'fundsMovementType' in content:
                funds_type = content.get('fundsMovementType')
                funds_text = get_funds_movement_text(funds_type)
                logger.info(f"      资金流向: {funds_type} {funds_text}")
            if 'source' in content:
                logger.info(f"      来源: {content.get('source', 'N/A')}")
            if 'titleSimplified' in content:
                logger.info(f"      标题: {content.get('titleSimplified', 'N/A')}")
        except:
            pass


def process_message_item(item, idx=None, send_to_telegram=False, signal_callback=None):
    """
    处理单条消息：打印详情并可选发送到 Telegram

    Args:
        item: 消息数据字典
        idx: 消息序号（可选）
        send_to_telegram: 是否发送到 Telegram

    Returns:
        bool: 是否为新消息（未处理过的）
    """
    msg_id = _get_message_id(item)
    fingerprint = _get_message_fingerprint(item)

    # 检查数据库中是否已处理过
    if msg_id and is_message_processed(msg_id):
        logger.info(f"  ⏭️ 消息 ID {msg_id} 已处理过，跳过")
        return False

    # 打印消息详情
    if fingerprint and is_message_fingerprint_processed(fingerprint):
        logger.info(f"  [skip] fingerprint {fingerprint} already processed")
        return False

    print_message_details(item, idx)

    # 提取消息信息用于数据库记录
    msg_type = _get_message_type(item)
    title = item.get('title')
    created_time = item.get('createTime')
    symbol = _extract_symbol_from_item(item)
    parsed_content = None
    price = None

    # 尝试从 content 中提取币种符号和价格
    if 'content' in item and item['content']:
        try:
            parsed_content = json.loads(item['content'])
            if not symbol:
                symbol = parsed_content.get('symbol')
            price = parsed_content.get('price')
        except Exception:
            pass

    def _maybe_trigger_ai_key_levels():
        if not symbol:
            return
        base_symbol = str(symbol).upper().replace("$", "").replace("USDT", "").strip()
        if not base_symbol:
            return
        try:
            from ai_key_levels_config import get_ai_levels_config
            from ai_key_levels_cache import get_levels
        except Exception:
            try:
                from signal_monitor.ai_key_levels_config import get_ai_levels_config
                from signal_monitor.ai_key_levels_cache import get_levels
            except Exception:
                return

        cfg = get_ai_levels_config()
        if not cfg.get("enabled", False):
            return
        if get_levels(base_symbol):
            return

        try:
            from ai_signal_analysis import generate_ai_key_levels
        except Exception:
            try:
                from signal_monitor.ai_signal_analysis import generate_ai_key_levels
            except Exception:
                return

        def _run():
            logger.info("[AI Key Levels] Trigger for %s", base_symbol)
            generate_ai_key_levels(base_symbol)

        threading.Thread(target=_run, daemon=True).start()

    _maybe_trigger_ai_key_levels()

    def _invoke_callback():
        if not signal_callback:
            return
        try:
            signal_callback(item, parsed_content)
        except Exception as callback_error:
            logger.exception(f"信号回调执行失败: {callback_error}")

    def _check_and_send_confluence_signal():
        """检查并发送融合信号"""
        # 只处理 Alpha (110) 和 FOMO (113) 信号
        if msg_type not in [110, 113]:
            return

        # 必须有币种符号和价格
        if not symbol or not price or not created_time:
            return

        # 获取信号追踪器
        tracker = get_signal_tracker()

        # 确定信号类型
        signal_type = 'alpha' if msg_type == 110 else 'fomo'

        # 添加信号到追踪器，检查是否形成融合信号
        is_confluence = tracker.add_signal(
            symbol=symbol,
            signal_type=signal_type,
            price=price,
            message_id=msg_id,
            timestamp_ms=created_time
        )

        # 如果检测到融合信号，发送提醒
        if is_confluence and send_to_telegram:
            summary = tracker.get_signal_summary(symbol)
            send_confluence_alert(
                symbol=symbol,
                price=summary['latest_price'],
                alpha_count=summary['alpha_count'],
                fomo_count=summary['fomo_count']
            )
    
    # 发送到 Telegram（如果启用）
    if send_to_telegram:
        logger.info(f"📤 发送消息到 Telegram...")
        telegram_message = format_message_for_telegram(item)
        
        # 检查是否为支持图表的信号类型
        # AI机会监控: 100, 资金异动: 108, Alpha: 110, 资金出逃: 111, FOMO加剧: 112, FOMO: 113
        # 对于 type 108 资金异动，仅BTC和ETH支持图表
        def _normalize_symbol(value):
            if not value:
                return ""
            return str(value).upper().replace("$", "").replace("USDT", "").strip()

        base_symbol = _normalize_symbol(symbol)
        supports_chart = (
            (msg_type in [100, 110, 111, 112, 113] and base_symbol) or
            (msg_type == 108 and base_symbol in ["BTC", "ETH"])
        )
        
        if supports_chart:
            # 对于AI机会监控、资金异动(BTC/ETH)、Alpha、资金出逃、FOMO加剧和FOMO信号，使用异步图表功能
            if msg_type == 108:
                logger.info(f"📊 检测到资金异动信号 (${base_symbol})，启用异步图表生成")
            else:
                logger.info(f"📊 检测到图表支持的信号类型 {msg_type}，启用异步图表生成")
            from telegram import send_message_with_async_chart
            telegram_result = send_message_with_async_chart(
                telegram_message,
                symbol,
                pin_message=False,
                signal_payload={"item": item, "parsed_content": parsed_content},
            )
        else:
            # 对于其他信号，使用普通发送（包含Binance合约链接）
            telegram_result = send_telegram_message(telegram_message, symbol=symbol)
        
        if telegram_result and telegram_result.get("success"):
            # 发送成功后记录到数据库
            if msg_id:
                content_str = item.get('content') or item.get('message') or title
                if mark_message_processed(msg_id, msg_type, symbol, title, created_time, content_str):
                    if fingerprint:
                        mark_message_fingerprint_processed(
                            fingerprint, msg_id, msg_type, symbol, created_time, content_str
                        )
                    logger.info(f"✅ 消息 ID {msg_id} 已记录到数据库")
                    _invoke_callback()
                    # 检查并发送融合信号
                    _check_and_send_confluence_signal()
                    return True  # 发送并记录成功
                else:
                    logger.warning(f"⚠️ 消息 ID {msg_id} 记录到数据库失败")
                    return False  # 记录失败，下次重试
            if fingerprint:
                content_str = item.get('content') or item.get('message') or title
                mark_message_fingerprint_processed(
                    fingerprint, msg_id, msg_type, symbol, created_time, content_str
                )
            _invoke_callback()
            # 检查并发送融合信号
            _check_and_send_confluence_signal()
            return True  # 没有 msg_id，但发送成功
        else:
            logger.warning(f"⚠️ Telegram 发送失败，消息 ID {msg_id} 未记录到数据库")
            return False  # 发送失败，下次重试
    else:
        # 即使不发送 Telegram，也记录到数据库（避免下次重复处理）
        if msg_id:
            content_str = item.get('content') or item.get('message') or title
            if mark_message_processed(msg_id, msg_type, symbol, title, created_time, content_str):
                if fingerprint:
                    mark_message_fingerprint_processed(
                        fingerprint, msg_id, msg_type, symbol, created_time, content_str
                    )
                logger.info(f"✅ 消息 ID {msg_id} 已记录到数据库（未发送 TG）")
                _invoke_callback()
                return True  # 记录成功
            return False  # 记录失败
        if fingerprint:
            content_str = item.get('content') or item.get('message') or title
            mark_message_fingerprint_processed(
                fingerprint, msg_id, msg_type, symbol, created_time, content_str
            )
        _invoke_callback()
        return True  # 没有 msg_id，直接返回成功


def process_response_data(response_data, send_to_telegram=False, seen_ids=None, signal_callback=None):
    """
    处理 API 响应数据
    
    Args:
        response_data: API 响应的 JSON 数据
        send_to_telegram: 是否将消息发送到 Telegram
        seen_ids: 已见过的消息 ID 集合（用于去重）
        signal_callback: 新消息回调函数（可选）
    
    Returns:
        int: 新消息数量
    """
    # 提取关键信息
    if 'code' in response_data:
        logger.info(f"  状态码: {response_data['code']}")
    if 'msg' in response_data:
        logger.info(f"  消息: {response_data['msg']}")
    
    items = _extract_message_items(response_data)
    if items:
        if send_to_telegram:
            if SIGNAL_MAX_AGE_SECONDS > 0:
                items, skipped_old = _filter_items_by_age(
                    items,
                    SIGNAL_MAX_AGE_SECONDS,
                    seen_ids=seen_ids,
                )
                if skipped_old:
                    logger.info(
                        "  Age filter: skipped %s messages older than %s minutes",
                        skipped_old,
                        SIGNAL_MAX_AGE_SECONDS // 60,
                    )
            elif _startup_filter_enabled():
                items, skipped_old = _filter_items_by_age(
                    items,
                    STARTUP_SIGNAL_MAX_AGE_SECONDS,
                    seen_ids=seen_ids,
                )
                if skipped_old:
                    logger.info(
                        "  Startup filter: skipped %s messages older than %s minutes",
                        skipped_old,
                        STARTUP_SIGNAL_MAX_AGE_SECONDS // 60,
                    )


        total_count = len(items)
        
        # 使用数据库进行持久化去重
        new_messages = []
        duplicate_in_batch = 0
        duplicate_in_db = 0
        
        for item in items:
            msg_id = _get_message_id(item)
            fingerprint = _get_message_fingerprint(item)
            if not msg_id and not fingerprint:
                continue
            
            # 检查本次批次中是否重复（内存去重）
            if seen_ids is not None and (
                (msg_id and msg_id in seen_ids)
                or (fingerprint and fingerprint in seen_ids)
            ):
                duplicate_in_batch += 1
                continue
            
            # 检查数据库中是否已处理（持久化去重）
            if msg_id and is_message_processed(msg_id):
                duplicate_in_db += 1
                if seen_ids is not None:
                    if msg_id:
                        seen_ids.add(msg_id)
                    if fingerprint:
                        seen_ids.add(fingerprint)
                continue
            if fingerprint and is_message_fingerprint_processed(fingerprint):
                duplicate_in_db += 1
                if seen_ids is not None:
                    if msg_id:
                        seen_ids.add(msg_id)
                    if fingerprint:
                        seen_ids.add(fingerprint)
                continue
            
            # 新消息（注意：这里不提前添加到 seen_ids，等发送成功后再添加）
            new_messages.append(item)
        
        new_count = len(new_messages)
        duplicate_count = duplicate_in_batch + duplicate_in_db
        
        logger.info(f"  消息统计: 总共 {total_count} 条, 新消息 {new_count} 条, 重复 {duplicate_count} 条")
        if duplicate_in_db > 0:
            logger.info(f"    └─ 数据库已处理: {duplicate_in_db} 条")
        if duplicate_in_batch > 0:
            logger.info(f"    └─ 本次批次重复: {duplicate_in_batch} 条")
        if seen_ids is not None:
            logger.info(f"  本次运行已处理消息: {len(seen_ids)} 条")
        
        if new_messages:
            logger.info(f"  【新消息列表】:")
            # 倒序发送消息（最新的消息最先发送到 Telegram）
            for idx, item in enumerate(reversed(new_messages), 1):
                # 处理消息，成功后才添加到 seen_ids（防止发送失败时被标记为已处理）
                success = process_message_item(
                    item,
                    idx,
                    send_to_telegram,
                    signal_callback=signal_callback
                )
                if success and seen_ids is not None:
                    msg_id = _get_message_id(item)
                    fingerprint = _get_message_fingerprint(item)
                    if msg_id:
                        seen_ids.add(msg_id)
                    if fingerprint:
                        seen_ids.add(fingerprint)
        else:
            logger.info(f"  本次无新消息（所有消息都已处理过）")
        
        return new_count
    
    return 0


class MessageHandler:
    """Legacy wrapper for compatibility with older code/tests."""

    def __init__(self, db=None):
        self.db = db
        if db is None:
            return
        try:
            import database as _database
            _database._db_instance = db
        except Exception:
            pass

    def process_response_data(self, response_data, send_to_telegram=False, seen_ids=None, signal_callback=None):
        return process_response_data(
            response_data,
            send_to_telegram=send_to_telegram,
            seen_ids=seen_ids,
            signal_callback=signal_callback,
        )

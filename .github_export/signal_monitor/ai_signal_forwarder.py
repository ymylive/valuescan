"""
AI Signal Forwarder
将 AI 信号分析结果转发到交易系统
"""

import json
import socket
import time
from typing import Any, Dict, Optional
from pathlib import Path

try:
    from .logger import logger
except ImportError:
    try:
        from logger import logger
    except ImportError:
        from signal_monitor.logger import logger


def _get_ipc_config():
    """获取 IPC 配置"""
    try:
        from config import IPC_HOST, IPC_PORT, IPC_CONNECT_TIMEOUT, IPC_MAX_RETRIES, IPC_RETRY_DELAY
        return {
            "host": IPC_HOST,
            "port": IPC_PORT,
            "timeout": IPC_CONNECT_TIMEOUT,
            "max_retries": IPC_MAX_RETRIES,
            "retry_delay": IPC_RETRY_DELAY,
        }
    except ImportError:
        return {
            "host": "127.0.0.1",
            "port": 8765,
            "timeout": 5,
            "max_retries": 3,
            "retry_delay": 1,
        }


def forward_ai_signal(
    symbol: str,
    direction: str,
    entry_price: Optional[float] = None,
    stop_loss: Optional[float] = None,
    take_profit_levels: Optional[list] = None,
    confidence: Optional[float] = None,
    analysis: Optional[str] = None,
    message_id: Optional[str] = None,
) -> bool:
    """
    将 AI 信号分析转发到交易系统

    Args:
        symbol: 交易对符号（如 "BTC"）
        direction: 交易方向 "LONG" 或 "SHORT"
        entry_price: 建议入场价格
        stop_loss: 止损价格
        take_profit_levels: 止盈价格列表 [(价格, 比例), ...]
        confidence: AI 信心度 (0-1)
        analysis: AI 分析文本
        message_id: 原始消息 ID

    Returns:
        bool: 是否成功转发
    """
    config = _get_ipc_config()

    # 构建 AI 信号 payload
    payload = {
        "message_type": "AI_SIGNAL",  # 特殊类型标识 AI 信号
        "message_id": message_id or f"ai_{symbol}_{int(time.time())}",
        "symbol": symbol.upper().replace("USDT", "").replace("/", ""),
        "direction": direction.upper(),
        "ai_data": {
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit_levels": take_profit_levels or [],
            "confidence": confidence,
            "analysis": analysis,
            "timestamp": int(time.time()),
        },
    }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n"

    # 尝试发送
    for attempt in range(1, config["max_retries"] + 1):
        try:
            with socket.create_connection(
                (config["host"], config["port"]), timeout=config["timeout"]
            ) as conn:
                conn.sendall(data)

            logger.info(
                "📡 AI 信号已转发: symbol=%s direction=%s entry=%.4f SL=%.4f confidence=%.2f",
                symbol,
                direction,
                entry_price or 0,
                stop_loss or 0,
                confidence or 0,
            )
            return True

        except (ConnectionRefusedError, TimeoutError, OSError) as exc:
            logger.warning(
                "AI 信号转发失败 (第 %s 次尝试): %s", attempt, exc
            )
            if attempt < config["max_retries"]:
                time.sleep(config["retry_delay"])

    logger.error("❌ AI 信号转发失败: symbol=%s direction=%s", symbol, direction)
    return False


def parse_ai_analysis_for_trading(ai_output: str, symbol: str, current_price: float) -> Optional[Dict[str, Any]]:
    """
    解析 AI 分析输出，提取交易信号

    Args:
        ai_output: AI 分析文本
        symbol: 币种符号
        current_price: 当前价格

    Returns:
        Dict 包含交易信号信息，如果无法解析则返回 None
    """
    if not ai_output:
        return None

    ai_lower = ai_output.lower()

    # 检测交易方向
    direction = None
    if any(keyword in ai_lower for keyword in ["做多", "看涨", "买入", "long", "bullish", "buy"]):
        direction = "LONG"
    elif any(keyword in ai_lower for keyword in ["做空", "看跌", "卖出", "short", "bearish", "sell"]):
        direction = "SHORT"

    if not direction:
        logger.debug("AI 分析未包含明确的交易方向: %s", symbol)
        return None

    # 尝试提取价格信息（简单的关键词匹配）
    entry_price = None
    stop_loss = None
    take_profit_levels = []

    # 这里可以添加更复杂的价格提取逻辑
    # 目前使用当前价格作为入场价
    entry_price = current_price

    # 根据方向设置默认止损止盈
    if direction == "LONG":
        stop_loss = current_price * 0.98  # 默认 -2% 止损
        take_profit_levels = [
            (current_price * 1.03, 0.5),  # +3% 平 50%
            (current_price * 1.05, 0.5),  # +5% 平 50%
        ]
    else:  # SHORT
        stop_loss = current_price * 1.02  # 默认 +2% 止损
        take_profit_levels = [
            (current_price * 0.97, 0.5),  # -3% 平 50%
            (current_price * 0.95, 0.5),  # -5% 平 50%
        ]

    # 评估信心度（基于关键词）
    confidence = 0.5  # 默认中等信心
    if any(keyword in ai_lower for keyword in ["强烈", "明确", "高度", "strong", "clear", "high"]):
        confidence = 0.8
    elif any(keyword in ai_lower for keyword in ["谨慎", "观望", "弱", "cautious", "weak", "uncertain"]):
        confidence = 0.3

    return {
        "symbol": symbol,
        "direction": direction,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit_levels": take_profit_levels,
        "confidence": confidence,
        "analysis": ai_output[:500],  # 截取前 500 字符
    }


if __name__ == "__main__":
    # 测试
    import logging
    logging.basicConfig(level=logging.INFO)

    print("AI Signal Forwarder 测试")
    print("=" * 60)

    # 测试解析
    test_analysis = """
    BTC 当前处于上升趋势，技术指标显示强烈的看涨信号。
    建议做多，目标位 50000，止损 45000。
    """

    result = parse_ai_analysis_for_trading(test_analysis, "BTC", 48000)
    print("\n解析结果:", json.dumps(result, indent=2, ensure_ascii=False))

    # 测试转发（需要交易系统运行）
    if result:
        success = forward_ai_signal(**result, message_id="test_123")
        print(f"\n转发结果: {'成功' if success else '失败'}")

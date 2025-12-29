"""
AI Mode Handler
处理 AI 托管模式下的交易信号
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime


class AISignalHandler:
    """
    AI 信号处理器

    在 AI 托管模式下，完全由 AI 信号决定交易
    忽略传统的信号聚合策略（FOMO + Alpha）
    """

    def __init__(self, blacklist: Optional[list] = None):
        """
        初始化 AI 信号处理器

        Args:
            blacklist: 币种黑名单列表
        """
        self.logger = logging.getLogger(__name__)
        self.blacklist = set(s.upper().replace("USDT", "").replace("/", "") for s in (blacklist or []))
        self.logger.info("AI Mode Handler initialized with blacklist: %s", self.blacklist)

    def is_blacklisted(self, symbol: str) -> bool:
        """检查币种是否在黑名单中"""
        clean_symbol = symbol.upper().replace("USDT", "").replace("/", "")
        return clean_symbol in self.blacklist

    def process_ai_signal(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        处理 AI 信号

        Args:
            payload: AI 信号 payload，包含:
                - symbol: 币种符号
                - direction: 交易方向 (LONG/SHORT)
                - ai_data: AI 分析数据
                    - entry_price: 入场价格
                    - stop_loss: 止损价格
                    - take_profit_levels: 止盈级别 [(价格, 比例), ...]
                    - confidence: 信心度 (0-1)
                    - analysis: AI 分析文本

        Returns:
            处理后的交易信号，如果不符合条件则返回 None
        """
        if not isinstance(payload, dict):
            self.logger.warning("Invalid AI signal payload type: %s", type(payload))
            return None

        symbol = payload.get("symbol", "").upper().replace("USDT", "").replace("/", "")
        if not symbol:
            self.logger.warning("AI signal missing symbol")
            return None

        # 检查黑名单
        if self.is_blacklisted(symbol):
            self.logger.info("AI signal ignored: %s is blacklisted", symbol)
            return None

        direction = payload.get("direction", "").upper()
        if direction not in ("LONG", "SHORT"):
            self.logger.warning("AI signal invalid direction: %s for %s", direction, symbol)
            return None

        ai_data = payload.get("ai_data", {})
        if not isinstance(ai_data, dict):
            self.logger.warning("AI signal missing ai_data for %s", symbol)
            return None

        entry_price = ai_data.get("entry_price")
        stop_loss = ai_data.get("stop_loss")
        take_profit_levels = ai_data.get("take_profit_levels", [])
        confidence = ai_data.get("confidence", 0.5)
        analysis = ai_data.get("analysis", "")

        # 验证必要字段
        if not entry_price or not stop_loss:
            self.logger.warning(
                "AI signal missing entry_price or stop_loss for %s", symbol
            )
            return None

        # 验证价格逻辑
        if direction == "LONG":
            if stop_loss >= entry_price:
                self.logger.warning(
                    "AI signal invalid LONG prices for %s: SL=%.4f >= Entry=%.4f",
                    symbol,
                    stop_loss,
                    entry_price,
                )
                return None
        else:  # SHORT
            if stop_loss <= entry_price:
                self.logger.warning(
                    "AI signal invalid SHORT prices for %s: SL=%.4f <= Entry=%.4f",
                    symbol,
                    stop_loss,
                    entry_price,
                )
                return None

        # 构建交易信号
        trade_signal = {
            "symbol": symbol,
            "direction": direction,
            "entry_price": float(entry_price),
            "stop_loss": float(stop_loss),
            "take_profit_levels": [
                (float(price), float(ratio))
                for price, ratio in take_profit_levels
                if isinstance(price, (int, float)) and isinstance(ratio, (int, float))
            ],
            "confidence": float(confidence),
            "analysis": str(analysis)[:500],  # 限制长度
            "timestamp": datetime.now(),
            "source": "AI",
            "message_id": payload.get("message_id"),
        }

        self.logger.info(
            "✅ AI signal processed: %s %s @ %.4f, SL=%.4f, confidence=%.2f",
            symbol,
            direction,
            entry_price,
            stop_loss,
            confidence,
        )

        return trade_signal

    def update_blacklist(self, blacklist: list):
        """更新黑名单"""
        self.blacklist = set(s.upper().replace("USDT", "").replace("/", "") for s in blacklist)
        self.logger.info("Blacklist updated: %s", self.blacklist)


if __name__ == "__main__":
    # 测试
    import json

    logging.basicConfig(level=logging.INFO)

    print("AI Mode Handler 测试")
    print("=" * 60)

    # 创建处理器
    handler = AISignalHandler(blacklist=["DOGE", "SHIB"])

    # 测试有效信号
    test_signal = {
        "message_type": "AI_SIGNAL",
        "message_id": "test_123",
        "symbol": "BTC",
        "direction": "LONG",
        "ai_data": {
            "entry_price": 48000,
            "stop_loss": 47000,
            "take_profit_levels": [(49000, 0.5), (50000, 0.5)],
            "confidence": 0.75,
            "analysis": "强烈看涨信号，建议做多",
            "timestamp": 1234567890,
        },
    }

    print("\n测试 1: 有效的 LONG 信号")
    result = handler.process_ai_signal(test_signal)
    print(json.dumps(result, indent=2, default=str, ensure_ascii=False))

    # 测试黑名单
    print("\n测试 2: 黑名单币种")
    test_signal["symbol"] = "DOGE"
    result = handler.process_ai_signal(test_signal)
    print(f"结果: {result}")

    # 测试无效价格
    print("\n测试 3: 无效的止损价格")
    test_signal["symbol"] = "ETH"
    test_signal["ai_data"]["stop_loss"] = 49000  # SL > Entry (LONG)
    result = handler.process_ai_signal(test_signal)
    print(f"结果: {result}")

    # 测试 SHORT 信号
    print("\n测试 4: 有效的 SHORT 信号")
    test_signal["direction"] = "SHORT"
    test_signal["ai_data"]["entry_price"] = 48000
    test_signal["ai_data"]["stop_loss"] = 49000
    test_signal["ai_data"]["take_profit_levels"] = [(47000, 0.5), (46000, 0.5)]
    result = handler.process_ai_signal(test_signal)
    print(json.dumps(result, indent=2, default=str, ensure_ascii=False))

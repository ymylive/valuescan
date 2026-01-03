"""
AI Position Management Agent
AI 仓位管理子代理 - 决定是否加仓、减仓、平仓
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
import requests


class AIPositionAgent:
    """
    AI 仓位管理代理

    定期分析持仓情况，决定是否需要:
    - 加仓 (Add): 趋势延续，增加仓位
    - 减仓 (Reduce): 风险增加，部分止盈
    - 平仓 (Close): 趋势反转，全部平仓
    - 持有 (Hold): 保持当前仓位
    """

    def __init__(
        self,
        api_key: str = "",
        api_url: str = "",
        model: str = "",
        check_interval: int = 300,
    ):
        """
        初始化 AI 仓位管理代理

        Args:
            api_key: AI API Key
            api_url: AI API URL
            model: AI 模型名称
            check_interval: 检查间隔（秒）
        """
        self.logger = logging.getLogger(__name__)
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.check_interval = check_interval
        self.last_check_time = {}  # symbol -> timestamp

        # 如果未提供配置，尝试从 ai_signal_config.json 读取
        if not self.api_key or not self.api_url or not self.model:
            self._load_config_from_file()

        self.logger.info(
            "AI Position Agent initialized: model=%s, interval=%ds",
            self.model,
            check_interval,
        )

    def _load_config_from_file(self):
        """从配置文件加载 AI API 配置"""
        try:
            from pathlib import Path

            config_path = Path(__file__).parent.parent / "signal_monitor" / "ai_signal_config.json"
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.api_key = self.api_key or config.get("api_key", "")
                    self.api_url = self.api_url or config.get("api_url", "")
                    self.model = self.model or config.get("model", "")
                    self.logger.info("Loaded AI config from file")
        except Exception as e:
            self.logger.warning("Failed to load AI config from file: %s", e)

    def should_check(self, symbol: str) -> bool:
        """检查是否需要对该币种进行分析"""
        now = time.time()
        last_check = self.last_check_time.get(symbol, 0)
        return (now - last_check) >= self.check_interval

    def analyze_position(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        current_price: float,
        quantity: float,
        unrealized_pnl: float,
        unrealized_pnl_percent: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        分析持仓并给出建议

        Args:
            symbol: 币种符号
            direction: 持仓方向 (LONG/SHORT)
            entry_price: 入场价格
            current_price: 当前价格
            quantity: 持仓数量
            unrealized_pnl: 未实现盈亏 (USDT)
            unrealized_pnl_percent: 未实现盈亏百分比
            stop_loss: 止损价格
            take_profit: 止盈价格

        Returns:
            AI 建议，包含:
                - action: 操作建议 (hold/add/reduce/close)
                - reason: 原因说明
                - ratio: 操作比例 (0-1)，仅用于 reduce
                - confidence: 信心度 (0-1)
        """
        if not self.api_key or not self.api_url or not self.model:
            self.logger.warning("AI Position Agent not configured, skipping analysis")
            return None

        if not self.should_check(symbol):
            return None

        self.last_check_time[symbol] = time.time()

        # 构建分析 prompt
        prompt = self._build_position_prompt(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            current_price=current_price,
            quantity=quantity,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_percent=unrealized_pnl_percent,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        # 调用 AI API
        try:
            response = self._call_ai_api(prompt)
            if not response:
                return None

            # 解析 AI 响应
            result = self._parse_ai_response(response)
            if result:
                self.logger.info(
                    "AI Position Analysis for %s: action=%s, reason=%s",
                    symbol,
                    result.get("action"),
                    result.get("reason", "")[:50],
                )
            return result

        except Exception as e:
            self.logger.error("AI Position Analysis failed for %s: %s", symbol, e)
            return None

    def _build_position_prompt(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        current_price: float,
        quantity: float,
        unrealized_pnl: float,
        unrealized_pnl_percent: float,
        stop_loss: Optional[float],
        take_profit: Optional[float],
    ) -> str:
        """构建仓位分析 prompt"""
        # 获取最新市场数据
        market_data = self._fetch_market_data(symbol)

        prompt = f"""你是专业的量化交易分析师，请分析以下持仓并给出操作建议。

**持仓信息:**
- 币种: {symbol}
- 方向: {direction}
- 入场价格: {entry_price:.4f}
- 当前价格: {current_price:.4f}
- 持仓数量: {quantity:.4f}
- 未实现盈亏: {unrealized_pnl:.2f} USDT ({unrealized_pnl_percent:+.2f}%)
- 止损价格: {stop_loss:.4f if stop_loss else '未设置'}
- 止盈价格: {take_profit:.4f if take_profit else '未设置'}

**市场数据:**
{json.dumps(market_data, indent=2, ensure_ascii=False)}

**操作选项:**
1. hold - 继续持有当前仓位
2. add - 加仓（趋势延续，增加仓位）
3. reduce - 减仓（风险增加，部分止盈）
4. close - 平仓（趋势反转，全部平仓）

**输出格式（严格 JSON）:**
{{
  "action": "hold|add|reduce|close",
  "reason": "简短说明原因（50字以内）",
  "ratio": 0.5,  // 仅用于 reduce，表示减仓比例 (0-1)
  "confidence": 0.8  // 信心度 (0-1)
}}

请基于技术分析、资金流向、风险收益比等因素给出建议。"""

        return prompt

    def _fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        """获取市场数据（简化版）"""
        try:
            # 这里可以调用 chart_pro_v10 或其他数据源
            # 为了简化，返回基本信息
            from signal_monitor.market_data_sources import fetch_market_snapshot

            snapshot = fetch_market_snapshot(symbol)
            if snapshot:
                return {
                    "price": snapshot.get("current_price"),
                    "volume_24h": snapshot.get("volume_24h"),
                    "price_change_24h": snapshot.get("price_change_24h"),
                    "fund_flow": snapshot.get("fund_flow", {}),
                }
        except Exception as e:
            self.logger.warning("Failed to fetch market data for %s: %s", symbol, e)

        return {"price": 0, "volume_24h": 0, "price_change_24h": 0}

    def _call_ai_api(self, prompt: str) -> Optional[str]:
        """调用 AI API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional quantitative trading analyst. Reply with strict JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 500,
            "temperature": 0.3,
        }

        try:
            session = requests.Session()
            session.trust_env = False
            resp = session.post(self.api_url, headers=headers, json=payload, timeout=30)

            if resp.status_code != 200:
                self.logger.warning(
                    "AI API call failed: %s - %s", resp.status_code, resp.text[:200]
                )
                return None

            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content.strip()

        except Exception as e:
            self.logger.error("AI API call error: %s", e)
            return None

    def _parse_ai_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析 AI 响应"""
        if not response:
            return None

        try:
            # 尝试直接解析 JSON
            data = json.loads(response)
        except json.JSONDecodeError:
            # 尝试提取 JSON 部分
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    data = json.loads(response[start : end + 1])
                except json.JSONDecodeError:
                    self.logger.warning("Failed to parse AI response: %s", response[:100])
                    return None
            else:
                return None

        # 验证必要字段
        action = data.get("action", "").lower()
        if action not in ("hold", "add", "reduce", "close"):
            self.logger.warning("Invalid action in AI response: %s", action)
            return None

        return {
            "action": action,
            "reason": str(data.get("reason", ""))[:100],
            "ratio": float(data.get("ratio", 0.5)) if action == "reduce" else 0,
            "confidence": float(data.get("confidence", 0.5)),
        }


if __name__ == "__main__":
    # 测试
    logging.basicConfig(level=logging.INFO)

    print("AI Position Agent 测试")
    print("=" * 60)

    # 创建代理（需要配置 AI API）
    agent = AIPositionAgent(check_interval=60)

    # 测试持仓分析
    print("\n测试: 分析 BTC 多头持仓")
    result = agent.analyze_position(
        symbol="BTC",
        direction="LONG",
        entry_price=48000,
        current_price=49500,
        quantity=0.1,
        unrealized_pnl=150,
        unrealized_pnl_percent=3.125,
        stop_loss=47000,
        take_profit=50000,
    )

    if result:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("AI 分析失败或未配置")

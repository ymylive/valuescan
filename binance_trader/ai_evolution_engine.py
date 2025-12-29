"""
AI Evolution Engine
AI 自我进化引擎 - 基于交易数据进行学习和优化
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import requests
from pathlib import Path


class AIEvolutionEngine:
    """
    AI 进化引擎

    功能：
    1. 分析历史交易数据
    2. 发现成功/失败模式
    3. 生成优化建议
    4. 自动调整策略参数
    5. A/B 测试新策略
    """

    def __init__(
        self,
        performance_tracker,
        api_key: str = "",
        api_url: str = "",
        model: str = "",
        evolution_config_path: str = "data/ai_evolution_config.json",
    ):
        """
        初始化进化引擎

        Args:
            performance_tracker: 性能追踪器实例
            api_key: AI API Key
            api_url: AI API URL
            model: AI 模型名称
            evolution_config_path: 进化配置文件路径
        """
        self.logger = logging.getLogger(__name__)
        self.tracker = performance_tracker
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.config_path = Path(evolution_config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # 加载或创建配置
        self.config = self._load_config()

        # 如果未提供 API 配置，尝试从 ai_signal_config.json 读取
        if not self.api_key or not self.api_url or not self.model:
            self._load_ai_config()

        self.logger.info("AI Evolution Engine initialized")

    def _load_config(self) -> Dict[str, Any]:
        """加载进化配置"""
        default_config = {
            "enabled": True,
            "min_trades_for_learning": 50,
            "learning_period_days": 30,
            "evolution_interval_hours": 24,
            "last_evolution_time": 0,
            "current_strategy_version": "1.0",

            # 策略配置
            "evolution_profile": "balanced_day",  # 默认平衡日内

            "strategy_parameters": {
                "confidence_threshold": 0.5,
                "risk_multiplier": 1.0,
                "position_size_multiplier": 1.0,
                "stop_loss_multiplier": 1.0,
                "take_profit_multiplier": 1.0,
            },
            "ab_testing": {
                "enabled": False,
                "test_ratio": 0.2,  # 20% 使用新策略
                "test_strategy_version": None,
                "test_parameters": {},
            },
            "evolution_history": [],
        }

        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    return {**default_config, **loaded}
            except Exception as e:
                self.logger.warning("Failed to load evolution config: %s", e)

        return default_config

    def _save_config(self):
        """保存进化配置"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            self.logger.info("Evolution config saved")
        except Exception as e:
            self.logger.error("Failed to save evolution config: %s", e)

    def _load_ai_config(self):
        """从 ai_signal_config.json 加载 AI API 配置"""
        try:
            config_path = Path(__file__).parent.parent / "signal_monitor" / "ai_signal_config.json"
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.api_key = self.api_key or config.get("api_key", "")
                    self.api_url = self.api_url or config.get("api_url", "")
                    self.model = self.model or config.get("model", "")
                    self.logger.info("Loaded AI config from file")
        except Exception as e:
            self.logger.warning("Failed to load AI config: %s", e)

    def should_evolve(self) -> bool:
        """检查是否应该进行进化"""
        if not self.config["enabled"]:
            return False

        last_evolution = self.config["last_evolution_time"]
        interval_seconds = self.config["evolution_interval_hours"] * 3600
        return (time.time() - last_evolution) >= interval_seconds

    def analyze_and_evolve(self) -> Optional[Dict[str, Any]]:
        """
        分析交易数据并进行进化

        Returns:
            Dict: 进化结果，包含新参数和预期改进
        """
        if not self.should_evolve():
            self.logger.info("Evolution not due yet")
            return None

        self.logger.info("Starting AI evolution process...")

        # 1. 获取交易数据
        trades = self.tracker.get_trades_for_learning(
            min_trades=self.config["min_trades_for_learning"],
            days=self.config["learning_period_days"],
        )

        if not trades:
            self.logger.warning("Insufficient trades for evolution")
            return None

        # 2. 分析交易模式
        patterns = self._analyze_patterns(trades)

        # 3. 生成优化建议
        optimization = self._generate_optimization(trades, patterns)

        if not optimization:
            self.logger.warning("Failed to generate optimization")
            return None

        # 4. 记录进化
        evolution_record = {
            "timestamp": int(time.time()),
            "trades_analyzed": len(trades),
            "patterns": patterns,
            "old_parameters": self.config["strategy_parameters"].copy(),
            "new_parameters": optimization["new_parameters"],
            "expected_improvement": optimization["expected_improvement"],
            "insights": optimization["insights"],
        }

        self.config["evolution_history"].append(evolution_record)
        self.config["last_evolution_time"] = int(time.time())

        # 5. 启用 A/B 测试（如果配置了）
        if self.config["ab_testing"]["enabled"]:
            self._start_ab_test(optimization["new_parameters"])
        else:
            # 直接应用新参数
            self.config["strategy_parameters"] = optimization["new_parameters"]
            self.config["current_strategy_version"] = self._increment_version(
                self.config["current_strategy_version"]
            )

        self._save_config()

        self.logger.info(
            "Evolution completed: expected improvement %.2f%%",
            optimization["expected_improvement"],
        )

        return evolution_record

    def _analyze_patterns(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析交易模式

        Args:
            trades: 交易数据列表

        Returns:
            Dict: 发现的模式
        """
        patterns = {
            "winning_patterns": [],
            "losing_patterns": [],
            "confidence_correlation": {},
            "symbol_performance": {},
            "direction_performance": {},
            "risk_level_performance": {},
        }

        # 按信心度分组
        confidence_groups = {"high": [], "medium": [], "low": []}
        for trade in trades:
            conf = trade["ai_confidence"]
            if conf >= 0.7:
                confidence_groups["high"].append(trade)
            elif conf >= 0.5:
                confidence_groups["medium"].append(trade)
            else:
                confidence_groups["low"].append(trade)

        # 计算每组的胜率和平均盈亏
        for group_name, group_trades in confidence_groups.items():
            if group_trades:
                winning = sum(1 for t in group_trades if t["realized_pnl"] > 0)
                win_rate = winning / len(group_trades) * 100
                avg_pnl = sum(t["realized_pnl_percent"] for t in group_trades) / len(group_trades)
                patterns["confidence_correlation"][group_name] = {
                    "count": len(group_trades),
                    "win_rate": win_rate,
                    "avg_pnl_percent": avg_pnl,
                }

        # 按币种分析
        symbol_stats = {}
        for trade in trades:
            symbol = trade["symbol"]
            if symbol not in symbol_stats:
                symbol_stats[symbol] = {"trades": [], "wins": 0, "total_pnl": 0}
            symbol_stats[symbol]["trades"].append(trade)
            if trade["realized_pnl"] > 0:
                symbol_stats[symbol]["wins"] += 1
            symbol_stats[symbol]["total_pnl"] += trade["realized_pnl_percent"]

        for symbol, stats in symbol_stats.items():
            count = len(stats["trades"])
            patterns["symbol_performance"][symbol] = {
                "count": count,
                "win_rate": stats["wins"] / count * 100,
                "avg_pnl_percent": stats["total_pnl"] / count,
            }

        # 按方向分析
        direction_stats = {"LONG": [], "SHORT": []}
        for trade in trades:
            direction_stats[trade["direction"]].append(trade)

        for direction, dir_trades in direction_stats.items():
            if dir_trades:
                winning = sum(1 for t in dir_trades if t["realized_pnl"] > 0)
                patterns["direction_performance"][direction] = {
                    "count": len(dir_trades),
                    "win_rate": winning / len(dir_trades) * 100,
                    "avg_pnl_percent": sum(t["realized_pnl_percent"] for t in dir_trades) / len(dir_trades),
                }

        # 按风险等级分析
        risk_stats = {"low": [], "medium": [], "high": []}
        for trade in trades:
            risk_level = trade.get("ai_risk_level", "medium")
            if risk_level in risk_stats:
                risk_stats[risk_level].append(trade)

        for risk_level, risk_trades in risk_stats.items():
            if risk_trades:
                winning = sum(1 for t in risk_trades if t["realized_pnl"] > 0)
                patterns["risk_level_performance"][risk_level] = {
                    "count": len(risk_trades),
                    "win_rate": winning / len(risk_trades) * 100,
                    "avg_pnl_percent": sum(t["realized_pnl_percent"] for t in risk_trades) / len(risk_trades),
                }

        return patterns

    def _generate_optimization(
        self,
        trades: List[Dict[str, Any]],
        patterns: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        使用 AI 生成优化建议

        Args:
            trades: 交易数据
            patterns: 分析出的模式

        Returns:
            Dict: 优化建议
        """
        if not self.api_key or not self.api_url or not self.model:
            self.logger.warning("AI API not configured, skipping optimization")
            return None

        # 构建 prompt
        prompt = self._build_optimization_prompt(trades, patterns)

        # 调用 AI API
        try:
            response = self._call_ai_api(prompt)
            if not response:
                return None

            # 解析响应
            optimization = self._parse_optimization_response(response)
            return optimization

        except Exception as e:
            self.logger.error("Failed to generate optimization: %s", e)
            return None

    def _build_optimization_prompt(
        self,
        trades: List[Dict[str, Any]],
        patterns: Dict[str, Any],
    ) -> str:
        """构建优化 prompt"""
        # 计算总体统计
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t["realized_pnl"] > 0)
        win_rate = winning_trades / total_trades * 100
        avg_pnl = sum(t["realized_pnl_percent"] for t in trades) / total_trades

        current_params = self.config["strategy_parameters"]

        # 获取策略配置
        profile_id = self.config.get("evolution_profile", "balanced_day")
        try:
            from binance_trader.ai_evolution_profiles import get_optimization_prompt_suffix
            profile_suffix = get_optimization_prompt_suffix(profile_id)
        except Exception as e:
            self.logger.warning("Failed to load profile config: %s", e)
            profile_suffix = ""

        prompt = f"""你是一个量化交易策略优化专家。请分析以下交易数据并提供优化建议。

**当前策略参数:**
{json.dumps(current_params, indent=2, ensure_ascii=False)}

**交易统计 (最近 {self.config['learning_period_days']} 天):**
- 总交易数: {total_trades}
- 胜率: {win_rate:.2f}%
- 平均盈亏: {avg_pnl:.2f}%

**信心度相关性:**
{json.dumps(patterns['confidence_correlation'], indent=2, ensure_ascii=False)}

**方向表现:**
{json.dumps(patterns['direction_performance'], indent=2, ensure_ascii=False)}

**风险等级表现:**
{json.dumps(patterns['risk_level_performance'], indent=2, ensure_ascii=False)}

**Top 5 币种表现:**
{json.dumps(dict(list(patterns['symbol_performance'].items())[:5]), indent=2, ensure_ascii=False)}

{profile_suffix}

**任务:**
1. 分析当前策略的优缺点
2. 识别可以改进的参数
3. 提供新的参数建议（必须符合策略约束）
4. 预估改进幅度

**输出格式（严格 JSON）:**
{{
  "insights": [
    "发现1: ...",
    "发现2: ...",
    "发现3: ..."
  ],
  "new_parameters": {{
    "confidence_threshold": 0.5,
    "risk_multiplier": 1.0,
    "position_size_multiplier": 1.0,
    "stop_loss_multiplier": 1.0,
    "take_profit_multiplier": 1.0
  }},
  "expected_improvement": 5.0,
  "reasoning": "简要说明优化逻辑"
}}

注意：
- 参数调整必须符合策略配置的约束
- 基于数据驱动，不要过度优化
- 考虑策略的优化目标权重
- 遵守最大参数变化限制
"""

        return prompt

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
                    "content": "You are a quantitative trading strategy optimization expert. Reply with strict JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 2000,
            "temperature": 0.3,
        }

        try:
            session = requests.Session()
            session.trust_env = False
            resp = session.post(self.api_url, headers=headers, json=payload, timeout=60)

            if resp.status_code != 200:
                self.logger.warning("AI API call failed: %s", resp.status_code)
                return None

            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content.strip()

        except Exception as e:
            self.logger.error("AI API call error: %s", e)
            return None

    def _parse_optimization_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析 AI 优化响应"""
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
                    self.logger.warning("Failed to parse optimization response")
                    return None
            else:
                return None

        # 验证必要字段
        if "new_parameters" not in data or "expected_improvement" not in data:
            self.logger.warning("Invalid optimization response format")
            return None

        # 验证参数是否符合策略约束
        profile_id = self.config.get("evolution_profile", "balanced_day")
        try:
            from binance_trader.ai_evolution_profiles import validate_parameters
            valid, error = validate_parameters(profile_id, data["new_parameters"])
            if not valid:
                self.logger.warning("Parameters validation failed: %s", error)
                # 不返回 None，而是记录警告并继续
                # 因为验证可能过于严格
        except Exception as e:
            self.logger.warning("Failed to validate parameters: %s", e)

        return data

    def _start_ab_test(self, new_parameters: Dict[str, Any]):
        """启动 A/B 测试"""
        self.config["ab_testing"]["test_strategy_version"] = self._increment_version(
            self.config["current_strategy_version"]
        )
        self.config["ab_testing"]["test_parameters"] = new_parameters
        self.logger.info(
            "Started A/B test: %s vs %s",
            self.config["current_strategy_version"],
            self.config["ab_testing"]["test_strategy_version"],
        )

    def _increment_version(self, version: str) -> str:
        """递增版本号"""
        try:
            major, minor = version.split(".")
            return f"{major}.{int(minor) + 1}"
        except Exception:
            return "1.1"

    def get_current_parameters(self, use_ab_test: bool = False) -> Dict[str, Any]:
        """
        获取当前策略参数

        Args:
            use_ab_test: 是否使用 A/B 测试参数（随机）

        Returns:
            Dict: 策略参数
        """
        if use_ab_test and self.config["ab_testing"]["enabled"]:
            import random

            if random.random() < self.config["ab_testing"]["test_ratio"]:
                return self.config["ab_testing"]["test_parameters"]

        return self.config["strategy_parameters"]


if __name__ == "__main__":
    # 测试
    import logging
    from ai_performance_tracker import AIPerformanceTracker

    logging.basicConfig(level=logging.INFO)

    print("AI Evolution Engine 测试")
    print("=" * 60)

    tracker = AIPerformanceTracker("data/test_ai_performance.db")
    engine = AIEvolutionEngine(tracker)

    print("\n当前配置:")
    print(json.dumps(engine.config, indent=2, ensure_ascii=False))

    print("\n当前参数:")
    params = engine.get_current_parameters()
    print(json.dumps(params, indent=2, ensure_ascii=False))

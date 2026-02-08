"""
交易员评测 AI 提示词模板
专业的跟单交易员分析提示词 - 增强版
"""

import json
from typing import Dict, Any, Optional

SYSTEM_PROMPT = """你是一位资深的加密货币跟单分析师，拥有10年以上量化交易和风险管理经验。
你的任务是评估带单交易员的交易表现，并为潜在跟随者提供专业、客观的分析建议。

  分析原则：
  1. 数据驱动：所有结论必须基于具体数据，不做主观臆断
  2. 风险优先：始终将风险评估放在首位，保护跟随者资金安全
  3. 客观中立：不夸大收益，不隐瞒风险，实事求是
  4. 全面评估：覆盖收益质量、回撤、杠杆、稳定性与行为一致性
  5. 实用导向：给出可操作的跟随建议和具体参数
  6. 多角度分析：从技术、心理、市场环境等多维度评估"""


def build_evaluation_prompt(metrics_data: Dict[str, Any]) -> str:
    """构建交易员评测提示词 - 增强版，多维度全面分析"""

    prompt = f"""# 任务
对以下带单交易员进行全面深度评测，从多个维度分析其交易能力和风险特征。
必须覆盖：收益质量/稳定性、回撤与风险暴露、杠杆与保证金行为、胜率与盈亏比、风控纪律与行为一致性，并指出数据缺失或冲突。

# 输出格式
仅返回严格 JSON，不要输出任何其他文字：
{{
    "summary": "100-150字的执行摘要，包含核心结论和关键数据",
    "trading_style": "aggressive/conservative/balanced",
    "holding_style": "scalper/day_trader/swing_trader/position_trader",
    "risk_assessment": {{
        "level": "low/medium/high/extreme",
        "score": 0-100,
        "key_risks": ["风险点1", "风险点2", "风险点3"],
        "leverage_analysis": "杠杆使用分析",
        "drawdown_analysis": "回撤风险分析",
        "discipline_analysis": "交易纪律分析"
    }},
    "margin_behavior": {{
        "frequency": "rare/occasional/frequent/excessive",
        "concern_level": "none/low/medium/high",
        "pattern": "defensive/aggressive/panic/strategic",
        "impact_on_roi": "对真实收益率的影响估算",
        "analysis": "保证金行为深度分析（100字以内）"
    }},
    "performance_quality": {{
        "consistency": "high/medium/low",
        "trend": "improving/stable/declining",
        "risk_adjusted_return": "excellent/good/average/poor",
        "analysis": "收益质量分析"
    }},
    "psychological_profile": {{
        "discipline": "high/medium/low",
        "emotional_control": "评估情绪控制能力",
        "loss_handling": "处理亏损的方式"
    }},
    "strengths": ["优势1", "优势2", "优势3"],
    "weaknesses": ["劣势1", "劣势2", "劣势3"],
    "red_flags": ["严重警告信号（如有）"],
    "follow_recommendation": {{
        "verdict": "strongly_recommend/recommend/neutral/caution/avoid",
        "confidence": 0-100,
        "suitable_for": ["适合人群1", "适合人群2"],
        "not_suitable_for": ["不适合人群1", "不适合人群2"],
        "suggested_copy_ratio": 0.0-1.0,
        "max_allocation_percent": 0-100,
        "stop_loss_suggestion": "建议的止损策略",
        "reasoning": "详细推荐理由（100字以内）"
    }},
    "market_condition_fit": {{
        "bull_market": "excellent/good/average/poor",
        "bear_market": "excellent/good/average/poor",
        "sideways_market": "excellent/good/average/poor"
    }}
}}

# 分析框架（权重分配）

## 1. 收益质量分析 (20%)
评估维度：
- ROI 的稳定性和持续性（不是单看数字大小）
- 收益来源分析（是否依赖单笔大赚，还是稳定盈利）
- 不同时间段的表现一致性（7天/30天/90天对比）
- 收益曲线的平滑度

质量评估标准：
- high（高质量）：收益稳定，回撤可控，各时间段表现一致
- medium（中等）：有波动但整体向好
- low（低质量）：收益不稳定，依赖运气或单笔大赚

## 2. 风险管理能力 (30%)
评估维度：
- 杠杆使用：平均杠杆、是否合理
- 最大回撤：历史最大亏损幅度
- 止损纪律：止损使用率（需结合胜率分析）
- 仓位控制：是否有合理的仓位管理

风险评分标准（0-100分，越高风险越大）：
- 杠杆风险：>20x=30分, >10x=20分, >5x=10分, <=5x=5分
- 回撤风险：>30%=25分, >20%=15分, >10%=8分, <=10%=3分
- 保证金风险：>20%添加率=25分, >10%=18分, >5%=10分, <=5%=2分
- 止损纪律评估（重要！需综合多维度判断）：

  止损率为0或极低不一定是坏事，需要综合分析：

  【情况A：高胜率精准交易型】（不扣分，反而是优势）
  条件：胜率>85% + 平均持仓<24小时 + 回撤<15%
  解读：交易员择时精准，每单都能盈利出场，不需要止损
  评价：这是顶级交易能力的体现，应作为优势标注

  【情况B：正常交易型】（轻微扣分0-5分）
  条件：胜率70-85% + 回撤<20%
  解读：胜率较高，偶尔亏损但控制得当
  评价：风险可控，正常范围

  【情况C：潜在扛单型】（警告！扣15-25分）
  条件：止损率<10% + 以下任一情况：
    - 平均持仓时间>48小时（长时间持仓不止损）
    - 最大回撤>25%（经历大幅亏损仍不止损）
    - 胜率<70% + 回撤>15%
  解读：可能存在"死扛不止损"的危险倾向
  评价：必须在red_flags中标注"疑似扛单行为"
  风险提示：一旦遇到极端行情，可能导致巨额亏损

  【情况D：高风险扛单型】（严重警告！扣25-35分）
  条件：止损率<5% + 平均持仓>72小时 + 回撤>20%
  解读：明显的扛单行为，靠时间换空间
  评价：强烈建议回避，必须在summary中警告

风险等级划分：
- low（低风险）：总分 0-25
- medium（中等风险）：总分 26-50
- high（高风险）：总分 51-75
- extreme（极高风险）：总分 76-100

## 3. 保证金行为分析 (25%) - 需要结合交易记录深度分析！

保证金添加行为有两种完全不同的含义，必须区分：

【做T操作 vs 扛单行为 - 关键区分！】

1. 做T操作（正常策略，不扣分）：
   - 定义：在同一仓位上进行高抛低吸，主动摊平成本
   - 特征：
     * 添加保证金后有明确的加仓/减仓操作
     * 最终以盈利平仓
     * 持仓期间有多次部分平仓记录
     * 平均持仓时间较短（<24小时）
   - 判断依据：查看recent_trades中是否有同一币种的多次开平仓记录

2. 扛单行为（高风险，需警告）：
   - 定义：亏损时被动补仓，等待行情回调
   - 特征：
     * 添加保证金后无主动操作，只是等待
     * 持仓时间很长（>48小时）
     * 最终可能盈利但经历了大幅浮亏
     * 无部分平仓记录，一次性全平
   - 判断依据：持仓时间长 + 回撤大 + 无做T记录

【如何判断 - 参考recent_trades数据】
- 如果recent_trades显示同一币种有多次开平仓 → 做T操作
- 如果recent_trades显示只有一次开仓一次平仓 → 可能是扛单
- 如果持仓时间短且盈利 → 做T成功
- 如果持仓时间长且经历大回撤 → 扛单行为

警戒标准（仅针对确认的扛单行为）：
- rare（罕见）：<5%交易涉及扛单 → 正常
- occasional（偶尔）：5-10% → 需要关注
- frequent（频繁）：10-20% → 高风险警告
- excessive（过度）：>20% → 强烈建议回避

【数据异常处理】
如果胜率、回撤、杠杆等关键数据为0或明显异常：
- 必须在summary中标注"部分数据可能不完整"
- 降低分析置信度
- 建议用户查看更多历史数据后再做决定

## 4. 交易风格分析 (15%)
评估维度：
- 交易频率：日均交易次数
- 偏好币种：主流币/山寨币偏好
- 多空比例：做多vs做空倾向
- 持仓时长：平均持仓时间

风格分类标准：
- aggressive（激进）：高杠杆(>15x)、高频交易、追涨杀跌
- conservative（稳健）：低杠杆(<8x)、高胜率(>55%)、严格止损
- balanced（均衡）：中等杠杆、适度频率、风险可控

持仓分类标准：
- scalper（超短线）：平均持仓<1小时
- day_trader（日内）：平均持仓1-24小时
- swing_trader（波段）：平均持仓1-7天
- position_trader（中长线）：平均持仓>7天

## 5. 心理素质评估 (10%)
评估维度：
- 交易纪律：是否严格执行策略
- 情绪控制：连续亏损后的行为模式
- 风险意识：是否有过度自信的迹象

# 跟随建议标准

strongly_recommend（强烈推荐）：
- 风险评分 < 25
- 无频繁保证金添加（<5%）
- 90天正收益且回撤 < 15%
- 收益质量高，表现稳定
- 建议跟单比例：0.8-1.0x

recommend（推荐）：
- 风险评分 25-40
- 保证金添加 < 10%
- 整体表现良好
- 有明确的风险管理
- 建议跟单比例：0.5-0.8x

neutral（中性）：
- 风险评分 40-55
- 存在一些风险因素
- 需要谨慎跟随
- 建议小仓位测试
- 建议跟单比例：0.3-0.5x

caution（警告）：
- 风险评分 55-75
- 存在明显风险
- 仅适合有经验的跟随者
- 必须设置严格止损
- 建议跟单比例：0.1-0.3x

avoid（回避）：
- 风险评分 > 75
- 频繁保证金添加（>15%）
- 极端杠杆或回撤
- 存在严重红旗信号
- 建议跟单比例：0x

# 交易员数据
```json
{json.dumps(metrics_data, ensure_ascii=False, indent=2)}
```

如输入包含 derived_signals、risk_score、margin_behavior 等提示，请纳入判断并保持一致性。
请基于以上数据和分析框架，给出专业、全面、客观的评测报告。重点关注保证金行为和风险因素。"""

    return prompt


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def _coerce_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _compute_risk_score(metrics) -> int:
    score = getattr(metrics, "risk_score", None)
    if isinstance(score, int) and 0 <= score <= 100 and score > 0:
        return score

    score = 0
    avg_leverage = _safe_float(getattr(metrics, "avg_leverage", 0.0))
    max_drawdown = _safe_float(getattr(metrics, "max_drawdown", 0.0))
    margin_ratio = _safe_float(getattr(metrics, "margin_addition_ratio", 0.0))
    stop_loss_usage = _safe_float(getattr(metrics, "stop_loss_usage_rate", 0.0))

    if avg_leverage > 20:
        score += 30
    elif avg_leverage > 10:
        score += 20
    elif avg_leverage > 5:
        score += 10

    if max_drawdown > 30:
        score += 25
    elif max_drawdown > 20:
        score += 15
    elif max_drawdown > 10:
        score += 8

    if margin_ratio > 0.2:
        score += 25
    elif margin_ratio > 0.1:
        score += 18
    elif margin_ratio > 0.05:
        score += 10

    if stop_loss_usage < 0.1:
        score += 20
    elif stop_loss_usage < 0.3:
        score += 10

    return int(_clamp(score, 0, 100))


def _risk_level_from_score(score: int) -> str:
    if score >= 76:
        return "extreme"
    if score >= 51:
        return "high"
    if score >= 26:
        return "medium"
    return "low"


def _margin_behavior_from_ratio(ratio: float) -> Dict[str, str]:
    if ratio > 0.2:
        return {"frequency": "excessive", "concern_level": "high"}
    if ratio > 0.1:
        return {"frequency": "frequent", "concern_level": "high"}
    if ratio > 0.05:
        return {"frequency": "occasional", "concern_level": "medium"}
    if ratio > 0:
        return {"frequency": "rare", "concern_level": "low"}
    return {"frequency": "rare", "concern_level": "none"}


def build_baseline_evaluation(metrics, analysis: Optional[Any] = None) -> Dict[str, Any]:
    """基于指标生成非 AI 评测结果（用于兜底与补全）。"""
    roi_7d = _safe_float(getattr(metrics, "roi_7d", 0.0))
    roi_30d = _safe_float(getattr(metrics, "roi_30d", 0.0))
    roi_90d = _safe_float(getattr(metrics, "roi_90d", 0.0))
    win_rate = _safe_float(getattr(metrics, "win_rate", 0.0))
    max_drawdown = _safe_float(getattr(metrics, "max_drawdown", 0.0))
    avg_leverage = _safe_float(getattr(metrics, "avg_leverage", 0.0))
    max_leverage = _safe_float(getattr(metrics, "max_leverage", 0.0))
    profit_factor = _safe_float(getattr(metrics, "profit_factor", 0.0))
    sharpe_ratio = _safe_float(getattr(metrics, "sharpe_ratio", 0.0))
    stop_loss_usage = _safe_float(getattr(metrics, "stop_loss_usage_rate", 0.0))
    margin_ratio = _safe_float(getattr(metrics, "margin_addition_ratio", 0.0))
    trade_count = int(getattr(metrics, "trade_count", 0) or 0)
    long_ratio = _safe_float(getattr(metrics, "long_ratio", 0.5))

    risk_score = _compute_risk_score(metrics)
    risk_level = getattr(metrics, "risk_level", "") or _risk_level_from_score(risk_score)

    margin_profile = _margin_behavior_from_ratio(margin_ratio)
    margin_pattern = "panic" if margin_ratio > 0.2 else "aggressive" if margin_ratio > 0.1 else "strategic" if margin_ratio > 0.05 else "defensive"
    margin_impact = "可能放大回撤" if margin_ratio > 0.1 else "影响可控"

    consistency = "high"
    roi_diffs = [abs(roi_7d - roi_30d), abs(roi_30d - roi_90d)]
    if any(diff > 20 for diff in roi_diffs):
        consistency = "low"
    elif any(diff > 10 for diff in roi_diffs):
        consistency = "medium"

    trend = "stable"
    if roi_7d > roi_30d > roi_90d:
        trend = "improving"
    elif roi_7d < roi_30d < roi_90d:
        trend = "declining"

    if sharpe_ratio >= 1.5 or profit_factor >= 2.0:
        risk_adjusted = "excellent"
    elif sharpe_ratio >= 1.0 or profit_factor >= 1.5:
        risk_adjusted = "good"
    elif sharpe_ratio >= 0.5 or profit_factor >= 1.1:
        risk_adjusted = "average"
    else:
        risk_adjusted = "poor"

    trading_style = getattr(metrics, "trading_style", "") or "balanced"
    holding_style = getattr(metrics, "holding_style", "") or "swing_trader"

    strengths = _coerce_list(getattr(analysis, "strengths", []))
    weaknesses = _coerce_list(getattr(analysis, "weaknesses", []))
    risk_factors = _coerce_list(getattr(analysis, "risk_factors", []))

    if not strengths:
        if win_rate >= 0.6:
            strengths.append("胜率较高")
        if max_drawdown <= 15:
            strengths.append("回撤控制良好")
        if profit_factor >= 2:
            strengths.append("盈亏比优秀")
    if not weaknesses:
        if max_drawdown >= 30:
            weaknesses.append("回撤偏大")
        if avg_leverage >= 15:
            weaknesses.append("杠杆偏高")
        if stop_loss_usage <= 0.1:
            weaknesses.append("止损使用偏低")

    red_flags = list(risk_factors)
    if margin_ratio >= 0.2:
        red_flags.append("频繁追加保证金")
    if max_drawdown >= 40:
        red_flags.append("历史大幅回撤")
    if max_leverage >= 50:
        red_flags.append("极端杠杆使用")
    if stop_loss_usage <= 0.05 and max_drawdown >= 20:
        red_flags.append("疑似扛单行为")

    if risk_score <= 25 and roi_90d > 0:
        verdict = "strongly_recommend"
        ratio = 0.8
    elif risk_score <= 40:
        verdict = "recommend"
        ratio = 0.6
    elif risk_score <= 55:
        verdict = "neutral"
        ratio = 0.4
    elif risk_score <= 75:
        verdict = "caution"
        ratio = 0.2
    else:
        verdict = "avoid"
        ratio = 0.0

    confidence_base = 50 if trade_count >= 200 else 40 if trade_count >= 50 else 30
    confidence = int(_clamp(confidence_base - (risk_score * 0.2), 30, 90))

    max_alloc = int(_clamp(ratio * 100, 5, 80))
    if verdict in ("caution", "avoid"):
        max_alloc = min(max_alloc, 20)

    if long_ratio > 0.65:
        market_fit = {"bull_market": "excellent", "bear_market": "poor", "sideways_market": "average"}
    elif long_ratio < 0.35:
        market_fit = {"bull_market": "poor", "bear_market": "excellent", "sideways_market": "average"}
    else:
        market_fit = {"bull_market": "good", "bear_market": "good", "sideways_market": "excellent"}

    summary = getattr(analysis, "summary", "") or (
        f"90天收益{roi_90d:+.1f}%，胜率{win_rate:.1%}，最大回撤{max_drawdown:.1f}%。"
        f" 风险评分{risk_score}/100，杠杆均值{avg_leverage:.1f}x。"
    )

    return {
        "summary": summary,
        "trading_style": trading_style,
        "holding_style": holding_style,
        "risk_assessment": {
            "level": risk_level,
            "score": risk_score,
            "key_risks": red_flags[:3] if red_flags else ["暂无明显高危信号"],
            "leverage_analysis": f"平均杠杆{avg_leverage:.1f}x，最高{max_leverage:.1f}x",
            "drawdown_analysis": f"最大回撤{max_drawdown:.1f}%，需关注回撤承受能力",
            "discipline_analysis": f"止损使用率{stop_loss_usage:.1%}，结合胜率评估纪律性",
        },
        "margin_behavior": {
            "frequency": margin_profile["frequency"],
            "concern_level": margin_profile["concern_level"],
            "pattern": margin_pattern,
            "impact_on_roi": margin_impact,
            "analysis": f"保证金添加占比{margin_ratio:.1%}，偏{margin_pattern}策略",
        },
        "performance_quality": {
            "consistency": consistency,
            "trend": trend,
            "risk_adjusted_return": risk_adjusted,
            "analysis": f"收益稳定性{consistency}，盈亏比{profit_factor:.2f}，夏普{sharpe_ratio:.2f}",
        },
        "psychological_profile": {
            "discipline": "high" if stop_loss_usage >= 0.5 else "medium" if stop_loss_usage >= 0.2 else "low",
            "emotional_control": "回撤可控" if max_drawdown <= 20 else "回撤偏高需观察",
            "loss_handling": "短持仓修正" if getattr(metrics, "avg_holding_hours", 0) < 24 else "持仓周期偏长",
        },
        "strengths": strengths[:3],
        "weaknesses": weaknesses[:3],
        "red_flags": red_flags[:3],
        "follow_recommendation": {
            "verdict": verdict,
            "confidence": confidence,
            "suitable_for": ["风险承受力中等以上", "可接受波动的跟随者"],
            "not_suitable_for": ["极低风险偏好", "无法承受回撤的用户"],
            "suggested_copy_ratio": ratio,
            "max_allocation_percent": max_alloc,
            "stop_loss_suggestion": "单笔止损2-3%，组合回撤>15%建议降低跟随比例",
            "reasoning": "基于风险评分、回撤与杠杆情况给出跟随建议",
        },
        "market_condition_fit": market_fit,
    }


def merge_evaluation(ai_eval: Optional[Dict[str, Any]], baseline: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(ai_eval, dict):
        return baseline

    def merge_value(key: str, base_val: Any, ai_val: Any) -> Any:
        if ai_val in (None, "", [], {}):
            return base_val
        if key in ("suggested_copy_ratio",):
            return _clamp(_safe_float(ai_val, base_val), 0.0, 1.0)
        if key in ("confidence", "score"):
            return int(_clamp(_safe_float(ai_val, base_val), 0, 100))
        return ai_val

    merged = dict(baseline)
    for key, base_val in baseline.items():
        if key not in ai_eval:
            continue
        ai_val = ai_eval.get(key)
        if isinstance(base_val, dict) and isinstance(ai_val, dict):
            merged_child = dict(base_val)
            for child_key, child_base in base_val.items():
                if child_key in ai_val:
                    merged_child[child_key] = merge_value(child_key, child_base, ai_val.get(child_key))
            merged[key] = merged_child
        else:
            merged[key] = merge_value(key, base_val, ai_val)

    for key, ai_val in ai_eval.items():
        if key not in merged and ai_val not in (None, "", [], {}):
            merged[key] = ai_val

    return merged


def parse_evaluation_response(response_text: str) -> Optional[Dict[str, Any]]:
    """解析 AI 评测响应"""
    try:
        # 去除可能的 markdown 代码块标记
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        # 尝试直接解析
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试提取 JSON 部分
        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response_text[start:end])
        except:
            pass

    return None


def get_default_evaluation() -> Dict[str, Any]:
    """返回默认评测结果"""
    return {
        "summary": "数据不足，无法完成评测",
        "trading_style": "balanced",
        "holding_style": "swing_trader",
        "risk_assessment": {
            "level": "medium",
            "score": 50,
            "key_risks": ["数据不足"],
            "leverage_analysis": "无法分析",
            "drawdown_analysis": "无法分析",
            "discipline_analysis": "无法分析",
        },
        "margin_behavior": {
            "frequency": "rare",
            "concern_level": "medium",
            "pattern": "defensive",
            "impact_on_roi": "无法估算",
            "analysis": "无法分析",
        },
        "performance_quality": {
            "consistency": "low",
            "trend": "stable",
            "risk_adjusted_return": "average",
            "analysis": "数据不足",
        },
        "psychological_profile": {
            "discipline": "medium",
            "emotional_control": "未知",
            "loss_handling": "未知",
        },
        "strengths": [],
        "weaknesses": ["数据不足"],
        "red_flags": ["数据不足"],
        "follow_recommendation": {
            "verdict": "neutral",
            "confidence": 40,
            "suitable_for": [],
            "not_suitable_for": ["所有人"],
            "suggested_copy_ratio": 0.0,
            "max_allocation_percent": 0,
            "stop_loss_suggestion": "观望",
            "reasoning": "数据不足，建议观望",
        },
        "market_condition_fit": {
            "bull_market": "average",
            "bear_market": "average",
            "sideways_market": "average",
        },
    }


def format_evaluation_message(evaluation: Dict[str, Any], metrics) -> str:
    """格式化评测结果为 Telegram 消息"""

    # 风格翻译
    style_cn = {
        "aggressive": "激进型",
        "conservative": "稳健型",
        "balanced": "均衡型",
        "unknown": "未知"
    }
    holding_cn = {
        "scalper": "超短线",
        "day_trader": "日内",
        "swing_trader": "波段",
        "position_trader": "中长线",
        "unknown": "未知"
    }
    risk_cn = {
        "low": "低",
        "medium": "中等",
        "high": "高",
        "extreme": "极高",
        "unknown": "未知"
    }
    verdict_cn = {
        "strongly_recommend": "强烈推荐",
        "recommend": "推荐",
        "neutral": "中性",
        "caution": "警告",
        "avoid": "回避"
    }
    margin_cn = {
        "rare": "罕见",
        "occasional": "偶尔",
        "frequent": "频繁",
        "excessive": "过度",
        "unknown": "未知"
    }

    risk = evaluation.get("risk_assessment", {})
    margin = evaluation.get("margin_behavior", {})
    rec = evaluation.get("follow_recommendation", {})

    # 构建消息
    lines = [
        f"<b>📊 交易员评测报告</b>",
        f"<b>ID:</b> {metrics.portfolio_id}",
        f"<b>昵称:</b> {metrics.nickname}",
        "",
        f"<b>📈 表现数据</b>",
        f"• 90天收益: {metrics.roi_90d:+.1f}%",
        f"• 胜率: {metrics.win_rate:.1%}",
        f"• 盈亏比: {getattr(metrics, 'profit_factor', 0):.2f}",
        f"• 夏普比: {getattr(metrics, 'sharpe_ratio', 0):.2f}",
        f"• 最大回撤: {metrics.max_drawdown:.1f}%",
        f"• 跟随者: {metrics.follower_count:,}",
        "",
        f"<b>🎯 风格分析</b>",
        f"• 交易风格: {style_cn.get(evaluation.get('trading_style', ''), '未知')}",
        f"• 持仓风格: {holding_cn.get(evaluation.get('holding_style', ''), '未知')}",
        f"• 平均杠杆: {metrics.avg_leverage:.1f}x",
        f"• 日均交易: {metrics.trade_frequency:.1f}次",
        f"• 止损使用: {metrics.stop_loss_usage_rate:.1%}",
    ]

    # 添加币种分布
    if hasattr(metrics, 'coin_distribution') and metrics.coin_distribution:
        coins_str = ", ".join([f"{c.get('asset', '?')} {c.get('volume', 0):.1f}%" for c in metrics.coin_distribution[:4]])
        lines.append(f"• 偏好币种: {coins_str}")

    lines.extend([
        "",
        f"<b>⚠️ 风险评估</b>",
        f"• 风险等级: {risk_cn.get(risk.get('level', ''), '未知')}",
        f"• 风险评分: {risk.get('score', 0)}/100",
    ])

    # 风险因素
    key_risks = risk.get("key_risks", [])
    if key_risks:
        lines.append(f"• 风险因素: {', '.join(key_risks[:3])}")

    # 保证金行为 - 重点标注
    lines.extend([
        "",
        f"<b>💰 保证金行为</b>",
        f"• 添加频率: {margin_cn.get(margin.get('frequency', ''), '未知')}",
        f"• 关注程度: {margin.get('concern_level', '未知')}",
        f"• 添加比例: {getattr(metrics, 'margin_addition_ratio', 0):.1%}",
    ])

    if margin.get("analysis"):
        lines.append(f"• 分析: {margin.get('analysis')[:100]}")

    # 优劣势
    strengths = evaluation.get("strengths", [])
    weaknesses = evaluation.get("weaknesses", [])

    if strengths:
        lines.extend(["", f"<b>✅ 优势</b>"])
        for s in strengths[:3]:
            lines.append(f"• {s}")

    if weaknesses:
        lines.extend(["", f"<b>❌ 劣势</b>"])
        for w in weaknesses[:3]:
            lines.append(f"• {w}")

    red_flags = evaluation.get("red_flags", [])
    if red_flags:
        lines.extend(["", f"<b>🚩 风险警示</b>"])
        for flag in red_flags[:3]:
            lines.append(f"• {flag}")

    # 跟随建议
    verdict = rec.get("verdict", "neutral")
    verdict_emoji = {
        "strongly_recommend": "🟢",
        "recommend": "🟢",
        "neutral": "🟡",
        "caution": "🟠",
        "avoid": "🔴"
    }

    lines.extend([
        "",
        f"<b>📋 跟随建议</b>",
        f"{verdict_emoji.get(verdict, '⚪')} <b>{verdict_cn.get(verdict, '中性')}</b>",
        f"• 建议比例: {rec.get('suggested_copy_ratio', 0):.0%}",
        f"• 最大占比: {rec.get('max_allocation_percent', 0)}%",
        f"• 置信度: {rec.get('confidence', 0)}/100",
    ])

    suitable = rec.get("suitable_for", [])
    if suitable:
        lines.append(f"• 适合: {', '.join(suitable[:2])}")

    if rec.get("reasoning"):
        lines.append(f"• 理由: {rec.get('reasoning')[:80]}")

    # 总结
    if evaluation.get("summary"):
        lines.extend(["", f"<b>📝 总结</b>", evaluation.get("summary")])

    return "\n".join(lines)

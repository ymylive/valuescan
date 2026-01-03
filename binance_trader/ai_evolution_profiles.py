"""
AI Evolution Strategy Profiles
AI 进化策略配置文件 - 定义不同的进化方向和交易风格
"""

from typing import Dict, Any


# ============ 风险偏好配置 ============

RISK_PROFILES = {
    "conservative": {
        "name": "稳健型",
        "name_en": "Conservative",
        "description": "低风险，追求稳定收益，注重资金安全",
        "optimization_goals": {
            "win_rate_weight": 0.4,  # 胜率权重
            "profit_weight": 0.2,  # 盈利权重
            "risk_weight": 0.4,  # 风险控制权重
            "sharpe_ratio_weight": 0.3,  # 夏普比率权重
            "max_drawdown_weight": 0.3,  # 最大回撤权重
        },
        "parameter_constraints": {
            "max_leverage": 5,  # 最大杠杆
            "max_position_percent": 3.0,  # 最大单仓位
            "min_confidence_threshold": 0.7,  # 最低信心度
            "stop_loss_range": [1.5, 3.0],  # 止损范围
            "take_profit_range": [2.0, 5.0],  # 止盈范围
        },
        "evolution_strategy": {
            "max_parameter_change": 0.1,  # 最大参数变化 10%
            "require_ab_test": True,  # 必须 A/B 测试
            "min_improvement": 3.0,  # 最小改进要求 3%
        },
    },
    "balanced": {
        "name": "风险平衡型",
        "name_en": "Balanced",
        "description": "平衡风险与收益，适合大多数交易者",
        "optimization_goals": {
            "win_rate_weight": 0.3,
            "profit_weight": 0.3,
            "risk_weight": 0.2,
            "sharpe_ratio_weight": 0.2,
            "max_drawdown_weight": 0.2,
        },
        "parameter_constraints": {
            "max_leverage": 10,
            "max_position_percent": 5.0,
            "min_confidence_threshold": 0.6,
            "stop_loss_range": [1.0, 3.0],
            "take_profit_range": [2.0, 6.0],
        },
        "evolution_strategy": {
            "max_parameter_change": 0.15,
            "require_ab_test": True,
            "min_improvement": 2.0,
        },
    },
    "aggressive": {
        "name": "激进型",
        "name_en": "Aggressive",
        "description": "高风险高收益，追求最大化利润",
        "optimization_goals": {
            "win_rate_weight": 0.2,
            "profit_weight": 0.5,  # 重点关注盈利
            "risk_weight": 0.1,
            "sharpe_ratio_weight": 0.1,
            "max_drawdown_weight": 0.1,
        },
        "parameter_constraints": {
            "max_leverage": 20,
            "max_position_percent": 10.0,
            "min_confidence_threshold": 0.5,
            "stop_loss_range": [0.5, 2.0],
            "take_profit_range": [3.0, 10.0],
        },
        "evolution_strategy": {
            "max_parameter_change": 0.2,
            "require_ab_test": False,  # 可以直接应用
            "min_improvement": 1.0,
        },
    },
}


# ============ 交易风格配置 ============

TRADING_STYLES = {
    "scalping": {
        "name": "剥头皮",
        "name_en": "Scalping",
        "description": "超短线交易，快进快出，追求小幅利润",
        "time_horizon": "1-5分钟",
        "characteristics": {
            "holding_time_target": 300,  # 目标持仓时间（秒）
            "profit_target": 0.5,  # 目标利润 0.5%
            "max_holding_time": 900,  # 最大持仓时间 15分钟
            "trade_frequency": "very_high",  # 交易频率
        },
        "parameter_preferences": {
            "stop_loss_percent": 0.3,  # 紧止损
            "take_profit_percent": 0.5,  # 小止盈
            "trailing_stop_activation": 0.3,
            "trailing_stop_callback": 0.2,
            "position_monitor_interval": 5,  # 5秒监控一次
        },
        "optimization_focus": {
            "execution_speed": 0.3,  # 执行速度
            "win_rate": 0.4,  # 胜率（剥头皮需要高胜率）
            "profit_per_trade": 0.1,  # 单笔利润
            "trade_frequency": 0.2,  # 交易频率
        },
    },
    "day_trading": {
        "name": "短线交易",
        "name_en": "Day Trading",
        "description": "日内交易，当日开仓当日平仓",
        "time_horizon": "1-8小时",
        "characteristics": {
            "holding_time_target": 14400,  # 4小时
            "profit_target": 2.0,  # 目标利润 2%
            "max_holding_time": 28800,  # 最大 8小时
            "trade_frequency": "high",
        },
        "parameter_preferences": {
            "stop_loss_percent": 1.0,
            "take_profit_percent": 2.0,
            "trailing_stop_activation": 1.5,
            "trailing_stop_callback": 0.8,
            "position_monitor_interval": 30,
        },
        "optimization_focus": {
            "execution_speed": 0.2,
            "win_rate": 0.3,
            "profit_per_trade": 0.3,
            "trade_frequency": 0.2,
        },
    },
    "swing_trading": {
        "name": "中线交易",
        "name_en": "Swing Trading",
        "description": "波段交易，持仓数天到数周",
        "time_horizon": "2-10天",
        "characteristics": {
            "holding_time_target": 259200,  # 3天
            "profit_target": 5.0,  # 目标利润 5%
            "max_holding_time": 864000,  # 最大 10天
            "trade_frequency": "medium",
        },
        "parameter_preferences": {
            "stop_loss_percent": 2.0,
            "take_profit_percent": 5.0,
            "trailing_stop_activation": 3.0,
            "trailing_stop_callback": 1.5,
            "position_monitor_interval": 300,  # 5分钟
        },
        "optimization_focus": {
            "execution_speed": 0.1,
            "win_rate": 0.2,
            "profit_per_trade": 0.5,  # 重点关注单笔利润
            "trade_frequency": 0.2,
        },
    },
    "position_trading": {
        "name": "长线交易",
        "name_en": "Position Trading",
        "description": "趋势跟踪，持仓数周到数月",
        "time_horizon": "1-3个月",
        "characteristics": {
            "holding_time_target": 2592000,  # 30天
            "profit_target": 15.0,  # 目标利润 15%
            "max_holding_time": 7776000,  # 最大 90天
            "trade_frequency": "low",
        },
        "parameter_preferences": {
            "stop_loss_percent": 5.0,  # 宽止损
            "take_profit_percent": 15.0,  # 大止盈
            "trailing_stop_activation": 8.0,
            "trailing_stop_callback": 3.0,
            "position_monitor_interval": 3600,  # 1小时
        },
        "optimization_focus": {
            "execution_speed": 0.05,
            "win_rate": 0.15,
            "profit_per_trade": 0.6,  # 最重视单笔利润
            "trade_frequency": 0.2,
        },
    },
}


# ============ 组合策略配置 ============

COMBINED_PROFILES = {
    "conservative_scalping": {
        "name": "稳健剥头皮",
        "risk_profile": "conservative",
        "trading_style": "scalping",
        "description": "低风险的超短线交易，追求稳定的小额利润",
    },
    "conservative_swing": {
        "name": "稳健波段",
        "risk_profile": "conservative",
        "trading_style": "swing_trading",
        "description": "低风险的中线交易，适合稳健投资者",
    },
    "balanced_day": {
        "name": "平衡日内",
        "risk_profile": "balanced",
        "trading_style": "day_trading",
        "description": "平衡风险的日内交易，最常见的交易方式",
    },
    "balanced_swing": {
        "name": "平衡波段",
        "risk_profile": "balanced",
        "trading_style": "swing_trading",
        "description": "平衡风险的波段交易，适合上班族",
    },
    "aggressive_scalping": {
        "name": "激进剥头皮",
        "risk_profile": "aggressive",
        "trading_style": "scalping",
        "description": "高频高风险交易，追求快速盈利",
    },
    "aggressive_day": {
        "name": "激进日内",
        "risk_profile": "aggressive",
        "trading_style": "day_trading",
        "description": "激进的日内交易，高风险高收益",
    },
}


def get_profile_config(profile_id: str) -> Dict[str, Any]:
    """
    获取完整的策略配置

    Args:
        profile_id: 策略 ID (如 "balanced_day")

    Returns:
        Dict: 完整的策略配置
    """
    if profile_id not in COMBINED_PROFILES:
        # 默认返回平衡日内
        profile_id = "balanced_day"

    combined = COMBINED_PROFILES[profile_id]
    risk_profile = RISK_PROFILES[combined["risk_profile"]]
    trading_style = TRADING_STYLES[combined["trading_style"]]

    return {
        "profile_id": profile_id,
        "name": combined["name"],
        "description": combined["description"],
        "risk_profile": risk_profile,
        "trading_style": trading_style,
    }


def get_optimization_prompt_suffix(profile_id: str) -> str:
    """
    根据策略配置生成优化 prompt 后缀

    Args:
        profile_id: 策略 ID

    Returns:
        str: Prompt 后缀
    """
    config = get_profile_config(profile_id)
    risk = config["risk_profile"]
    style = config["trading_style"]

    prompt = f"""
**策略配置: {config['name']}**
- 风险偏好: {risk['name']} - {risk['description']}
- 交易风格: {style['name']} - {style['description']}
- 时间周期: {style['time_horizon']}

**优化目标权重:**
- 胜率: {risk['optimization_goals']['win_rate_weight']:.1f}
- 盈利: {risk['optimization_goals']['profit_weight']:.1f}
- 风险控制: {risk['optimization_goals']['risk_weight']:.1f}
- 夏普比率: {risk['optimization_goals']['sharpe_ratio_weight']:.1f}
- 最大回撤: {risk['optimization_goals']['max_drawdown_weight']:.1f}

**交易风格关注点:**
- 执行速度: {style['optimization_focus']['execution_speed']:.1f}
- 胜率: {style['optimization_focus']['win_rate']:.1f}
- 单笔利润: {style['optimization_focus']['profit_per_trade']:.1f}
- 交易频率: {style['optimization_focus']['trade_frequency']:.1f}

**参数约束:**
- 最大杠杆: {risk['parameter_constraints']['max_leverage']}x
- 最大单仓位: {risk['parameter_constraints']['max_position_percent']}%
- 最低信心度: {risk['parameter_constraints']['min_confidence_threshold']}
- 止损范围: {risk['parameter_constraints']['stop_loss_range']}%
- 止盈范围: {risk['parameter_constraints']['take_profit_range']}%

**进化策略:**
- 最大参数变化: {risk['evolution_strategy']['max_parameter_change'] * 100:.0f}%
- 需要 A/B 测试: {'是' if risk['evolution_strategy']['require_ab_test'] else '否'}
- 最小改进要求: {risk['evolution_strategy']['min_improvement']}%

请根据以上策略配置生成优化建议，确保参数在约束范围内，并符合该策略的优化目标。
"""

    return prompt


def validate_parameters(profile_id: str, parameters: Dict[str, Any]) -> tuple[bool, str]:
    """
    验证参数是否符合策略约束

    Args:
        profile_id: 策略 ID
        parameters: 参数字典

    Returns:
        tuple: (是否有效, 错误信息)
    """
    config = get_profile_config(profile_id)
    constraints = config["risk_profile"]["parameter_constraints"]

    # 验证信心度阈值
    if "confidence_threshold" in parameters:
        if parameters["confidence_threshold"] < constraints["min_confidence_threshold"]:
            return False, f"信心度阈值不能低于 {constraints['min_confidence_threshold']}"

    # 验证止损范围
    if "stop_loss_multiplier" in parameters:
        sl_range = constraints["stop_loss_range"]
        # 这里简化验证，实际应该结合基础止损值
        if parameters["stop_loss_multiplier"] < 0.5 or parameters["stop_loss_multiplier"] > 2.0:
            return False, f"止损倍数应在 0.5-2.0 范围内"

    # 验证止盈范围
    if "take_profit_multiplier" in parameters:
        tp_range = constraints["take_profit_range"]
        if parameters["take_profit_multiplier"] < 0.5 or parameters["take_profit_multiplier"] > 2.0:
            return False, f"止盈倍数应在 0.5-2.0 范围内"

    return True, ""


if __name__ == "__main__":
    # 测试
    import json

    print("AI Evolution Strategy Profiles 测试")
    print("=" * 60)

    # 列出所有策略
    print("\n可用策略:")
    for profile_id, profile in COMBINED_PROFILES.items():
        print(f"  {profile_id}: {profile['name']} - {profile['description']}")

    # 测试获取配置
    print("\n\n测试: balanced_day 配置")
    config = get_profile_config("balanced_day")
    print(json.dumps(config, indent=2, ensure_ascii=False))

    # 测试 prompt 生成
    print("\n\n测试: Prompt 后缀")
    prompt_suffix = get_optimization_prompt_suffix("aggressive_scalping")
    print(prompt_suffix)

    # 测试参数验证
    print("\n\n测试: 参数验证")
    test_params = {
        "confidence_threshold": 0.5,
        "stop_loss_multiplier": 1.0,
        "take_profit_multiplier": 1.5,
    }
    valid, error = validate_parameters("conservative_swing", test_params)
    print(f"参数: {test_params}")
    print(f"验证结果: {'通过' if valid else '失败'}")
    if not valid:
        print(f"错误: {error}")

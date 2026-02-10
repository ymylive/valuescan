#!/usr/bin/env python3
"""手动触发美股监控测试"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signal_monitor.market_alert import (
    fetch_us_market_batch,
    fetch_vix,
    analyze_us_market_impact,
    send_alert,
    load_config,
)

def main():
    print("=== 美股监控测试 ===\n")

    config = load_config()
    us_cfg = config.get("us_market", {})

    # 获取分类配置
    categories = us_cfg.get("categories", {
        "indices": ["SPY", "QQQ"],
        "tech": ["NVDA", "AAPL"],
        "crypto_stocks": ["COIN", "MSTR"],
        "macro": ["GLD"],
    })

    # 批量获取所有标的数据
    all_symbols = []
    for syms in categories.values():
        all_symbols.extend(syms)

    print(f"获取 {len(all_symbols)} 个标的数据...")
    market_data = fetch_us_market_batch(all_symbols)
    print(f"成功获取 {len(market_data)} 个\n")

    # 获取VIX
    vix = fetch_vix()
    print(f"VIX: {vix}\n")

    # 构建消息
    from datetime import datetime, timezone, timedelta
    NY_TZ = timezone(timedelta(hours=-5))
    now = datetime.now(NY_TZ)

    lines = []

    # 判断整体方向
    indices = categories.get("indices", [])
    idx_changes = [market_data[s]["change_pct"] for s in indices if s in market_data]
    avg_change = sum(idx_changes) / len(idx_changes) if idx_changes else 0

    if avg_change > 0.5:
        emoji, direction = "📈", "上涨"
    elif avg_change < -0.5:
        emoji, direction = "📉", "下跌"
    else:
        emoji, direction = "➡️", "平开"

    lines.append(f"{emoji} <b>美股监控测试 - {direction}</b>")
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
    if us_cfg.get("ai_analysis_enabled", False):
        try:
            from signal_monitor.ai_signal_analysis import analyze_signal
            impact_data = analyze_us_market_impact(market_data, vix)
            print("调用AI分析...")
            ai_result = analyze_signal("US_MARKET", signal_payload={"us_market": impact_data})
            if ai_result and ai_result.get("analysis"):
                analysis = ai_result["analysis"]
                message += f"\n\n<b>🤖 AI分析 (对加密市场影响):</b>\n{analysis}"
                print(f"AI分析完成: {analysis[:100]}...")
        except Exception as e:
            print(f"AI分析失败: {e}")

    print("\n=== 发送消息 ===")
    print(message)
    print("\n")

    # 发送
    success = send_alert(message)
    print(f"发送结果: {'成功' if success else '失败'}")

if __name__ == "__main__":
    main()

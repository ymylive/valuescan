#!/usr/bin/env python3
"""Test Telegram info flow and AI analysis with BTC as example"""
import sys
import os
sys.path.insert(0, str(__file__).rsplit('scripts', 1)[0])
os.chdir(str(__file__).rsplit('scripts', 1)[0])

from valuescan_api import get_main_force, get_hold_cost, get_keyword

print("=" * 60)
print("BTC Telegram 信息流 + AI 市场分析测试")
print("=" * 60)

# 1. 获取 BTC 数据
print("\n【1. 获取 BTC ValuScan 数据】")
btc_kw = get_keyword("BTC")
print(f"BTC keyword: {btc_kw}")

mf = get_main_force("BTC", 14)
hc = get_hold_cost("BTC", 14)

mf_data = mf.get("data", [])
hc_data = hc.get("data", {})

current_mf = float(mf_data[-1]["price"]) if mf_data else None
holding = hc_data.get("holdingPrice", [])
current_hc = float(holding[-1]["val"]) if holding else None

print(f"主力位: ${current_mf:,.2f}" if current_mf else "主力位: N/A")
print(f"主力成本: ${current_hc:,.2f}" if current_hc else "主力成本: N/A")

# 2. 模拟 Telegram 消息格式
print("\n【2. Telegram 消息格式预览】")
telegram_msg = f"""
📊 *BTC 市场分析*

🟢 *主力位*: ${current_mf:,.2f}
💰 *主力成本*: ${current_hc:,.2f}

📈 *技术分析*:
- 当前价格相对主力位
- 主力成本支撑位

⏰ 数据有效期: 14 天
"""
print(telegram_msg)

# 3. AI 市场分析
print("\n【3. AI 市场分析模块测试】")
try:
    from signal_monitor.ai_market_summary import AIMarketSummary
    
    ai = AIMarketSummary()
    print("✓ AIMarketSummary 模块加载成功")
    
    # 检查配置
    config = ai.get_config() if hasattr(ai, 'get_config') else {}
    print(f"  - AI 模型配置: {config.get('model', 'default')}")
    
except ImportError as e:
    print(f"✗ AIMarketSummary 模块加载失败: {e}")
except Exception as e:
    print(f"✗ AI 模块错误: {e}")

# 4. AI 简评测试
print("\n【4. AI 简评模块测试】")
try:
    from signal_monitor.ai_signal_analyzer import AISignalAnalyzer
    
    analyzer = AISignalAnalyzer()
    print("✓ AISignalAnalyzer 模块加载成功")
    
except ImportError as e:
    print(f"✗ AISignalAnalyzer 模块加载失败: {e}")
except Exception as e:
    print(f"✗ AI 分析器错误: {e}")

# 5. 生成简评
print("\n【5. 生成 BTC 简评】")
btc_summary = f"""
🔍 *BTC 快速简评*

📊 核心数据:
• 主力位: ${current_mf:,.2f} (14日)
• 主力成本: ${current_hc:,.2f}
• 价差: ${abs(current_mf - current_hc):,.2f} ({((current_mf - current_hc) / current_hc * 100):.1f}%)

💡 解读:
{'• 主力位高于主力成本，市场处于获利状态' if current_mf > current_hc else '• 主力位低于主力成本，市场承压'}
• 主力成本可作为中长期支撑参考

⚠️ 本分析基于 ValuScan 数据，仅供参考
"""
print(btc_summary)

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)

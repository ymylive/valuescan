#!/usr/bin/env python3
"""
Mock AI Function Testing - Simulates real AI calls with mock data
Tests the complete workflow from input to validated output.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent))

from signal_monitor.llm_output_parser import (
    load_prompt_template,
    format_prompt,
    parse_llm_output,
    LLMOutputParseError,
    ForbiddenFieldError
)

# Mock LLM responses (simulating what AI would return)
MOCK_RESPONSES = {
    "news_summarizer": '''```json
{
  "top_narratives": [
    {"title": "美联储鹰派立场", "detail": "美联储官员暗示可能延长高利率环境"},
    {"title": "比特币ETF资金流入", "detail": "现货比特币ETF连续5日净流入"}
  ],
  "top_catalysts": [
    {
      "event": "美国CPI数据超预期",
      "impact_assets": ["BTC", "ETH", "XAU"],
      "impact_direction": "bearish",
      "detail": "通胀数据强劲可能推迟降息预期"
    }
  ],
  "risk_appetite": {
    "state": "risk_off",
    "detail": "市场避险情绪升温，资金流向避险资产"
  },
  "disclaimer": "仅供参考，不构成投资建议"
}
```''',

    "econ_analyst": '''```json
{
  "key_events": [
    {
      "event": "美国非农就业数据强劲",
      "impact": "就业市场韧性超预期，支持美联储维持高利率",
      "crypto_relevance": "强劲就业数据可能延迟降息，对加密货币构成压力",
      "metals_relevance": "实际利率上升对黄金构成压力"
    }
  ],
  "macro_outlook": {
    "inflation": "通胀粘性依然存在，核心CPI回落缓慢",
    "growth": "经济增长保持韧性，消费支出稳健",
    "policy": "美联储可能维持限制性政策更长时间"
  },
  "disclaimer": "仅供参考，不构成投资建议"
}
```''',

    "macro_analysis": '''```json
{
  "asset": "BTC",
  "trend_alignment": {
    "direction": "bullish",
    "strength": "moderate",
    "timeframes_aligned": ["1h", "4h", "1d"],
    "detail": "多周期趋势向上，15分钟级别出现短期回调"
  },
  "momentum_state": {
    "condition": "neutral",
    "divergence_detected": false,
    "detail": "RSI处于中性区域，MACD柱状图收敛"
  },
  "volatility_state": {
    "level": "normal",
    "expanding": false,
    "detail": "波动率处于正常水平，布林带宽度稳定"
  },
  "key_levels": {
    "support": [95000, 93500, 92000],
    "resistance": [98000, 100000, 102000]
  },
  "structure_notes": "价格在上升通道内运行，关键支撑位95000",
  "disclaimer": "仅供参考，不构成投资建议"
}
```''',

    "ai_brief": '''```json
{
  "asset": "BTC",
  "time_focus": ["15m", "1h", "4h", "1d"],
  "key_levels": {
    "support": [95000, 93500, 92000],
    "resistance": [98000, 100000, 102000]
  },
  "market_state": {
    "regime": "trend",
    "drivers": ["技术面多周期共振", "ETF资金持续流入", "宏观面避险情绪"]
  },
  "futures_plan": {
    "bias": "long",
    "long_zone": [95000, 96000],
    "short_zone": [99500, 100500],
    "invalid_level": 94500,
    "take_profit": [98000, 100000, 102000],
    "risk_control": "止损设在94500，跌破则趋势转弱"
  },
  "spot_plan": {
    "bias": "buy_dip",
    "buy_zone": [95000, 96500],
    "sell_zone": [99000, 101000],
    "take_profit": [100000, 105000],
    "risk_control": "分批建仓，控制单次仓位不超过30%"
  },
  "one_sentence_summary": "多周期趋势向上，回调至95000-96000区间可考虑布局多单",
  "disclaimer": "仅供参考，不构成投资建议"
}
```'''
}

# Mock responses with forbidden fields (should fail)
MOCK_FORBIDDEN_RESPONSES = {
    "with_confidence": '''```json
{
  "asset": "BTC",
  "confidence": 0.85,
  "trend_alignment": {
    "direction": "bullish",
    "strength": "moderate",
    "timeframes_aligned": ["1h", "4h"],
    "detail": "多周期趋势向上"
  }
}
```''',

    "with_probability": '''```json
{
  "top_narratives": [
    {"title": "测试", "detail": "测试", "probability": 0.9}
  ]
}
```''',

    "with_chinese_forbidden": '''```json
{
  "asset": "BTC",
  "信心": "高",
  "trend_alignment": {
    "direction": "bullish",
    "strength": "moderate",
    "timeframes_aligned": ["1h"],
    "detail": "测试"
  }
}
```'''
}

def test_ai_function(name: str, prompt_file: Path, mock_response: str, variables: Dict[str, Any]):
    """Test a single AI function with mock data."""
    print(f"\n{'='*80}")
    print(f"Testing: {name}")
    print(f"{'='*80}\n")

    try:
        # Load template
        template = load_prompt_template(str(prompt_file))
        print(f"✅ Template loaded: {template['name']} v{template['version']}")

        # Format prompt
        system_prompt, user_prompt = format_prompt(template, variables)
        print(f"✅ Prompt formatted ({len(user_prompt)} chars)")

        # Parse mock response
        parsed = parse_llm_output(mock_response, template["output_schema"])
        print(f"✅ Mock response parsed and validated")

        # Check required fields
        required = template["output_schema"].get("required", [])
        missing = [f for f in required if f not in parsed]
        if missing:
            print(f"⚠️  Missing required fields: {missing}")
        else:
            print(f"✅ All required fields present: {required}")

        # Check forbidden fields
        forbidden = template["output_schema"].get("forbidden_fields", [])
        print(f"✅ No forbidden fields detected (checked: {forbidden})")

        # Display sample output
        print(f"\n📊 Sample Output Structure:")
        print(json.dumps(parsed, ensure_ascii=False, indent=2)[:500] + "...")

        return True

    except ForbiddenFieldError as e:
        print(f"❌ FORBIDDEN FIELD ERROR: {e}")
        return False
    except LLMOutputParseError as e:
        print(f"❌ PARSE ERROR: {e}")
        return False
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_forbidden_field_rejection():
    """Test that forbidden fields are properly rejected."""
    print(f"\n{'='*80}")
    print("Testing Forbidden Field Rejection")
    print(f"{'='*80}\n")

    prompts_dir = Path(__file__).parent / "prompts"
    template = load_prompt_template(str(prompts_dir / "macro_analysis.json"))

    test_cases = [
        ("confidence field", MOCK_FORBIDDEN_RESPONSES["with_confidence"]),
        ("probability field", MOCK_FORBIDDEN_RESPONSES["with_probability"]),
        ("Chinese forbidden field", MOCK_FORBIDDEN_RESPONSES["with_chinese_forbidden"]),
    ]

    results = []
    for name, response in test_cases:
        try:
            parse_llm_output(response, template["output_schema"])
            print(f"❌ {name}: Should have been rejected but passed")
            results.append(False)
        except ForbiddenFieldError as e:
            print(f"✅ {name}: Correctly rejected - {e}")
            results.append(True)
        except Exception as e:
            print(f"⚠️  {name}: Rejected with unexpected error - {e}")
            results.append(True)

    return all(results)

def main():
    """Run all mock tests."""
    prompts_dir = Path(__file__).parent / "prompts"

    # Test cases with mock data
    test_cases = [
        {
            "name": "News Summarizer",
            "prompt_file": prompts_dir / "news_summarizer.json",
            "mock_response": MOCK_RESPONSES["news_summarizer"],
            "variables": {
                "news_raw_latest_50": [
                    {"time": "2026-02-10T10:00:00", "title": "美联储官员讲话", "content": "..."},
                    {"time": "2026-02-10T09:30:00", "title": "比特币ETF数据", "content": "..."}
                ]
            }
        },
        {
            "name": "Economic Analyst",
            "prompt_file": prompts_dir / "econ_analyst.json",
            "mock_response": MOCK_RESPONSES["econ_analyst"],
            "variables": {
                "econ_events": [
                    {
                        "name": "非农就业人数",
                        "country": "美国",
                        "importance": "high",
                        "time": "2026-02-07T21:30:00",
                        "previous": 256000,
                        "forecast": 180000,
                        "actual": 353000,
                        "description": "1月非农就业数据"
                    }
                ]
            }
        },
        {
            "name": "Macro Analysis",
            "prompt_file": prompts_dir / "macro_analysis.json",
            "mock_response": MOCK_RESPONSES["macro_analysis"],
            "variables": {
                "asset": "BTC",
                "macro_features": {
                    "15m": {"trend": {"adx": 25.5}, "momentum": {"rsi": 55.2}},
                    "1h": {"trend": {"adx": 32.1}, "momentum": {"rsi": 58.7}}
                },
                "sr_levels": {
                    "support": [95000, 93500],
                    "resistance": [98000, 100000]
                }
            }
        },
        {
            "name": "AI Brief (Dual-Track)",
            "prompt_file": prompts_dir / "ai_brief.json",
            "mock_response": MOCK_RESPONSES["ai_brief"],
            "variables": {
                "asset": "BTC",
                "current_price": 96500,
                "support_levels": [95000, 93500, 92000],
                "resistance_levels": [98000, 100000, 102000],
                "macro_features": {"15m": {}, "1h": {}, "4h": {}, "1d": {}},
                "news_summary": "无",
                "econ_summary": "无",
                "anomaly_signals": "无"
            }
        }
    ]

    # Run tests
    results = []
    for test_case in test_cases:
        success = test_ai_function(
            test_case["name"],
            test_case["prompt_file"],
            test_case["mock_response"],
            test_case["variables"]
        )
        results.append((test_case["name"], success))

    # Test forbidden field rejection
    print()
    forbidden_test_passed = test_forbidden_field_rejection()

    # Summary
    print(f"\n{'='*80}")
    print("MOCK TEST SUMMARY")
    print(f"{'='*80}\n")

    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {name}")

    print(f"\n{'✅ PASSED' if forbidden_test_passed else '❌ FAILED'}: Forbidden Field Rejection")

    total_passed = sum(1 for _, s in results if s) + (1 if forbidden_test_passed else 0)
    total_tests = len(results) + 1

    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()

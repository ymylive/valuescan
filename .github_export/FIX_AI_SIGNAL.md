# AI Signal Analysis Fix

## Problem
The `_build_prompt` function in `signal_monitor/ai_signal_analysis.py` had duplicate return statements causing the Chinese prompt to never be returned, resulting in a `None` value being passed to the AI API.

## Error Message
```
2025-12-28 17:36:13 [WARNING] AI API call failed: 422 - {"detail":[{"loc":["body","messages",1,"content"],"msg":"none is not an allowed value","type":"type_error.none.not_allowed"}]}
```

## Root Cause
Lines 394-415 contained unreachable duplicate code after the English return statement at line 357. The function structure was:

```python
def _build_prompt(...):
    # ... setup code ...

    if language == "en":
        return f"""..."""  # Line 357 - returns for English

    # Lines 358-393: _build_key_levels_prompt function definition (WRONG LOCATION!)

    # Lines 394-415: Unreachable duplicate Chinese prompt (NEVER EXECUTED!)
    return f"""你是资深量化分析师..."""
```

## Solution
Remove lines 394-415 (the unreachable duplicate Chinese prompt) and add the Chinese prompt immediately after the English return statement:

```python
def _build_prompt(...):
    # ... setup code ...

    if language == "en":
        return f"""..."""  # English prompt

    # Chinese prompt (immediately after English)
    return f"""你是资深量化分析师。分析该币种和信号，给出是否入场的判断，如入场则设置止盈止损位（盈亏比>2），并给出充分理由、未来走势和风险系数。
仅返回严格的 JSON，不要额外文字。
JSON 格式:
{{"analysis":"...","supports":[...],"resistances":[...],"stop_loss":0,"take_profit":0,"rr":0,"risk_level":"低/中/高","entry_decision":"是/否","overlays":[{{"x1":0,"y1":0,"x2":0,"y2":0,"style":"dashed","label":"channel_top","type":"channel"}}]}}
要求:
1) analysis: 约200字。必须包含：
   - 币种分析（当前价格、趋势、成交量、市值等关键数据）
   - 信号分析（信号类型、强度、可靠性评估）
   - 是否入场判断（是/否，附详细理由，必须基于数据支撑）
   - 如入场：止盈止损位设置及理由（必须引用订单簿关键位、Taker资金流、形态支撑）
   - 未来可能走势（短期走势预测，附概率评估）
   - 风险系数评估（风险等级及主要风险因素）
2) supports/resistances: 基于多源数据（订单簿堆积、Taker资金流偏向、形态关键点）返回1-3个关键位。
3) 支撑位 < 当前价 < 阻力位。
4) stop_loss < price < take_profit。rr（盈亏比）必须 > 2.0。
5) risk_level: "低"（盈亏比>3，支撑强）、"中"（盈亏比2-3）、"高"（盈亏比<2.5或支撑弱）。
6) entry_decision: 信号强且盈亏比>2时为"是"，否则为"否"。
7) overlays: 从 overlay_candidates 选择，|x2-x1|>=20，y1/y2在价格范围内。
8) 如信号显示FOMO加剧或资金异动，设置 risk_level="高" 并在分析中警示。
9) analysis 必须引用具体数据（订单簿堆积量、Taker资金流比例、K线关键价位）并说明为何这些位置对做市商重要。
输入数据 (JSON):
{payload_json}"""
```

## Manual Fix Steps

1. SSH to VPS:
   ```bash
   ssh root@valuescan.io
   ```

2. Edit the file:
   ```bash
   cd /root/valuescan/signal_monitor
   nano ai_signal_analysis.py
   ```

3. Find line 357 (the English return statement ending with `{payload_json}"""`)

4. Delete lines 394-415 (the duplicate unreachable Chinese prompt)

5. After line 357, add a blank line and then add the Chinese prompt return statement (shown above)

6. Save and restart the service:
   ```bash
   sudo systemctl restart valuescan-signal
   ```

7. Check logs:
   ```bash
   sudo journalctl -u valuescan-signal -f
   ```

## Verification
After the fix, when a signal triggers AI analysis, you should see:
- No more 422 errors about "none is not an allowed value"
- AI analysis completing successfully with Chinese output
- Telegram messages containing the AI analysis text

## Files Changed
- `signal_monitor/ai_signal_analysis.py` (lines 358-415)

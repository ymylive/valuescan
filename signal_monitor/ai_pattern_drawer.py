"""
AI辅助线绘制模块
使用AI来识别和绘制图表形态
"""

import json
import requests
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd
from logger import logger


def build_pattern_prompt(
    symbol: str,
    df: pd.DataFrame,
    current_price: float,
    local_patterns: Dict[str, Any],
    language: str = "zh"
) -> str:
    """
    构建AI形态识别的Prompt
    """
    # 准备K线数据
    klines = []
    if 'timestamp' in df.columns:
        ts_ms = (df['timestamp'].astype('int64') // 10**6).astype('int64')
        for i, row in df.reset_index(drop=True).iterrows():
            klines.append({
                'ts': int(ts_ms.iloc[i]),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume']),
            })

    # 准备本地检测的形态信息
    local_pattern_summary = {}
    for pattern_name, pattern_data in local_patterns.items():
        if pattern_data and isinstance(pattern_data, dict):
            local_pattern_summary[pattern_name] = {
                'type': pattern_data.get('type'),
                'score': pattern_data.get('score'),
                'strength': pattern_data.get('strength'),
                'window': pattern_data.get('window'),
            }

    payload = {
        'symbol': symbol,
        'current_price': current_price,
        'klines': klines[-100:],  # 只发送最近100根K线
        'local_patterns': local_pattern_summary,
    }

    payload_json = json.dumps(payload, ensure_ascii=False)

    if language == "en":
        return f"""You are a professional technical analyst. Analyze the chart and identify trend lines and patterns.

Input data (JSON):
{payload_json}

Requirements:
1. Identify the most significant trend lines and patterns from the klines data
2. For each pattern, provide:
   - Pattern type: channel/wedge/triangle/flag/trendline
   - Coordinates: x1, y1, x2, y2 (x is kline index, y is price)
   - Style: solid/dashed/dotted
   - Label: brief description
   - Confidence: 0-1 score
3. Validate against local_patterns if provided
4. Lines must:
   - Touch at least 2 pivot points (highs for resistance, lows for support)
   - Have length >= 20 bars
   - Be within price range
5. Return ONLY strict JSON, no extra text

JSON format:
{{
  "patterns": [
    {{
      "type": "channel",
      "lines": [
        {{"x1": 0, "y1": 0, "x2": 100, "y2": 0, "style": "solid", "label": "upper", "role": "resistance"}},
        {{"x1": 0, "y1": 0, "x2": 100, "y2": 0, "style": "solid", "label": "lower", "role": "support"}}
      ],
      "confidence": 0.85,
      "description": "Ascending channel"
    }}
  ],
  "trendlines": [
    {{"x1": 0, "y1": 0, "x2": 100, "y2": 0, "style": "dashed", "label": "support", "confidence": 0.75}}
  ]
}}"""

    return f"""你是专业的技术分析师。分析图表并识别趋势线和形态。

输入数据 (JSON):
{payload_json}

要求:
1. 从K线数据中识别最重要的趋势线和形态
2. 对于每个形态，提供:
   - 形态类型: channel/wedge/triangle/flag/trendline
   - 坐标: x1, y1, x2, y2 (x是K线索引, y是价格)
   - 样式: solid/dashed/dotted
   - 标签: 简短描述
   - 置信度: 0-1分数
3. 如果提供了local_patterns，进行验证
4. 线条必须:
   - 至少触碰2个枢轴点（阻力线触碰高点，支撑线触碰低点）
   - 长度 >= 20根K线
   - 在价格范围内
5. 只返回严格的JSON，不要额外文本

JSON格式:
{{
  "patterns": [
    {{
      "type": "channel",
      "lines": [
        {{"x1": 0, "y1": 0, "x2": 100, "y2": 0, "style": "solid", "label": "上轨", "role": "resistance"}},
        {{"x1": 0, "y1": 0, "x2": 100, "y2": 0, "style": "solid", "label": "下轨", "role": "support"}}
      ],
      "confidence": 0.85,
      "description": "上升通道"
    }}
  ],
  "trendlines": [
    {{"x1": 0, "y1": 0, "x2": 100, "y2": 0, "style": "dashed", "label": "支撑", "confidence": 0.75}}
  ]
}}"""


def call_ai_pattern_api(prompt: str, config: Dict[str, Any]) -> Optional[str]:
    """
    调用AI API进行形态识别
    """
    api_key = (config.get('api_key') or '').strip()
    api_url = (config.get('api_url') or '').strip()
    model = (config.get('model') or '').strip()

    if not api_key or not api_url or not model:
        return None

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': 'You are a professional technical analyst. Reply with strict JSON only.'},
            {'role': 'user', 'content': prompt}
        ],
        'max_tokens': 8000,
        'temperature': 0.3,
    }

    try:
        session = requests.Session()
        session.trust_env = False
        resp = session.post(api_url, headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            logger.warning(f"AI pattern API call failed: {resp.status_code} - {resp.text[:200]}")
            return None

        data = resp.json()
        content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
        if not content:
            return None

        return content.strip()
    except Exception as exc:
        logger.warning(f"AI pattern API call error: {exc}")
        return None


def parse_ai_pattern_response(raw: str) -> Dict[str, Any]:
    """
    解析AI返回的形态数据
    """
    if not raw:
        return {'patterns': [], 'trendlines': []}

    cleaned = raw.strip()

    # 尝试直接解析
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # 尝试提取JSON
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            data = json.loads(cleaned[start:end + 1])
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    logger.warning("Failed to parse AI pattern response")
    return {'patterns': [], 'trendlines': []}


def validate_line(line: Dict[str, Any], df: pd.DataFrame, min_length: int = 20) -> bool:
    """
    验证线条的有效性
    """
    try:
        x1 = float(line.get('x1', 0))
        y1 = float(line.get('y1', 0))
        x2 = float(line.get('x2', 0))
        y2 = float(line.get('y2', 0))
    except (ValueError, TypeError):
        return False

    # 检查长度
    if abs(x2 - x1) < min_length:
        return False

    # 检查索引范围
    max_idx = len(df) - 1
    if not (0 <= x1 <= max_idx and 0 <= x2 <= max_idx):
        return False

    # 检查价格范围
    price_min = df['low'].min() * 0.95
    price_max = df['high'].max() * 1.05
    if not (price_min <= y1 <= price_max and price_min <= y2 <= price_max):
        return False

    return True


def validate_pattern_touches(line: Dict[str, Any], df: pd.DataFrame,
                              role: str = 'support', min_touches: int = 2) -> Tuple[bool, int]:
    """
    验证线条是否触碰足够的枢轴点
    返回: (是否有效, 触碰次数)
    """
    try:
        x1 = int(line.get('x1', 0))
        y1 = float(line.get('y1', 0))
        x2 = int(line.get('x2', 0))
        y2 = float(line.get('y2', 0))
    except (ValueError, TypeError):
        return False, 0

    if x2 == x1:
        return False, 0

    # 计算线性方程
    slope = (y2 - y1) / (x2 - x1)
    intercept = y1 - slope * x1

    # 选择要检查的序列
    if role == 'resistance':
        series = df['high'].values
    else:
        series = df['low'].values

    # 计算容差
    atr = (df['high'] - df['low']).rolling(14).mean().iloc[-1]
    tolerance = atr * 0.5

    # 计算触碰次数
    touches = 0
    for i in range(max(0, x1), min(len(series), x2 + 1)):
        line_value = slope * i + intercept
        if abs(series[i] - line_value) <= tolerance:
            touches += 1

    return touches >= min_touches, touches


def merge_ai_and_local_patterns(
    ai_patterns: Dict[str, Any],
    local_patterns: Dict[str, Any],
    df: pd.DataFrame
) -> List[Dict[str, Any]]:
    """
    融合AI和本地检测的形态
    策略：
    1. 优先使用高置信度的AI形态
    2. 验证AI形态的触碰次数
    3. 如果AI形态不足，补充本地形态
    """
    merged_lines = []

    # 1. 处理AI形态
    ai_pattern_list = ai_patterns.get('patterns', [])
    for pattern in ai_pattern_list:
        if not isinstance(pattern, dict):
            continue

        confidence = float(pattern.get('confidence', 0))
        if confidence < 0.6:  # 置信度太低
            continue

        lines = pattern.get('lines', [])
        for line in lines:
            if not isinstance(line, dict):
                continue

            # 验证线条
            if not validate_line(line, df):
                continue

            # 验证触碰
            role = line.get('role', 'support')
            is_valid, touch_count = validate_pattern_touches(line, df, role)
            if not is_valid:
                continue

            # 添加元数据
            line['source'] = 'AI'
            line['pattern_type'] = pattern.get('type')
            line['confidence'] = confidence
            line['touch_count'] = touch_count

            merged_lines.append(line)

    # 2. 处理AI趋势线
    ai_trendlines = ai_patterns.get('trendlines', [])
    for line in ai_trendlines:
        if not isinstance(line, dict):
            continue

        confidence = float(line.get('confidence', 0))
        if confidence < 0.6:
            continue

        if not validate_line(line, df):
            continue

        # 验证触碰
        role = line.get('role', 'support')
        is_valid, touch_count = validate_pattern_touches(line, df, role)
        if not is_valid:
            continue

        line['source'] = 'AI'
        line['pattern_type'] = 'trendline'
        line['touch_count'] = touch_count

        merged_lines.append(line)

    # 3. 如果AI形态不足，补充本地形态
    if len(merged_lines) < 2:
        for pattern_name, pattern_data in local_patterns.items():
            if not pattern_data or not isinstance(pattern_data, dict):
                continue

            score = pattern_data.get('score', 0)
            if score < 0.6:
                continue

            upper = pattern_data.get('upper')
            lower = pattern_data.get('lower')
            window = pattern_data.get('window', 60)

            if not (isinstance(upper, (list, tuple)) and isinstance(lower, (list, tuple))):
                continue

            slope_u, intercept_u = float(upper[0]), float(upper[1])
            slope_l, intercept_l = float(lower[0]), float(lower[1])

            x_start = len(df) - window
            x_end = len(df) - 1

            # 上轨
            merged_lines.append({
                'x1': x_start,
                'y1': slope_u * x_start + intercept_u,
                'x2': x_end,
                'y2': slope_u * x_end + intercept_u,
                'style': 'solid',
                'label': f'{pattern_name}_upper',
                'role': 'resistance',
                'source': 'LOCAL',
                'pattern_type': pattern_name,
                'confidence': score,
            })

            # 下轨
            merged_lines.append({
                'x1': x_start,
                'y1': slope_l * x_start + intercept_l,
                'x2': x_end,
                'y2': slope_l * x_end + intercept_l,
                'style': 'solid',
                'label': f'{pattern_name}_lower',
                'role': 'support',
                'source': 'LOCAL',
                'pattern_type': pattern_name,
                'confidence': score,
            })

    return merged_lines


def draw_ai_patterns(
    symbol: str,
    df: pd.DataFrame,
    current_price: float,
    local_patterns: Dict[str, Any],
    config: Dict[str, Any],
    language: str = "zh"
) -> List[Dict[str, Any]]:
    """
    使用AI绘制形态辅助线
    返回: 线条列表
    """
    # 1. 构建Prompt
    prompt = build_pattern_prompt(symbol, df, current_price, local_patterns, language)

    # 2. 调用AI API
    raw_response = call_ai_pattern_api(prompt, config)
    if not raw_response:
        logger.info("AI pattern detection not available, using local patterns only")
        # 返回本地形态
        return merge_ai_and_local_patterns({'patterns': [], 'trendlines': []}, local_patterns, df)

    # 3. 解析响应
    ai_patterns = parse_ai_pattern_response(raw_response)

    # 4. 融合AI和本地形态
    merged_lines = merge_ai_and_local_patterns(ai_patterns, local_patterns, df)

    logger.info(f"AI pattern detection: {len(merged_lines)} lines identified")

    return merged_lines


def get_pattern_color(pattern_type: str, role: str) -> str:
    """
    根据形态类型和角色返回颜色
    """
    if role == 'resistance':
        return '#F43F5E'  # 红色
    elif role == 'support':
        return '#10B981'  # 绿色
    else:
        return '#6366F1'  # 紫色


def get_pattern_style_params(confidence: float, source: str) -> Dict[str, Any]:
    """
    根据置信度和来源返回样式参数
    """
    if source == 'AI':
        if confidence >= 0.8:
            return {'linewidth': 1.8, 'alpha': 0.95, 'linestyle': '-'}
        elif confidence >= 0.6:
            return {'linewidth': 1.5, 'alpha': 0.85, 'linestyle': '-'}
        else:
            return {'linewidth': 1.2, 'alpha': 0.7, 'linestyle': '--'}
    else:  # LOCAL
        if confidence >= 0.7:
            return {'linewidth': 1.5, 'alpha': 0.85, 'linestyle': '-'}
        else:
            return {'linewidth': 1.2, 'alpha': 0.7, 'linestyle': '--'}

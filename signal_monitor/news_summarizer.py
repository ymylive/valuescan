"""LLM-based news summarization with strict JSON parsing."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

try:
    from signal_monitor.logger import logger
except Exception:
    from logger import logger

SUMMARY_PROMPT = """分析以下50条金十数据新闻，提取关键信息：

{news_json}

请严格按照以下JSON格式输出（不要包含任何其他文字）：

{{
  "top_narratives": [
    {{"title": "叙事标题", "detail": "详细说明"}},
    ...  // 最多5条
  ],
  "top_catalysts": [
    {{
      "event": "催化事件",
      "impact_assets": ["BTC", "ETH"],
      "impact_direction": "bullish|bearish|neutral",
      "detail": "影响说明"
    }},
    ...  // 最多5条
  ],
  "risk_appetite": {{
    "state": "risk_on|risk_off|neutral",
    "detail": "风险偏好说明"
  }}
}}
"""


def _call_llm(prompt: str) -> Optional[str]:
    """Call LLM API (placeholder for real implementation)."""
    # TODO: Implement real LLM API call (OpenAI, Anthropic, etc.)
    # For now, return None to indicate LLM unavailable
    return None


def _parse_json_strict(text: str) -> Optional[Dict[str, Any]]:
    """Parse JSON with strict validation."""
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            return None

        # Validate schema
        if "top_narratives" not in data or "top_catalysts" not in data or "risk_appetite" not in data:
            logger.warning("Missing required fields in LLM response")
            return None

        narratives = data.get("top_narratives", [])
        if not isinstance(narratives, list) or len(narratives) > 5:
            logger.warning("Invalid top_narratives format")
            return None

        catalysts = data.get("top_catalysts", [])
        if not isinstance(catalysts, list) or len(catalysts) > 5:
            logger.warning("Invalid top_catalysts format")
            return None

        risk = data.get("risk_appetite", {})
        if not isinstance(risk, dict) or "state" not in risk:
            logger.warning("Invalid risk_appetite format")
            return None

        if risk["state"] not in ("risk_on", "risk_off", "neutral"):
            logger.warning("Invalid risk_appetite state: %s", risk["state"])
            return None

        return data
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse LLM JSON response: %s", exc)
        return None


def summarize_news(news_items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Summarize news using LLM.

    Args:
        news_items: List of raw news items

    Returns:
        Structured summary matching SCHEMAS_V3.md format, or None if failed
    """
    if not news_items:
        logger.warning("No news items to summarize")
        return None

    # Prepare prompt
    news_json = json.dumps(news_items, ensure_ascii=False, indent=2)
    prompt = SUMMARY_PROMPT.format(news_json=news_json)

    # Call LLM
    response = _call_llm(prompt)
    if not response:
        logger.warning("LLM API unavailable for news summarization")
        return None

    # Parse and validate
    summary = _parse_json_strict(response)
    if not summary:
        logger.error("Failed to parse LLM response into valid JSON")
        return None

    logger.info("Successfully summarized %d news items", len(news_items))
    return summary

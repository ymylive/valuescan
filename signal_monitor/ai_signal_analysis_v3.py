#!/usr/bin/env python3
"""
AI Signal Analysis V3 - Refactored with externalized prompts and strict validation.

Uses prompt templates from prompts/ directory and llm_output_parser for validation.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from .llm_output_parser import (
        load_prompt_template,
        format_prompt,
        parse_llm_output,
        LLMOutputParseError,
        ForbiddenFieldError
    )
    from .ai_api_utils import build_payload, resolve_protocol_and_url, should_force_responses_stream
    from .ai_request_queue import call_ai_with_queue
    from .logger import logger
except Exception:
    from llm_output_parser import (
        load_prompt_template,
        format_prompt,
        parse_llm_output,
        LLMOutputParseError,
        ForbiddenFieldError
    )
    from ai_api_utils import build_payload, resolve_protocol_and_url, should_force_responses_stream
    from ai_request_queue import call_ai_with_queue
    from logger import logger

# Prompt file paths
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
PROMPT_NEWS_SUMMARIZER = PROMPTS_DIR / "news_summarizer.json"
PROMPT_ECON_ANALYST = PROMPTS_DIR / "econ_analyst.json"
PROMPT_MACRO_ANALYSIS = PROMPTS_DIR / "macro_analysis.json"
PROMPT_AI_BRIEF = PROMPTS_DIR / "ai_brief.json"


def _call_llm_with_retry(
    system_prompt: str,
    user_prompt: str,
    schema: Dict[str, Any],
    config: Dict[str, Any],
    max_retries: int = 2
) -> Optional[Dict[str, Any]]:
    """
    Call LLM API with retry logic for format errors only.

    Args:
        system_prompt: System prompt
        user_prompt: User prompt
        schema: JSON schema for validation
        config: AI API configuration
        max_retries: Maximum retry attempts

    Returns:
        Validated JSON output or None on failure
    """
    api_key = config.get("api_key", "").strip()
    api_url = config.get("api_url", "").strip()
    model = config.get("model", "").strip()

    if not api_key or not api_url or not model:
        logger.error("Missing AI API configuration")
        return None

    protocol, resolved_url = resolve_protocol_and_url(api_url, config.get("api_protocol"))
    stream = should_force_responses_stream(resolved_url, protocol)

    for attempt in range(max_retries + 1):
        try:
            # Build payload
            payload = build_payload(
                protocol,
                resolved_url,
                model,
                system_prompt,
                user_prompt,
                max_tokens=int(os.getenv("NOFX_AI_MAX_TOKENS", "8000")),
                temperature=0.7,
                stream=stream
            )

            # Call AI API via queue
            raw_response = call_ai_with_queue(
                url=resolved_url,
                payload=payload,
                api_key=api_key,
                timeout=int(os.getenv("NOFX_AI_API_TIMEOUT", "90")),
                protocol=protocol
            )

            if not raw_response:
                logger.error("Empty response from AI API")
                return None

            # Parse and validate output
            validated_output = parse_llm_output(raw_response, schema)
            logger.info(f"LLM output validated successfully on attempt {attempt + 1}")
            return validated_output

        except ForbiddenFieldError as e:
            # Content error - do not retry
            logger.error(f"Forbidden field detected: {e}")
            return None

        except LLMOutputParseError as e:
            # Format error - retry
            logger.warning(f"Parse error on attempt {attempt + 1}/{max_retries + 1}: {e}")
            if attempt >= max_retries:
                logger.error("Max retries reached, giving up")
                return None
            continue

        except Exception as e:
            logger.error(f"Unexpected error calling LLM: {e}")
            return None

    return None


def summarize_news(news_raw: list, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Summarize news data into top narratives, catalysts, and risk appetite.

    Args:
        news_raw: List of raw news items (up to 50)
        config: AI API configuration

    Returns:
        News summary dict or None on failure
    """
    try:
        template = load_prompt_template(str(PROMPT_NEWS_SUMMARIZER))
        # Serialize once and reuse
        news_json = json.dumps(news_raw, ensure_ascii=False, indent=2)
        system_prompt, user_prompt = format_prompt(template, {
            "news_raw_latest_50": news_json
        })

        result = _call_llm_with_retry(
            system_prompt,
            user_prompt,
            template["output_schema"],
            config
        )

        return result

    except Exception as e:
        logger.error(f"Error summarizing news: {e}")
        return None


def analyze_economic_events(econ_events: list, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Analyze economic events and their market impact.

    Args:
        econ_events: List of economic event dicts
        config: AI API configuration

    Returns:
        Economic summary dict or None on failure
    """
    try:
        template = load_prompt_template(str(PROMPT_ECON_ANALYST))
        # Serialize once and reuse
        econ_json = json.dumps(econ_events, ensure_ascii=False, indent=2)
        system_prompt, user_prompt = format_prompt(template, {
            "econ_events": econ_json
        })

        result = _call_llm_with_retry(
            system_prompt,
            user_prompt,
            template["output_schema"],
            config
        )

        return result

    except Exception as e:
        logger.error(f"Error analyzing economic events: {e}")
        return None


def analyze_macro_features(
    asset: str,
    macro_features: Dict[str, Any],
    sr_levels: Dict[str, list],
    config: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Analyze multi-timeframe technical features.

    Args:
        asset: Asset symbol (BTC, ETH, XAU, XAG)
        macro_features: Multi-timeframe technical features
        sr_levels: Support/resistance levels
        config: AI API configuration

    Returns:
        Macro analysis dict or None on failure
    """
    try:
        template = load_prompt_template(str(PROMPT_MACRO_ANALYSIS))
        system_prompt, user_prompt = format_prompt(template, {
            "asset": asset,
            "macro_features": macro_features,
            "sr_levels": sr_levels
        })

        result = _call_llm_with_retry(
            system_prompt,
            user_prompt,
            template["output_schema"],
            config
        )

        return result

    except Exception as e:
        logger.error(f"Error analyzing macro features: {e}")
        return None


def generate_ai_brief(
    asset: str,
    current_price: float,
    support_levels: list,
    resistance_levels: list,
    macro_features: Dict[str, Any],
    news_summary: Optional[Dict[str, Any]],
    econ_summary: Optional[Dict[str, Any]],
    anomaly_signals: Optional[list],
    config: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Generate comprehensive AI brief with dual-track trading plans.

    Args:
        asset: Asset symbol (BTC, ETH, XAU, XAG)
        current_price: Current market price
        support_levels: List of support levels
        resistance_levels: List of resistance levels
        macro_features: Multi-timeframe technical features
        news_summary: News summary dict (optional)
        econ_summary: Economic summary dict (optional)
        anomaly_signals: List of anomaly signals (optional)
        config: AI API configuration

    Returns:
        AI brief dict with futures_plan and spot_plan or None on failure
    """
    try:
        template = load_prompt_template(str(PROMPT_AI_BRIEF))

        # Format optional fields
        news_str = json.dumps(news_summary, ensure_ascii=False, indent=2) if news_summary else "无"
        econ_str = json.dumps(econ_summary, ensure_ascii=False, indent=2) if econ_summary else "无"
        anomaly_str = json.dumps(anomaly_signals, ensure_ascii=False, indent=2) if anomaly_signals else "无"

        system_prompt, user_prompt = format_prompt(template, {
            "asset": asset,
            "current_price": current_price,
            "support_levels": support_levels,
            "resistance_levels": resistance_levels,
            "macro_features": macro_features,
            "news_summary": news_str,
            "econ_summary": econ_str,
            "anomaly_signals": anomaly_str
        })

        result = _call_llm_with_retry(
            system_prompt,
            user_prompt,
            template["output_schema"],
            config
        )

        return result

    except Exception as e:
        logger.error(f"Error generating AI brief: {e}")
        return None

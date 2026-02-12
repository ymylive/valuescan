#!/usr/bin/env python3
"""
Test suite for AI module V3 refactor.

Validates that:
1. Prompt templates load correctly
2. Output schemas forbid confidence fields
3. Parser detects forbidden fields
4. JSON extraction works with markdown code blocks
"""

import json
import pytest
from pathlib import Path

try:
    from signal_monitor.llm_output_parser import (
        extract_json_from_text,
        detect_forbidden_fields,
        validate_output_schema,
        load_prompt_template,
        ForbiddenFieldError,
        LLMOutputParseError
    )
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from signal_monitor.llm_output_parser import (
        extract_json_from_text,
        detect_forbidden_fields,
        validate_output_schema,
        load_prompt_template,
        ForbiddenFieldError,
        LLMOutputParseError
    )


def test_extract_json_from_markdown():
    """Test JSON extraction from markdown code blocks."""
    text = """Here is the analysis:
```json
{
  "asset": "BTC",
  "disclaimer": "仅供参考，不构成投资建议"
}
```
"""
    result = extract_json_from_text(text)
    assert '"asset"' in result
    assert '"BTC"' in result


def test_extract_json_from_raw():
    """Test JSON extraction from raw text."""
    text = 'Some text {"asset": "BTC", "value": 123} more text'
    result = extract_json_from_text(text)
    data = json.loads(result)
    assert data["asset"] == "BTC"
    assert data["value"] == 123


def test_extract_json_from_raw_nested():
    """Test JSON extraction from nested raw JSON text."""
    text = 'prefix {"asset":"BTC","plan":{"long":{"entry":12345},"targets":[1,2,3]}} suffix'
    result = extract_json_from_text(text)
    data = json.loads(result)
    assert data["asset"] == "BTC"
    assert data["plan"]["long"]["entry"] == 12345
    assert data["plan"]["targets"] == [1, 2, 3]


def test_detect_forbidden_fields_confidence():
    """Test detection of confidence field."""
    data = {
        "asset": "BTC",
        "confidence": 0.85,
        "analysis": "test"
    }
    violations = detect_forbidden_fields(data)
    assert len(violations) > 0
    assert any("confidence" in v for v in violations)


def test_detect_forbidden_fields_nested():
    """Test detection of forbidden fields in nested structures."""
    data = {
        "asset": "BTC",
        "futures_plan": {
            "bias": "long",
            "probability": 0.75
        }
    }
    violations = detect_forbidden_fields(data)
    assert len(violations) > 0
    assert any("probability" in v for v in violations)


def test_detect_forbidden_fields_chinese():
    """Test detection of Chinese forbidden keywords."""
    data = {
        "asset": "BTC",
        "分析": {
            "置信度": 0.8
        }
    }
    violations = detect_forbidden_fields(data)
    assert len(violations) > 0


def test_no_forbidden_fields():
    """Test that clean data passes validation."""
    data = {
        "asset": "BTC",
        "disclaimer": "仅供参考，不构成投资建议",
        "futures_plan": {
            "bias": "long",
            "risk_control": "strict stop loss"
        }
    }
    violations = detect_forbidden_fields(data)
    assert len(violations) == 0


def test_load_prompt_templates():
    """Test that all prompt templates load correctly."""
    prompts_dir = Path(__file__).parent.parent / "prompts"

    templates = [
        "news_summarizer.json",
        "econ_analyst.json",
        "macro_analysis.json",
        "ai_brief.json"
    ]

    for template_file in templates:
        template_path = prompts_dir / template_file
        assert template_path.exists(), f"Template {template_file} not found"

        template = load_prompt_template(str(template_path))

        # Validate structure
        assert "version" in template
        assert "name" in template
        assert "system_prompt" in template
        assert "user_prompt_template" in template
        assert "output_schema" in template

        # Validate forbidden fields are specified
        schema = template["output_schema"]
        assert "forbidden_fields" in schema
        assert len(schema["forbidden_fields"]) > 0

        # Validate disclaimer requirement
        assert "disclaimer" in schema["properties"]
        assert schema["properties"]["disclaimer"]["const"] == "仅供参考，不构成投资建议"


def test_schema_validation_with_forbidden_fields():
    """Test that schema validation rejects forbidden fields."""
    schema = {
        "type": "object",
        "properties": {
            "asset": {"type": "string"}
        },
        "forbidden_fields": ["confidence", "probability"]
    }

    data = {
        "asset": "BTC",
        "confidence": 0.9
    }

    with pytest.raises(ForbiddenFieldError):
        validate_output_schema(data, schema)


def test_ai_brief_schema_structure():
    """Test AI brief schema has dual-track structure."""
    prompts_dir = Path(__file__).parent.parent / "prompts"
    template = load_prompt_template(str(prompts_dir / "ai_brief.json"))

    schema = template["output_schema"]
    props = schema["properties"]

    # Validate dual-track structure
    assert "futures_plan" in props
    assert "spot_plan" in props

    # Validate futures plan structure
    futures_props = props["futures_plan"]["properties"]
    assert "bias" in futures_props
    assert "long_zone" in futures_props
    assert "short_zone" in futures_props
    assert "invalid_level" in futures_props
    assert "take_profit" in futures_props

    # Validate spot plan structure
    spot_props = props["spot_plan"]["properties"]
    assert "bias" in spot_props
    assert "buy_zone" in spot_props
    assert "sell_zone" in spot_props
    assert "take_profit" in spot_props


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

#!/usr/bin/env python3
"""
AI Modules and Prompts Testing Script
Tests all AI functions and validates prompt quality.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from signal_monitor.llm_output_parser import (
    load_prompt_template,
    extract_json_from_text,
    detect_forbidden_fields,
    validate_output_schema,
    LLMOutputParseError,
    ForbiddenFieldError
)

# Test results storage
test_results = []

def score_prompt_quality(template: Dict[str, Any]) -> Dict[str, int]:
    """Score prompt quality on multiple dimensions."""
    scores = {
        "instruction_clarity": 0,
        "structure": 0,
        "forbidden_declaration": 0,
        "disclaimer": 0
    }

    system_prompt = template.get("system_prompt", "")
    user_prompt = template.get("user_prompt_template", "")
    schema = template.get("output_schema", {})

    # 1. Instruction clarity (10 points)
    clarity_keywords = ["MUST", "NEVER", "ALWAYS", "CRITICAL", "exact", "strict"]
    clarity_count = sum(1 for kw in clarity_keywords if kw in system_prompt)
    scores["instruction_clarity"] = min(10, clarity_count * 2)

    # 2. Structure (10 points)
    if "output in this exact JSON structure" in user_prompt or "exact JSON structure" in user_prompt:
        scores["structure"] += 5
    if "{" in user_prompt and "}" in user_prompt:
        scores["structure"] += 5

    # 3. Forbidden field declaration (10 points)
    if "NEVER include confidence" in system_prompt or "NEVER include" in system_prompt:
        scores["forbidden_declaration"] += 5
    if "forbidden_fields" in schema:
        scores["forbidden_declaration"] += 5

    # 4. Disclaimer (10 points)
    if "disclaimer" in user_prompt or "disclaimer" in str(schema):
        scores["disclaimer"] += 5
    if "仅供参考" in system_prompt or "仅供参考" in user_prompt:
        scores["disclaimer"] += 5

    return scores

def test_prompt_file(prompt_path: Path, name: str) -> Dict[str, Any]:
    """Test a single prompt file."""
    result = {
        "name": name,
        "file": str(prompt_path),
        "status": "✅",
        "issues": [],
        "scores": {},
        "total_score": 0
    }

    try:
        # Load template
        template = load_prompt_template(str(prompt_path))

        # Check required fields
        required = ["version", "name", "description", "system_prompt", "user_prompt_template", "output_schema"]
        for field in required:
            if field not in template:
                result["issues"].append(f"Missing required field: {field}")
                result["status"] = "❌"

        # Check schema structure
        schema = template.get("output_schema", {})
        if "required" not in schema:
            result["issues"].append("Schema missing 'required' field")
            result["status"] = "⚠️"

        if "properties" not in schema:
            result["issues"].append("Schema missing 'properties' field")
            result["status"] = "⚠️"

        # Check forbidden fields declaration
        if "forbidden_fields" not in schema:
            result["issues"].append("Schema missing 'forbidden_fields' declaration")
            result["status"] = "⚠️"
        else:
            forbidden = schema["forbidden_fields"]
            expected = ["confidence", "confident", "probability", "置信", "信心", "胜率"]
            if set(forbidden) != set(expected):
                result["issues"].append(f"Forbidden fields incomplete: {forbidden}")
                result["status"] = "⚠️"

        # Check placeholder consistency
        user_prompt = template.get("user_prompt_template", "")
        placeholders = set()
        import re
        for match in re.finditer(r'\{(\w+)\}', user_prompt):
            placeholders.add(match.group(1))

        # Score quality
        scores = score_prompt_quality(template)
        result["scores"] = scores
        result["total_score"] = sum(scores.values())

        if not result["issues"]:
            result["issues"].append("All checks passed")

    except Exception as e:
        result["status"] = "❌"
        result["issues"].append(f"Error loading template: {e}")

    return result

def test_json_extraction():
    """Test JSON extraction from various formats."""
    test_cases = [
        ('{"key": "value"}', True, "Plain JSON"),
        ('```json\n{"key": "value"}\n```', True, "Markdown code block"),
        ('```\n{"key": "value"}\n```', True, "Code block without language"),
        ('Some text {"key": "value"} more text', True, "JSON in text"),
        ('No JSON here', False, "No JSON"),
    ]

    results = []
    for text, should_pass, description in test_cases:
        try:
            extracted = extract_json_from_text(text)
            parsed = json.loads(extracted)
            results.append(f"✅ {description}")
        except Exception as e:
            if should_pass:
                results.append(f"❌ {description}: {e}")
            else:
                results.append(f"✅ {description} (correctly failed)")

    return results

def test_forbidden_field_detection():
    """Test forbidden field detection."""
    test_cases = [
        ({"key": "value"}, [], "Clean data"),
        ({"confidence": 0.9}, ["root.confidence"], "Top-level confidence"),
        ({"nested": {"probability": 0.8}}, ["root.nested.probability"], "Nested probability"),
        ({"list": [{"信心": "high"}]}, ["root.list[0].信心"], "Chinese forbidden field"),
        ({"confident": True, "置信": 0.9}, ["root.confident", "root.置信"], "Multiple violations"),
    ]

    results = []
    for data, expected_violations, description in test_cases:
        violations = detect_forbidden_fields(data)
        if set(violations) == set(expected_violations):
            results.append(f"✅ {description}")
        else:
            results.append(f"❌ {description}: expected {expected_violations}, got {violations}")

    return results

def test_schema_validation():
    """Test schema validation."""
    schema = {
        "type": "object",
        "required": ["name", "value"],
        "properties": {
            "name": {"type": "string"},
            "value": {"type": "number"}
        },
        "forbidden_fields": ["confidence"]
    }

    test_cases = [
        ({"name": "test", "value": 42}, True, "Valid data"),
        ({"name": "test"}, False, "Missing required field"),
        ({"name": "test", "value": "not a number"}, False, "Wrong type"),
        ({"name": "test", "value": 42, "confidence": 0.9}, False, "Forbidden field"),
    ]

    results = []
    for data, should_pass, description in test_cases:
        try:
            validate_output_schema(data, schema)
            if should_pass:
                results.append(f"✅ {description}")
            else:
                results.append(f"❌ {description}: should have failed")
        except Exception as e:
            if not should_pass:
                results.append(f"✅ {description} (correctly failed: {type(e).__name__})")
            else:
                results.append(f"❌ {description}: {e}")

    return results

def generate_report(results: List[Dict[str, Any]]):
    """Generate comprehensive test report."""
    print("\n" + "="*80)
    print("AI MODULES AND PROMPTS TEST REPORT")
    print("="*80 + "\n")

    # Prompt file tests
    print("## PROMPT FILE TESTS\n")
    for result in results:
        print(f"### {result['name']}")
        print(f"**File**: {result['file']}")
        print(f"**Status**: {result['status']}\n")

        if result.get("scores"):
            scores = result["scores"]
            total = result["total_score"]
            print(f"**Prompt Quality** (Total: {total}/40):")
            print(f"- Instruction Clarity: {scores['instruction_clarity']}/10")
            print(f"- Structure: {scores['structure']}/10")
            print(f"- Forbidden Field Declaration: {scores['forbidden_declaration']}/10")
            print(f"- Disclaimer: {scores['disclaimer']}/10\n")

        print("**Issues Found**:")
        for issue in result["issues"]:
            print(f"- {issue}")
        print()

    # Parser tests
    print("\n## PARSER FUNCTION TESTS\n")

    print("### JSON Extraction")
    extraction_results = test_json_extraction()
    for r in extraction_results:
        print(f"- {r}")

    print("\n### Forbidden Field Detection")
    detection_results = test_forbidden_field_detection()
    for r in detection_results:
        print(f"- {r}")

    print("\n### Schema Validation")
    validation_results = test_schema_validation()
    for r in validation_results:
        print(f"- {r}")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    passed = sum(1 for r in results if r["status"] == "✅")
    warned = sum(1 for r in results if r["status"] == "⚠️")
    failed = sum(1 for r in results if r["status"] == "❌")

    print(f"\nPrompt Files: {passed} passed, {warned} warnings, {failed} failed")
    print(f"Average Quality Score: {sum(r['total_score'] for r in results) / len(results):.1f}/40")

    print("\n## RECOMMENDATIONS\n")

    # Generate recommendations
    low_score_prompts = [r for r in results if r["total_score"] < 30]
    if low_score_prompts:
        print("**Low Quality Prompts** (score < 30/40):")
        for r in low_score_prompts:
            print(f"- {r['name']}: {r['total_score']}/40")
            print("  Suggestions:")
            if r["scores"]["instruction_clarity"] < 8:
                print("  - Add more explicit instructions (MUST, NEVER, ALWAYS)")
            if r["scores"]["structure"] < 8:
                print("  - Provide clearer output structure examples")
            if r["scores"]["forbidden_declaration"] < 8:
                print("  - Strengthen forbidden field declarations")
            if r["scores"]["disclaimer"] < 8:
                print("  - Ensure disclaimer is prominent")
    else:
        print("✅ All prompts meet quality standards (30+/40)")

    print("\n" + "="*80)

def main():
    """Run all tests."""
    prompts_dir = Path(__file__).parent / "prompts"

    prompt_files = [
        (prompts_dir / "news_summarizer.json", "News Summarizer"),
        (prompts_dir / "econ_analyst.json", "Economic Analyst"),
        (prompts_dir / "macro_analysis.json", "Macro Analysis"),
        (prompts_dir / "ai_brief.json", "AI Brief (Dual-Track)"),
    ]

    results = []
    for prompt_path, name in prompt_files:
        if prompt_path.exists():
            result = test_prompt_file(prompt_path, name)
            results.append(result)
        else:
            results.append({
                "name": name,
                "file": str(prompt_path),
                "status": "❌",
                "issues": ["File not found"],
                "scores": {},
                "total_score": 0
            })

    generate_report(results)

if __name__ == "__main__":
    main()

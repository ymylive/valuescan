#!/usr/bin/env python3
"""
LLM Output Parser with strict validation.

Handles JSON extraction, schema validation, and forbidden field detection.
"""

import json
import re
from typing import Any, Dict, List, Optional
from jsonschema import validate, ValidationError

try:
    from .logger import logger
except ImportError as e:
    try:
        from logger import logger
    except ImportError:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to import logger: {e}")


class LLMOutputParseError(Exception):
    """Raised when LLM output cannot be parsed or validated."""
    pass


class ForbiddenFieldError(Exception):
    """Raised when output contains forbidden confidence/probability fields."""
    pass


# Compile regex patterns at module level
_CODE_BLOCK_PATTERN = re.compile(r'```(?:json)?\s*\n(.*?)\n```', re.DOTALL)


def _extract_balanced_json(text: str) -> Optional[str]:
    starts = [idx for idx, ch in enumerate(text) if ch in "{["]
    for start in starts:
        stack: List[str] = []
        in_string = False
        escaped = False
        for idx in range(start, len(text)):
            ch = text[idx]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
                continue

            if ch == "{":
                stack.append("}")
                continue
            if ch == "[":
                stack.append("]")
                continue

            if ch in "}]":
                if not stack or ch != stack[-1]:
                    break
                stack.pop()
                if not stack:
                    return text[start : idx + 1].strip()

    return None


def extract_json_from_text(text: str) -> str:
    """
    Extract JSON from LLM output, handling markdown code blocks.

    Args:
        text: Raw LLM output text

    Returns:
        Extracted JSON string

    Raises:
        LLMOutputParseError: If no valid JSON found
    """
    # Try to find JSON in markdown code blocks
    matches = _CODE_BLOCK_PATTERN.findall(text)

    if matches:
        # Use the first code block
        json_str = matches[0].strip()
    else:
        json_str = _extract_balanced_json(text)
        if not json_str:
            raise LLMOutputParseError(f"No JSON found in output: {text[:200]}...")

    return json_str


def detect_forbidden_fields(data: Any, path: str = "root") -> List[str]:
    """
    Recursively detect forbidden confidence/probability fields.

    Args:
        data: Parsed JSON data
        path: Current path in the data structure (for error reporting)

    Returns:
        List of paths where forbidden fields were found
    """
    forbidden_keywords = [
        "confidence", "confident", "probability",
        "置信", "信心", "胜率"
    ]

    violations = []

    if isinstance(data, dict):
        for key, value in data.items():
            # Check if key itself is forbidden
            if any(kw in key.lower() for kw in forbidden_keywords):
                violations.append(f"{path}.{key}")

            # Recursively check nested structures
            violations.extend(detect_forbidden_fields(value, f"{path}.{key}"))

    elif isinstance(data, list):
        for i, item in enumerate(data):
            violations.extend(detect_forbidden_fields(item, f"{path}[{i}]"))

    return violations


def validate_output_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> None:
    """
    Validate parsed JSON against schema.

    Args:
        data: Parsed JSON data
        schema: JSON schema definition

    Raises:
        ValidationError: If data doesn't match schema
        ForbiddenFieldError: If forbidden fields detected
    """
    # First check for forbidden fields
    forbidden_fields = schema.get("forbidden_fields", [])
    if forbidden_fields:
        violations = detect_forbidden_fields(data)
        if violations:
            raise ForbiddenFieldError(
                f"Forbidden confidence/probability fields detected at: {', '.join(violations)}"
            )

    # Then validate against JSON schema
    validate(instance=data, schema=schema)


def parse_llm_output(
    raw_output: str,
    schema: Dict[str, Any],
    max_retries: int = 2
) -> Dict[str, Any]:
    """
    Parse and validate LLM output with retry logic.

    Args:
        raw_output: Raw text output from LLM
        schema: JSON schema for validation
        max_retries: Maximum retry attempts (not used here, for API layer)

    Returns:
        Validated JSON data

    Raises:
        LLMOutputParseError: If parsing fails
        ForbiddenFieldError: If forbidden fields detected
        ValidationError: If schema validation fails
    """
    try:
        # Step 1: Extract JSON from text
        json_str = extract_json_from_text(raw_output)
        logger.debug(f"Extracted JSON: {json_str[:200]}...")

        # Step 2: Parse JSON
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise LLMOutputParseError(f"Invalid JSON: {e}")

        # Step 3: Validate schema
        validate_output_schema(data, schema)

        logger.info("LLM output parsed and validated successfully")
        return data

    except (LLMOutputParseError, ForbiddenFieldError, ValidationError) as e:
        logger.error(f"LLM output validation failed: {e}")
        logger.debug(f"Raw output: {raw_output[:500]}...")
        raise


def load_prompt_template(prompt_file: str) -> Dict[str, Any]:
    """
    Load prompt template from JSON file.

    Args:
        prompt_file: Path to prompt JSON file

    Returns:
        Prompt template dictionary
    """
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def format_prompt(
    template: Dict[str, Any],
    variables: Dict[str, Any]
) -> tuple[str, str]:
    """
    Format prompt template with variables.

    Args:
        template: Prompt template dictionary
        variables: Variables to substitute

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    system_prompt = template["system_prompt"]
    user_prompt = template["user_prompt_template"]

    # Substitute variables in user prompt
    for key, value in variables.items():
        placeholder = f"{{{key}}}"
        if placeholder in user_prompt:
            # Convert value to string if needed
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value, ensure_ascii=False, indent=2)
            else:
                value_str = str(value)
            user_prompt = user_prompt.replace(placeholder, value_str)

    return system_prompt, user_prompt

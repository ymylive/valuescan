from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

AI_PROTOCOL_AUTO = "auto"
AI_PROTOCOL_COMPATIBLE = "compatible"
AI_PROTOCOL_RESPONSES = "responses"

_DEFAULT_TIMEOUT_SEC = 60
_MAX_TIMEOUT_SEC = 180
_TIMEOUT_PER_KB_SEC = 10


def calculate_timeout(prompt_size: int) -> int:
    """Calculate request timeout based on prompt size in characters.

    Base 60s + 10s per KB of prompt, capped at 180s.
    """
    extra = (prompt_size // 1000) * _TIMEOUT_PER_KB_SEC
    return min(_DEFAULT_TIMEOUT_SEC + extra, _MAX_TIMEOUT_SEC)


def normalize_protocol(value: Optional[str]) -> str:
    if not value:
        return AI_PROTOCOL_AUTO
    candidate = value.strip().lower()
    if candidate in (AI_PROTOCOL_AUTO, AI_PROTOCOL_COMPATIBLE, AI_PROTOCOL_RESPONSES):
        return candidate
    return AI_PROTOCOL_AUTO


def detect_protocol_from_url(api_url: str) -> str:
    lower = (api_url or "").lower()
    if "/responses" in lower:
        return AI_PROTOCOL_RESPONSES
    if "/chat/completions" in lower:
        return AI_PROTOCOL_COMPATIBLE
    return AI_PROTOCOL_COMPATIBLE


def resolve_protocol_and_url(api_url: str, protocol: Optional[str]) -> Tuple[str, str]:
    resolved = normalize_protocol(protocol)
    if resolved == AI_PROTOCOL_AUTO:
        resolved = detect_protocol_from_url(api_url)
    return resolved, apply_protocol_to_url(api_url, resolved)


def apply_protocol_to_url(api_url: str, protocol: str) -> str:
    base = (api_url or "").strip()
    if not base:
        return base
    trimmed = base.rstrip("/")
    lower = trimmed.lower()
    if lower.endswith("/chat/completions"):
        if protocol == AI_PROTOCOL_RESPONSES:
            return trimmed[: -len("/chat/completions")] + "/responses"
        return trimmed
    if lower.endswith("/responses"):
        if protocol == AI_PROTOCOL_COMPATIBLE:
            return trimmed[: -len("/responses")] + "/chat/completions"
        return trimmed
    if "/responses" in lower or "/chat/completions" in lower:
        return trimmed
    if protocol == AI_PROTOCOL_RESPONSES:
        return f"{trimmed}/responses"
    return f"{trimmed}/chat/completions"


def is_openai_official(api_url: str) -> bool:
    host = urlparse(api_url or "").netloc.lower()
    return host == "api.openai.com"


def should_force_responses_stream(api_url: str, protocol: str) -> bool:
    return protocol == AI_PROTOCOL_RESPONSES and not is_openai_official(api_url)


def responses_token_key(api_url: str) -> str:
    if is_openai_official(api_url):
        return "max_output_tokens"
    return "max_tokens"


def build_responses_input(system_prompt: str, user_prompt: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if system_prompt:
        items.append(
            {
                "role": "system",
                "content": [{"type": "input_text", "text": system_prompt}],
            }
        )
    if user_prompt:
        items.append(
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_prompt}],
            }
        )
    return items


def build_payload(
    protocol: str,
    api_url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
    stream: bool,
) -> Dict[str, Any]:
    if protocol == AI_PROTOCOL_RESPONSES:
        payload: Dict[str, Any] = {
            "model": model,
            "input": build_responses_input(system_prompt, user_prompt),
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens:
            token_key = responses_token_key(api_url)
            payload[token_key] = max_tokens
        if stream:
            payload["stream"] = True
        # Ensure no conflicting token keys
        if "max_tokens" in payload and "max_output_tokens" in payload:
            payload.pop("max_tokens")
        return payload

    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    return payload


def _join_text_parts(items: Any) -> str:
    if isinstance(items, str):
        return items
    if not isinstance(items, list):
        return ""
    texts: List[str] = []
    for item in items:
        if isinstance(item, str):
            texts.append(item)
            continue
        if isinstance(item, dict):
            text = item.get("text") or item.get("content")
            if isinstance(text, str):
                texts.append(text)
                continue
            nested = _join_text_parts(text)
            if nested:
                texts.append(nested)
    return "\n".join(t for t in texts if t).strip()


def _extract_content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        direct = content.get("text")
        if isinstance(direct, str) and direct:
            return direct
        parts = content.get("parts")
        if parts:
            return _join_text_parts(parts)
        nested = content.get("content")
        if nested:
            return _extract_content_text(nested)
    if isinstance(content, list):
        return _join_text_parts(content)
    return ""


def _extract_candidates_text(data: Dict[str, Any]) -> str:
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        return ""
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content") or candidate.get("message")
        text = _extract_content_text(content)
        if text:
            return text
        output = candidate.get("output")
        if isinstance(output, str) and output:
            return output
    return ""


def parse_compatible_content(data: Dict[str, Any]) -> str:
    if not isinstance(data, dict):
        return ""
    choice = (data.get("choices") or [{}])[0] if isinstance(data.get("choices"), list) else {}
    message = choice.get("message") if isinstance(choice, dict) else {}
    content = ""
    if isinstance(message, dict):
        content = _extract_content_text(message.get("content"))
    if not content and isinstance(choice, dict):
        content = choice.get("text") or ""
    if not content and isinstance(choice, dict):
        delta = choice.get("delta") or {}
        if isinstance(delta, dict):
            content = _extract_content_text(delta.get("content"))
    if not content:
        content = _extract_candidates_text(data)
    if not content:
        content = _extract_content_text(data.get("content"))
    if not content and isinstance(data.get("result"), str):
        content = data.get("result")
    return content.strip() if content else ""


def parse_responses_body(body_text: str) -> str:
    trimmed = (body_text or "").strip()
    if not trimmed:
        return ""
    if "data:" in trimmed:
        delta_parts: List[str] = []
        done_text = ""
        last_payload = ""
        for line in trimmed.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[len("data:") :].strip()
            if not payload or payload == "[DONE]":
                continue
            last_payload = payload
            try:
                data = json.loads(payload)
            except Exception:
                continue
            event_type = data.get("type")
            if event_type == "response.output_text.delta":
                delta = data.get("delta")
                if isinstance(delta, str) and delta:
                    delta_parts.append(delta)
            elif event_type == "response.output_text.done":
                text = data.get("text")
                if isinstance(text, str) and text:
                    done_text = text
        if done_text:
            return done_text
        if delta_parts:
            return "".join(delta_parts)
        if last_payload:
            return parse_responses_json(last_payload)
    if trimmed.startswith("{") or trimmed.startswith("["):
        return parse_responses_json(trimmed)
    return ""


def parse_responses_json(payload: str) -> str:
    try:
        data = json.loads(payload)
    except Exception:
        return ""

    error = data.get("error")
    if isinstance(error, dict):
        code = error.get("code")
        message = error.get("message")
        raise ValueError(f"API error: code={code}, message={message}")

    texts: List[str] = []
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text:
        texts.append(output_text)

    if not texts:
        for item in data.get("output", []) or []:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for content in item.get("content", []) or []:
                if isinstance(content, dict):
                    text = content.get("text")
                    if isinstance(text, str) and text:
                        texts.append(text)

    if not texts:
        for choice in data.get("choices", []) or []:
            if not isinstance(choice, dict):
                continue
            text = choice.get("text")
            if isinstance(text, str) and text:
                texts.append(text)
                continue
            message = choice.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content:
                    texts.append(content)

    return "\n".join(texts).strip() if texts else ""


def resolve_responses_token_key_override(body_text: str) -> Optional[str]:
    lower = (body_text or "").lower()
    if "unsupported parameter: max_output_tokens" in lower:
        return "max_tokens"
    if "unsupported parameter: max_tokens" in lower:
        return ""
    return None


def override_responses_token_key(payload: Dict[str, Any], token_key: str, fallback: int) -> Dict[str, Any]:
    value = fallback
    for key in ("max_output_tokens", "max_tokens"):
        if key in payload:
            try:
                value = int(payload[key])
            except Exception:
                value = fallback
    payload.pop("max_output_tokens", None)
    payload.pop("max_tokens", None)
    if token_key:
        payload[token_key] = value
    return payload

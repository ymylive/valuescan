from __future__ import annotations

import json
import logging
import os
import queue
import shlex
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CACHE_LOCK = threading.Lock()


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(value, (int, float)):
        return value != 0
    return default


def _normalize_args(raw_args: Any) -> List[str]:
    if isinstance(raw_args, list):
        return [str(item).strip() for item in raw_args if str(item).strip()]
    if isinstance(raw_args, str):
        text = raw_args.strip()
        if not text:
            return []
        try:
            return shlex.split(text)
        except ValueError:
            return [part for part in text.split(" ") if part.strip()]
    return []


def _normalize_env(raw_env: Any) -> Dict[str, str]:
    if not isinstance(raw_env, dict):
        return {}
    env: Dict[str, str] = {}
    for key, value in raw_env.items():
        env_key = str(key).strip()
        if not env_key:
            continue
        env[env_key] = "" if value is None else str(value)
    return env


def _read_mcp_message(stream: Any) -> Dict[str, Any]:
    headers: Dict[str, str] = {}

    while True:
        line = stream.readline()
        if not line:
            raise RuntimeError("MCP stream closed")
        if line in (b"\r\n", b"\n"):
            break

        decoded = line.decode("utf-8", errors="replace").strip()
        if ":" not in decoded:
            continue
        key, _, value = decoded.partition(":")
        headers[key.strip().lower()] = value.strip()

    content_length = _as_int(headers.get("content-length"), 0)
    if content_length <= 0:
        raise RuntimeError("Invalid MCP content-length")

    payload = stream.read(content_length)
    if not payload or len(payload) < content_length:
        raise RuntimeError("Incomplete MCP payload")

    try:
        return json.loads(payload.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid MCP JSON payload: {exc}") from exc


def _read_mcp_message_with_timeout(stream: Any, timeout_sec: int) -> Dict[str, Any]:
    result_queue: "queue.Queue[Tuple[str, Any]]" = queue.Queue(maxsize=1)

    def _worker() -> None:
        try:
            result_queue.put(("ok", _read_mcp_message(stream)))
        except Exception as exc:
            result_queue.put(("err", exc))

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

    try:
        status, value = result_queue.get(timeout=max(1, timeout_sec))
    except queue.Empty as exc:
        raise TimeoutError("MCP response timeout") from exc

    if status == "err":
        raise value
    return value


class _MCPStdioSession:
    def __init__(self, command: str, args: List[str], env: Dict[str, str], timeout_sec: int) -> None:
        self.command = command
        self.args = args
        self.env = env
        self.timeout_sec = max(5, timeout_sec)
        self._id = 0
        self.proc: Optional[subprocess.Popen[bytes]] = None

    def __enter__(self) -> "_MCPStdioSession":
        repo_root = Path(__file__).resolve().parents[1]
        command = self.command
        resolved = shutil.which(command, path=self.env.get("PATH"))
        if not resolved and os.name == "nt" and "." not in Path(command).suffix:
            for ext in (".cmd", ".exe", ".bat"):
                resolved = shutil.which(f"{command}{ext}", path=self.env.get("PATH"))
                if resolved:
                    break
        executable = resolved or command
        self.proc = subprocess.Popen(
            [executable, *self.args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=str(repo_root),
            env=self.env,
        )
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if not self.proc:
            return
        try:
            self.proc.terminate()
            self.proc.wait(timeout=2)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass

    def _send(self, payload: Dict[str, Any]) -> None:
        if not self.proc or not self.proc.stdin:
            raise RuntimeError("MCP process is not running")

        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        header = f"Content-Length: {len(raw)}\r\n\r\n".encode("ascii")
        self.proc.stdin.write(header + raw)
        self.proc.stdin.flush()

    def notify(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        self._send(
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": params or {},
            }
        )

    def request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.proc or not self.proc.stdout:
            raise RuntimeError("MCP process is not running")

        self._id += 1
        request_id = self._id
        self._send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {},
            }
        )

        max_messages = 30
        for _ in range(max_messages):
            message = _read_mcp_message_with_timeout(self.proc.stdout, self.timeout_sec)
            if not isinstance(message, dict):
                continue
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise RuntimeError(f"MCP error: {message.get('error')}")
            result = message.get("result")
            return result if isinstance(result, dict) else {}

        raise RuntimeError("MCP response not found for request")

    def initialize(self) -> None:
        self.request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "clientInfo": {
                    "name": "valuescan-ai",
                    "version": "1.0.0",
                },
                "capabilities": {},
            },
        )
        self.notify("notifications/initialized", {})

    def list_tools(self) -> List[Dict[str, Any]]:
        result = self.request("tools/list", {})
        tools = result.get("tools")
        return tools if isinstance(tools, list) else []


def _pick_tool_name(tools: List[Dict[str, Any]], preferred: str) -> Optional[str]:
    names = [str(tool.get("name") or "") for tool in tools]
    if preferred and preferred in names:
        return preferred

    for token in ("search", "news", "web", "query"):
        for name in names:
            if token in name.lower():
                return name
    return names[0] if names else None


def _render_text(result: Dict[str, Any]) -> str:
    content = result.get("content")
    if isinstance(content, list):
        texts: List[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    texts.append(text.strip())
        if texts:
            return "\n".join(texts)

    if isinstance(content, str) and content.strip():
        return content.strip()

    return json.dumps(result, ensure_ascii=False)[:4000]


def _build_search_query(symbol: str, snapshot: Dict[str, Any], signal_payload: Optional[Dict[str, Any]], cfg: Dict[str, Any]) -> str:
    title = ""
    if isinstance(signal_payload, dict):
        item = signal_payload.get("item") or {}
        title = str(item.get("title") or "").strip()

    template = str(
        cfg.get("query_template")
        or "{symbol} crypto latest market news macro policy risk funding open interest sentiment"
    )
    try:
        return template.format(
            symbol=symbol,
            price=snapshot.get("current_price"),
            title=title,
        )
    except Exception:
        return f"{symbol} crypto latest market news macro policy risk funding open interest sentiment"


def _build_arg_candidates(query: str, max_results: int, cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    custom = cfg.get("arguments")
    candidates: List[Dict[str, Any]] = []

    if isinstance(custom, dict):
        normalized = {}
        for key, value in custom.items():
            if isinstance(value, str):
                normalized[str(key)] = value.replace("{query}", query)
            else:
                normalized[str(key)] = value
        candidates.append(normalized)

    candidates.extend(
        [
            {"query": query, "numResults": max_results},
            {"query": query, "limit": max_results},
            {"query": query, "count": max_results},
            {"query": query},
            {"q": query, "limit": max_results},
            {"q": query},
        ]
    )
    return candidates


def _normalize_sources(mcp_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_sources = mcp_cfg.get("sources")
    if isinstance(raw_sources, list):
        normalized: List[Dict[str, Any]] = []
        for index, item in enumerate(raw_sources, start=1):
            if not isinstance(item, dict):
                continue
            if not _as_bool(item.get("enabled"), True):
                continue
            merged = dict(mcp_cfg)
            merged.pop("sources", None)
            merged.update(item)
            merged["name"] = str(item.get("name") or f"source_{index}")
            normalized.append(merged)
        if normalized:
            return normalized

    fallback = dict(mcp_cfg)
    fallback.pop("sources", None)
    fallback["name"] = str(mcp_cfg.get("name") or "source_1")
    return [fallback]


def _collect_single_source(query: str, cfg: Dict[str, Any], max_prompt_chars: int) -> Optional[Dict[str, Any]]:
    command = str(cfg.get("command") or "").strip()
    if not command:
        return None

    args = _normalize_args(cfg.get("args"))
    timeout_sec = max(5, min(120, _as_int(cfg.get("timeout_sec"), 25)))
    env = os.environ.copy()
    env.update(_normalize_env(cfg.get("env")))
    preferred_tool = str(cfg.get("tool_name") or "").strip()

    with _MCPStdioSession(command, args, env, timeout_sec) as session:
        session.initialize()
        tools = session.list_tools()
        tool_name = _pick_tool_name(tools, preferred_tool)
        if not tool_name:
            return None

        raw = _call_search_tool(session, tool_name, query, cfg)
        text = _render_text(raw).strip()
        if not text:
            return None

        if len(text) > max_prompt_chars:
            text = text[:max_prompt_chars].rstrip() + " ..."

        return {
            "name": str(cfg.get("name") or "source"),
            "query": query,
            "tool": tool_name,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "content": text,
        }


def _aggregate_source_contents(items: List[Dict[str, Any]], max_prompt_chars: int) -> str:
    if not items:
        return ""

    parts: List[str] = []
    for item in items:
        name = str(item.get("name") or "source")
        tool = str(item.get("tool") or "")
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        title = f"[{name}]"
        if tool:
            title += f" ({tool})"
        parts.append(f"{title}\n{content}")

    text = "\n\n".join(parts).strip()
    if len(text) > max_prompt_chars:
        return text[:max_prompt_chars].rstrip() + " ..."
    return text


def _call_search_tool(session: _MCPStdioSession, tool_name: str, query: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    max_results = max(1, min(20, _as_int(cfg.get("max_results"), 5)))
    arg_candidates = _build_arg_candidates(query, max_results, cfg)

    last_error: Optional[Exception] = None
    for args in arg_candidates:
        try:
            result = session.request("tools/call", {"name": tool_name, "arguments": args})
            if isinstance(result, dict) and not result.get("isError"):
                return result
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"MCP tool call failed: {last_error}")


def collect_mcp_research_context(
    symbol: str,
    snapshot: Dict[str, Any],
    signal_payload: Optional[Dict[str, Any]],
    ai_config: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    mcp_cfg = ai_config.get("mcp_search")
    if not isinstance(mcp_cfg, dict) or not _as_bool(mcp_cfg.get("enabled"), False):
        return None

    cache_ttl_sec = max(0, _as_int(mcp_cfg.get("cache_ttl_sec"), 900))
    max_prompt_chars = max(200, min(6000, _as_int(mcp_cfg.get("max_prompt_chars"), 2500)))
    max_parallel_sources = max(1, min(5, _as_int(mcp_cfg.get("max_parallel_sources"), 2)))

    query = _build_search_query(symbol, snapshot, signal_payload, mcp_cfg)
    sources = _normalize_sources(mcp_cfg)
    source_keys = []
    for src in sources:
        source_keys.append(
            {
                "name": src.get("name"),
                "command": src.get("command"),
                "args": src.get("args"),
                "tool_name": src.get("tool_name"),
                "max_results": src.get("max_results"),
            }
        )
    cache_key = json.dumps({"query": query, "sources": source_keys}, ensure_ascii=False)

    now = time.time()
    if cache_ttl_sec > 0:
        with _CACHE_LOCK:
            cached = _CACHE.get(cache_key)
            if cached and cached[0] > now:
                return cached[1]

    results: List[Dict[str, Any]] = []
    workers = min(max_parallel_sources, len(sources))
    if workers <= 1:
        for source_cfg in sources:
            try:
                result = _collect_single_source(query, source_cfg, max_prompt_chars)
                if result:
                    results.append(result)
            except Exception as exc:
                logger.warning("MCP source failed (%s): %s", source_cfg.get("name"), exc)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_collect_single_source, query, source_cfg, max_prompt_chars): source_cfg
                for source_cfg in sources
            }
            for future in as_completed(futures):
                source_cfg = futures[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as exc:
                    logger.warning("MCP source failed (%s): %s", source_cfg.get("name"), exc)

    if not results:
        logger.warning("MCP search context unavailable: all sources failed")
        return None

    results.sort(key=lambda item: str(item.get("name") or ""))
    merged_text = _aggregate_source_contents(results, max_prompt_chars)
    if not merged_text:
        return None

    context = {
        "query": query,
        "source_count": len(results),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "sources": results,
        "content": merged_text,
    }

    if cache_ttl_sec > 0:
        with _CACHE_LOCK:
            _CACHE[cache_key] = (now + cache_ttl_sec, context)
    return context

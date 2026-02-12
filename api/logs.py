"""Logs API for querying and streaming logs."""
from flask import Blueprint, jsonify, request, Response
from typing import Dict, Any, Generator
from datetime import datetime
import logging
import json
from pathlib import Path
import re
import time
import threading
from collections import deque
from .auth import require_auth

logs_bp = Blueprint('logs', __name__)
logger = logging.getLogger(__name__)

# Log storage - will be populated from actual log files
_logs_lock = threading.Lock()
_log_entries: deque = deque(maxlen=1000)

SENSITIVE_PATTERNS = [
    (r'api[_-]?key["\s:=]+[\w-]+', 'api_key=***'),
    (r'token["\s:=]+[\w.-]+', 'token=***'),
    (r'password["\s:=]+\S+', 'password=***'),
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '***@***.***'),
]

def sanitize_log_message(message: str) -> str:
    for pattern, replacement in SENSITIVE_PATTERNS:
        message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
    return message

@logs_bp.route('', methods=['GET'])
@require_auth
def query_logs() -> tuple[Dict[str, Any], int]:
    """Query logs with filters."""
    try:
        level = request.args.get('level', 'info').upper()
        module = request.args.get('module')
        since = request.args.get('since')

        try:
            limit = int(request.args.get('limit', 100))
            if limit < 1:
                limit = 100
            elif limit > 1000:
                limit = 1000
        except ValueError:
            limit = 100

        with _logs_lock:
            filtered_logs = list(_log_entries)

        if level:
            filtered_logs = [log for log in filtered_logs if log.get('level') == level]

        if module:
            filtered_logs = [log for log in filtered_logs if log.get('module') == module]

        if since:
            try:
                since_dt = datetime.fromisoformat(since)
                filtered_logs = [
                    log for log in filtered_logs
                    if datetime.fromisoformat(log.get('timestamp', '')) >= since_dt
                ]
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid since parameter format"}), 400

        # Apply limit
        filtered_logs = filtered_logs[-limit:]

        sanitized_logs = [
            {**log, "message": sanitize_log_message(log.get("message", ""))}
            for log in filtered_logs
        ]

        return jsonify({
            "status": "success",
            "logs": sanitized_logs,
            "count": len(sanitized_logs)
        }), 200
    except Exception as e:
        logger.error(f"Failed to query logs: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@logs_bp.route('/stream', methods=['GET'])
@require_auth
def stream_logs() -> Response:
    """Stream logs in real-time using SSE."""
    def generate() -> Generator[str, None, None]:
        """Generate SSE events for log streaming."""
        start_time = time.time()
        max_duration = 300

        while time.time() - start_time < max_duration:
            try:
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now().isoformat()})}\n\n"
                time.sleep(1)
            except GeneratorExit:
                return

        yield f"data: {json.dumps({'type': 'timeout'})}\n\n"

    return Response(generate(), mimetype='text/event-stream')

def add_log_entry(level: str, module: str, message: str):
    """Add a log entry to the in-memory store."""
    with _logs_lock:
        _log_entries.append({
            "timestamp": datetime.now().isoformat(),
            "level": level.upper(),
            "module": module,
            "message": message
        })

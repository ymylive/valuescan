"""Health API for system status monitoring."""
from flask import Blueprint, jsonify
from typing import Dict, Any
from datetime import datetime
import time
import logging
import threading

health_bp = Blueprint('health', __name__)
logger = logging.getLogger(__name__)

# System start time
_start_time = time.time()

# Task status tracking - will be updated by actual task runners
_health_lock = threading.Lock()
_task_status: Dict[str, Dict[str, Any]] = {
    "anomaly_detection": {
        "status": "idle",
        "last_run": None,
        "next_run": None
    },
    "macro_analysis": {
        "status": "idle",
        "last_run": None,
        "next_run": None
    },
    "ai_brief": {
        "status": "idle",
        "last_run": None,
        "next_run": None
    },
    "news_fetch": {
        "status": "idle",
        "last_run": None,
        "next_run": None
    },
    "econ_fetch": {
        "status": "idle",
        "last_run": None,
        "next_run": None
    }
}

@health_bp.route('', methods=['GET'])
def get_health() -> tuple[Dict[str, Any], int]:
    """Get system health status."""
    try:
        uptime = int(time.time() - _start_time)

        with _health_lock:
            tasks = _task_status.copy()

        health_data = {
            "version": "3.0.0",
            "uptime_seconds": uptime,
            "tasks": tasks,
            "queue_backlog": 0  # TODO: Integrate with actual queue
        }

        return jsonify(health_data), 200
    except Exception as e:
        logger.error(f"Failed to get health status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def update_task_status(task_name: str, status: str, last_run: str = None, next_run: str = None):
    """Update task status."""
    with _health_lock:
        if task_name in _task_status:
            _task_status[task_name]["status"] = status
            if last_run:
                _task_status[task_name]["last_run"] = last_run
            if next_run:
                _task_status[task_name]["next_run"] = next_run

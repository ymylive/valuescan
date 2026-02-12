"""Control API for scheduler and manual triggers."""
from flask import Blueprint, jsonify, request
from typing import Dict, Any
import logging
from .auth import require_auth

control_bp = Blueprint('control', __name__)
logger = logging.getLogger(__name__)

# Placeholder for scheduler state - will be integrated with actual scheduler
_scheduler_state = {"running": False}

@control_bp.route('/scheduler/start', methods=['POST'])
@require_auth
def start_scheduler() -> tuple[Dict[str, Any], int]:
    """Start the scheduler."""
    try:
        _scheduler_state["running"] = True
        logger.info("Scheduler started via control API")
        return jsonify({"status": "success", "message": "Scheduler started"}), 200
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@control_bp.route('/scheduler/stop', methods=['POST'])
@require_auth
def stop_scheduler() -> tuple[Dict[str, Any], int]:
    """Stop the scheduler."""
    try:
        _scheduler_state["running"] = False
        logger.info("Scheduler stopped via control API")
        return jsonify({"status": "success", "message": "Scheduler stopped"}), 200
    except Exception as e:
        logger.error(f"Failed to stop scheduler: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@control_bp.route('/trigger/anomaly', methods=['POST'])
@require_auth
def trigger_anomaly() -> tuple[Dict[str, Any], int]:
    """Manually trigger anomaly detection."""
    try:
        logger.info("Anomaly detection trigger requested")
        return jsonify({"status": "success", "message": "Anomaly detection triggered"}), 200
    except Exception as e:
        logger.error(f"Failed to trigger anomaly detection: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@control_bp.route('/trigger/macro', methods=['POST'])
@require_auth
def trigger_macro() -> tuple[Dict[str, Any], int]:
    """Manually trigger macro analysis."""
    try:
        logger.info("Macro analysis trigger requested")
        return jsonify({"status": "success", "message": "Macro analysis triggered"}), 200
    except Exception as e:
        logger.error(f"Failed to trigger macro analysis: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@control_bp.route('/trigger/ai_brief', methods=['POST'])
@require_auth
def trigger_ai_brief() -> tuple[Dict[str, Any], int]:
    """Manually trigger AI brief generation."""
    try:
        logger.info("AI brief trigger requested")
        return jsonify({"status": "success", "message": "AI brief triggered"}), 200
    except Exception as e:
        logger.error(f"Failed to trigger AI brief: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@control_bp.route('/trigger/news', methods=['POST'])
@require_auth
def trigger_news() -> tuple[Dict[str, Any], int]:
    """Manually trigger news fetch."""
    try:
        logger.info("News fetch trigger requested")
        return jsonify({"status": "success", "message": "News fetch triggered"}), 200
    except Exception as e:
        logger.error(f"Failed to trigger news fetch: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@control_bp.route('/trigger/econ', methods=['POST'])
@require_auth
def trigger_econ() -> tuple[Dict[str, Any], int]:
    """Manually trigger economic data fetch."""
    try:
        logger.info("Economic data trigger requested")
        return jsonify({"status": "success", "message": "Economic data fetch triggered"}), 200
    except Exception as e:
        logger.error(f"Failed to trigger economic data fetch: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

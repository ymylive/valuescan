"""Config API for getting and updating system configuration."""
from flask import Blueprint, jsonify, request
from typing import Dict, Any, List
from datetime import datetime
import json
import logging
from pathlib import Path
import jsonschema
import threading
from .auth import require_auth

config_bp = Blueprint('config', __name__)
logger = logging.getLogger(__name__)

# Config file path - will be set during initialization
_config_lock = threading.Lock()
_config_path: Path = None
_config_history: List[Dict[str, Any]] = []

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "signal_monitor": {"type": "object"},
        "macro_analysis": {"type": "object"},
        "ai_brief": {"type": "object"},
        "news_fetch": {"type": "object"},
        "econ_data": {"type": "object"},
        "scheduler": {"type": "object"}
    },
    "required": ["version"],
    "additionalProperties": False
}

def init_config_api(config_path: Path):
    """Initialize config API with config file path."""
    global _config_path
    resolved = config_path.resolve()
    allowed_base = Path(__file__).resolve().parents[1]
    if not str(resolved).startswith(str(allowed_base)):
        raise ValueError(f"Config path must be within {allowed_base}")
    _config_path = resolved

@config_bp.route('', methods=['GET'])
@require_auth
def get_config() -> tuple[Dict[str, Any], int]:
    """Get current configuration."""
    try:
        with _config_lock:
            if not _config_path or not _config_path.exists():
                return jsonify({"status": "error", "message": "Config file not found"}), 404

            with open(_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

        return jsonify({"status": "success", "config": config}), 200
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@config_bp.route('', methods=['PUT'])
@require_auth
def update_config() -> tuple[Dict[str, Any], int]:
    """Update configuration with validation."""
    try:
        new_config = request.get_json()
        if not new_config:
            return jsonify({"status": "error", "message": "No config data provided"}), 400

        try:
            jsonschema.validate(new_config, CONFIG_SCHEMA)
        except jsonschema.ValidationError as e:
            return jsonify({"status": "error", "message": f"Invalid config: {e.message}"}), 400

        with _config_lock:
            # Backup old config
            if _config_path and _config_path.exists():
                with open(_config_path, 'r', encoding='utf-8') as f:
                    old_config = json.load(f)

                _config_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "config": old_config
                })

                if len(_config_history) > 100:
                    _config_history.pop(0)

            # Write new config
            with open(_config_path, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=2, ensure_ascii=False)

        logger.info("Config updated successfully")

        # Check if restart is required (simplified logic)
        restart_required = True  # TODO: Implement hot-reload detection

        return jsonify({
            "status": "success",
            "message": "Config updated",
            "restart_required": restart_required
        }), 200
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@config_bp.route('/history', methods=['GET'])
@require_auth
def get_config_history() -> tuple[Dict[str, Any], int]:
    """Get config change history."""
    try:
        with _config_lock:
            history = _config_history[-10:]
        return jsonify({
            "status": "success",
            "history": history
        }), 200
    except Exception as e:
        logger.error(f"Failed to get config history: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

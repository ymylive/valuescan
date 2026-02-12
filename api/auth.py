"""Authentication middleware for API endpoints."""
from functools import wraps
from flask import request, jsonify
import os
import secrets
import logging

logger = logging.getLogger(__name__)

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or ''
        expected_key = os.getenv('VALUESCAN_API_KEY') or ''

        if not expected_key or not secrets.compare_digest(api_key, expected_key):
            logger.warning(f"Unauthorized access attempt from {request.remote_addr}")
            return jsonify({"status": "error", "message": "Unauthorized"}), 401

        return f(*args, **kwargs)
    return decorated

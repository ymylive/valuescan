"""Rate limiting for API endpoints."""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

def init_rate_limiter(app):
    """Initialize rate limiter with Flask app."""
    limiter.init_app(app)
    return limiter

"""Signal Monitor Module
AI-driven signal monitoring utilities.
"""

import sys
from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent
if str(_PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_DIR))

__version__ = "1.0.0"
__author__ = "Signal Team"


def process_response_data(*args, **kwargs):
    from .message_handler import process_response_data as _impl

    return _impl(*args, **kwargs)


def get_database(*args, **kwargs):
    from .database import get_database as _impl

    return _impl(*args, **kwargs)

__all__ = [
    'process_response_data',
    'get_database',
]

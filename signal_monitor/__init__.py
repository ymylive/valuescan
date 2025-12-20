"""
ValueScan Signal Monitor Module
信号监控模块 - 从 valuescan.io 捕捉加密货币交易信号
"""

__version__ = "1.0.0"
__author__ = "ValueScan Team"

def capture_api_request(*args, **kwargs):
    from .api_monitor import capture_api_request as _impl

    return _impl(*args, **kwargs)


def process_response_data(*args, **kwargs):
    from .message_handler import process_response_data as _impl

    return _impl(*args, **kwargs)


def get_database(*args, **kwargs):
    from .database import get_database as _impl

    return _impl(*args, **kwargs)

__all__ = [
    'capture_api_request',
    'process_response_data',
    'get_database',
]

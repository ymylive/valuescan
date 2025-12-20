"""
Process Keepalive Service

A lightweight daemon for monitoring and auto-recovering critical services.
"""

from .config import ServiceConfig, ServiceState, GlobalConfig, TelegramConfig
from .health import HealthChecker
from .restarter import ServiceRestarter
from .alerter import Alerter
from .service import KeepaliveService

__all__ = [
    'ServiceConfig',
    'ServiceState',
    'GlobalConfig',
    'TelegramConfig',
    'HealthChecker',
    'ServiceRestarter',
    'Alerter',
    'KeepaliveService',
]

__version__ = '1.0.0'

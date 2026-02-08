"""Compatibility shim for signal_monitor logger imports."""

from signal_monitor.logger import logger, setup_logger

__all__ = ["logger", "setup_logger"]

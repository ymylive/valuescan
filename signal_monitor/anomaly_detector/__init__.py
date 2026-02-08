"""
异动检测系统 - Anomaly Detector

全方位加密货币异动信号检测系统
参考: Crypto-Anomaly-Detection, funding-rate-arbitrage

模块结构:
- data/: 数据提供者
- features/: 特征计算器
- detector: 信号检测器
- engine: 主引擎
"""

from .config import AnomalyConfig
from .detector import SignalDetector, Signal
from .engine import AnomalyDetectorEngine

__all__ = [
    "AnomalyConfig",
    "SignalDetector",
    "Signal",
    "AnomalyDetectorEngine",
]

__version__ = "1.0.0"

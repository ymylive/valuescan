#!/usr/bin/env python3
"""非交互式启动脚本 - 直接启动独立模式"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from futures_main import FuturesAutoTradingSystem

if __name__ == "__main__":
    system = FuturesAutoTradingSystem()
    system.run_standalone()

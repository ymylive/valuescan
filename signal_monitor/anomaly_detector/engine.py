"""
异动检测主引擎 - Freqtrade风格的统一入口
"""

from __future__ import annotations

import os
import time
import threading
from typing import Dict, List, Any, Optional, Callable

try:
    from .logger import logger
except Exception:
    import logging
    logger = logging.getLogger(__name__)

from .config import AnomalyConfig
from .data.provider import DataProvider
from .detector import SignalDetector, Signal


class AnomalyDetectorEngine:
    """
    异动检测主引擎

    统一管理数据获取、特征计算、信号检测
    """

    def __init__(self, config: Optional[AnomalyConfig] = None):
        self.config = config or AnomalyConfig()
        self.data_provider = DataProvider()
        self.detector = SignalDetector(self.config)

        # 回调函数
        self._on_signal: Optional[Callable[[Signal], None]] = None

        # 运行状态
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # 去重缓存 {signal_key: timestamp}
        self._signal_cache: Dict[str, float] = {}
        self._dedup_window = int(os.getenv("NOFX_ANOMALY_DEDUP_SECONDS", "900"))  # 5分钟去重

    def set_signal_callback(self, callback: Callable[[Signal], None]) -> None:
        """设置信号回调"""
        self._on_signal = callback

    def scan_symbol(self, symbol: str) -> List[Signal]:
        """
        扫描单个币种

        Args:
            symbol: 币种符号

        Returns:
            检测到的信号列表
        """
        try:
            # 获取数据
            ticker = self.data_provider.get_ticker(symbol)
            if not ticker:
                return []

            ohlcv = self.data_provider.get_ohlcv(symbol, "1h", 50)
            if len(ohlcv) < 10:
                return []

            volumes = [k.volume for k in ohlcv]
            closes = [k.close for k in ohlcv]

            # 获取衍生品数据
            funding_rate = self.data_provider.get_funding_rate(symbol) or 0.0
            open_interest = self.data_provider.get_open_interest(symbol) or 0.0

            # 获取BTC价格
            btc_ticker = self.data_provider.get_ticker("BTC")
            btc_price = btc_ticker.price if btc_ticker else 0.0

            # 获取情绪指数
            fgi = self.data_provider.get_fear_greed_index() or 50

            # 检测信号
            signals = self.detector.detect_from_raw(
                symbol=symbol,
                volumes=volumes,
                closes=closes,
                funding_rate=funding_rate,
                open_interest=open_interest,
                btc_price=btc_price,
                fear_greed_index=fgi,
            )

            return signals

        except Exception as e:
            logger.error(f"[AnomalyEngine] Scan {symbol} failed: {e}")
            return []

    def scan_all(self) -> List[Signal]:
        """
        扫描所有配置的币种

        Returns:
            所有检测到的信号
        """
        all_signals = []

        for symbol in self.config.symbols:
            signals = self.scan_symbol(symbol)
            for sig in signals:
                if self._should_emit(sig):
                    all_signals.append(sig)
                    if self._on_signal:
                        self._on_signal(sig)

        return all_signals

    def _should_emit(self, signal: Signal) -> bool:
        """检查信号是否应该发送（去重）"""
        key = f"{signal.symbol}:{signal.signal_type}"
        now = time.time()

        if key in self._signal_cache:
            if now - self._signal_cache[key] < self._dedup_window:
                return False

        self._signal_cache[key] = now

        # 清理过期缓存
        self._signal_cache = {
            k: v for k, v in self._signal_cache.items()
            if now - v < self._dedup_window * 2
        }

        return True

    def start(self, interval: int = 60) -> None:
        """
        启动后台扫描

        Args:
            interval: 扫描间隔（秒）
        """
        if self._running:
            return

        self._running = True

        def run():
            logger.info(f"[AnomalyEngine] Started, interval={interval}s")
            while self._running:
                try:
                    self.scan_all()
                except Exception as e:
                    logger.error(f"[AnomalyEngine] Scan error: {e}")

                time.sleep(interval)

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止后台扫描"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("[AnomalyEngine] Stopped")

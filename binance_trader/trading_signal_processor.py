"""
Trading signal processor.

Decide trading direction based on ValueScan signals and movement list status:
- Long: Alpha (110) or FOMO (113) and on movement list.
- Short: bearish signals (112/111/100) and not on movement list.
"""

import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Set


sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from signal_monitor.movement_list_cache import (
        MovementListCache,
        get_movement_list_cache,
    )
except ImportError:
    class MovementListCache:
        def is_on_movement_list(self, symbol: str) -> bool:
            return False

        def _is_cache_expired(self) -> bool:
            return True

    def get_movement_list_cache():
        return MovementListCache()


@dataclass
class TradeSignal:
    symbol: str
    direction: str
    signal_type: int
    predict_type: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    on_movement_list: bool = False
    reason: str = ""


class TradingSignalProcessor:
    """
    Trading signal processor.

    Long: Alpha (110) or FOMO (113) + on movement list.
    Short: bearish signals (112/111/100) + NOT on movement list.
    """

    BULLISH_TYPES: Set[int] = {110, 113}
    BEARISH_TYPES: Set[int] = {112, 111}
    BEARISH_PREDICT_TYPES: Set[int] = {7, 24}

    def __init__(
        self,
        movement_cache: Optional[MovementListCache] = None,
        long_enabled: bool = True,
        short_enabled: bool = False,
    ):
        self.movement_cache = movement_cache or get_movement_list_cache()
        self.long_enabled = long_enabled
        self.short_enabled = short_enabled
        self.logger = logging.getLogger(__name__)

    def process_signal(
        self,
        message_type: int,
        symbol: str,
        predict_type: Optional[int] = None,
    ) -> Optional[TradeSignal]:
        if not symbol:
            self.logger.warning("Empty symbol received; skip signal")
            return None

        symbol = self._normalize_symbol(symbol)

        cache_expired = False
        if hasattr(self.movement_cache, "_is_cache_expired"):
            cache_expired = bool(self.movement_cache._is_cache_expired())

        is_bullish = message_type in self.BULLISH_TYPES
        is_bearish = self._is_bearish_signal(message_type, predict_type)

        if cache_expired:
            if is_bullish:
                is_on_list = True
                self.logger.warning(
                    "Movement list cache expired; assume %s is on list for LONG signals",
                    symbol,
                )
            elif is_bearish:
                is_on_list = False
                self.logger.warning(
                    "Movement list cache expired; assume %s is NOT on list for SHORT signals",
                    symbol,
                )
            else:
                is_on_list = False
        else:
            is_on_list = self.movement_cache.is_on_movement_list(symbol)

        self.logger.info(
            "Signal received: type=%s, symbol=%s, predictType=%s, on_list=%s, cache_expired=%s",
            message_type,
            symbol,
            predict_type,
            is_on_list,
            cache_expired,
        )

        if is_bullish:
            return self._process_bullish_signal(message_type, symbol, is_on_list)

        if is_bearish:
            return self._process_bearish_signal(
                message_type, symbol, is_on_list, predict_type
            )

        self.logger.debug("Signal type %s not handled", message_type)
        return None

    def _normalize_symbol(self, symbol: str) -> str:
        symbol = symbol.upper().strip()
        for suffix in ["/USDT", "USDT", "/USD", "USD"]:
            if symbol.endswith(suffix):
                symbol = symbol[: -len(suffix)]
                break
        return symbol

    def _is_bearish_signal(
        self, message_type: int, predict_type: Optional[int]
    ) -> bool:
        if message_type in self.BEARISH_TYPES:
            return True
        if message_type == 100 and predict_type in self.BEARISH_PREDICT_TYPES:
            return True
        return False

    def _process_bullish_signal(
        self, message_type: int, symbol: str, is_on_list: bool
    ) -> Optional[TradeSignal]:
        signal_name = "Alpha" if message_type == 110 else "FOMO"

        if not is_on_list:
            self.logger.info(
                "Skip LONG %s: %s signal but not on movement list", symbol, signal_name
            )
            return None

        if not self.long_enabled:
            self.logger.info(
                "Skip LONG %s: %s signal but long disabled", symbol, signal_name
            )
            return None

        reason = f"{signal_name} signal + on movement list"
        self.logger.warning("Generate LONG signal: %s (%s)", symbol, reason)

        return TradeSignal(
            symbol=symbol,
            direction="LONG",
            signal_type=message_type,
            on_movement_list=True,
            reason=reason,
        )

    def _process_bearish_signal(
        self,
        message_type: int,
        symbol: str,
        is_on_list: bool,
        predict_type: Optional[int],
    ) -> Optional[TradeSignal]:
        signal_names = {
            112: "FOMO Intensify",
            111: "Capital Outflow",
        }
        if message_type == 100:
            predict_names = {7: "Risk Increase", 24: "Price Top"}
            signal_name = predict_names.get(predict_type, f"Type100-{predict_type}")
        else:
            signal_name = signal_names.get(message_type, f"Type{message_type}")

        if is_on_list:
            self.logger.info(
                "Skip SHORT %s: %s signal but on movement list", symbol, signal_name
            )
            return None

        if not self.short_enabled:
            self.logger.info(
                "Skip SHORT %s: %s signal but short disabled", symbol, signal_name
            )
            return None

        reason = f"{signal_name} signal + not on movement list"
        self.logger.warning("Generate SHORT signal: %s (%s)", symbol, reason)

        return TradeSignal(
            symbol=symbol,
            direction="SHORT",
            signal_type=message_type,
            predict_type=predict_type,
            on_movement_list=False,
            reason=reason,
        )

    def update_config(self, long_enabled: bool = None, short_enabled: bool = None):
        if long_enabled is not None:
            self.long_enabled = long_enabled
            self.logger.info(
                "Long strategy %s", "enabled" if long_enabled else "disabled"
            )
        if short_enabled is not None:
            self.short_enabled = short_enabled
            self.logger.info(
                "Short strategy %s", "enabled" if short_enabled else "disabled"
            )


_processor_instance: Optional[TradingSignalProcessor] = None


def get_trading_signal_processor(
    long_enabled: bool = True, short_enabled: bool = False
) -> TradingSignalProcessor:
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = TradingSignalProcessor(
            long_enabled=long_enabled, short_enabled=short_enabled
        )
    return _processor_instance


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("TradingSignalProcessor self-test")
    print("=" * 60)

    class MockMovementListCache:
        def __init__(self, symbols_on_list=None):
            self.symbols = set(s.upper() for s in (symbols_on_list or []))

        def is_on_movement_list(self, symbol: str) -> bool:
            return symbol.upper() in self.symbols

        def _is_cache_expired(self) -> bool:
            return False

    print("\nTest LONG signals:")
    cache = MockMovementListCache(symbols_on_list=["BTC", "ETH"])
    processor = TradingSignalProcessor(cache, long_enabled=True, short_enabled=False)
    signal = processor.process_signal(110, "BTC")
    print("BTC Alpha:", signal)
    signal = processor.process_signal(113, "XRP")
    print("XRP FOMO:", signal)

    print("\nTest SHORT signals:")
    processor = TradingSignalProcessor(cache, long_enabled=False, short_enabled=True)
    signal = processor.process_signal(112, "XRP")
    print("XRP FOMO Intensify:", signal)
    signal = processor.process_signal(111, "BTC")
    print("BTC Capital Outflow:", signal)

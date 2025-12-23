"""
浜ゆ槗淇″彿澶勭悊鍣?

鏍规嵁 ValueScan 淇″彿鍜屽紓鍔ㄦ鍗曠姸鎬佸喅瀹氫氦鏄撴柟鍚戯細
- 鍋氬: Alpha(110) 鎴?FOMO(113) + 鍦ㄥ紓鍔ㄦ鍗曚笂
- 鍋氱┖: 鐪嬭穼淇″彿(112/111/100) + 涓嶅湪寮傚姩姒滃崟涓?
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Set

import sys
from pathlib import Path

# 娣诲姞鐖剁洰褰曞埌璺緞浠ュ鍏?signal_monitor 妯″潡
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from signal_monitor.movement_list_cache import MovementListCache, get_movement_list_cache
except ImportError:
    # 濡傛灉瀵煎叆澶辫触锛屽畾涔変竴涓崰浣嶇被
    class MovementListCache:
        def is_on_movement_list(self, symbol: str) -> bool:
            return False
        def _is_cache_expired(self) -> bool:
            return True
    
    def get_movement_list_cache():
        return MovementListCache()


@dataclass
class TradeSignal:
    """浜ゆ槗淇″彿"""
    symbol: str           # 甯佺绗﹀彿 (濡?"BTC")
    direction: str        # 'LONG' or 'SHORT'
    signal_type: int      # 鍘熷淇″彿绫诲瀷 (110/113/112/111/100)
    predict_type: Optional[int] = None  # Type 100 鐨?predictType
    timestamp: datetime = field(default_factory=datetime.now)
    on_movement_list: bool = False  # 鏄惁鍦ㄥ紓鍔ㄦ鍗曚笂
    reason: str = ""      # 淇″彿鐢熸垚鍘熷洜


class TradingSignalProcessor:
    """
    浜ゆ槗淇″彿澶勭悊鍣?
    
    鍋氬閫昏緫: Alpha(110) 鎴?FOMO(113) + 鍦ㄥ紓鍔ㄦ鍗曚笂
    鍋氱┖閫昏緫: 鐪嬭穼淇″彿(112/111/100) + 涓嶅湪寮傚姩姒滃崟涓?
    """
    
    # 鐪嬫定淇″彿绫诲瀷
    BULLISH_TYPES: Set[int] = {110, 113}  # Alpha, FOMO
    
    # 鐪嬭穼淇″彿绫诲瀷
    BEARISH_TYPES: Set[int] = {112, 111}  # FOMO鍔犲墽, 璧勯噾鍑洪€?
    
    # Type 100 鐨勭湅璺?predictType
    BEARISH_PREDICT_TYPES: Set[int] = {7, 24}  # 椋庨櫓澧炲姞, 浠锋牸楂樼偣
    
    def __init__(self, 
                 movement_cache: Optional[MovementListCache] = None,
                 long_enabled: bool = True,
                 short_enabled: bool = False):
        """
        鍒濆鍖栧鐞嗗櫒
        
        Args:
            movement_cache: 寮傚姩姒滃崟缂撳瓨瀹炰緥锛孨one 鍒欎娇鐢ㄥ叏灞€鍗曚緥
            long_enabled: 鏄惁鍚敤鍋氬
            short_enabled: 鏄惁鍚敤鍋氱┖
        """
        self.movement_cache = movement_cache or get_movement_list_cache()
        self.long_enabled = long_enabled
        self.short_enabled = short_enabled
        self.logger = logging.getLogger(__name__)
    
    def process_signal(self, message_type: int, symbol: str, 
                       predict_type: Optional[int] = None) -> Optional[TradeSignal]:
        """
        澶勭悊淇″彿锛岃繑鍥炰氦鏄撲俊鍙锋垨 None
        
        Args:
            message_type: 淇″彿绫诲瀷 (110/113/112/111/100)
            symbol: 甯佺绗﹀彿
            predict_type: Type 100 鐨?predictType (7=椋庨櫓澧炲姞, 24=浠锋牸楂樼偣)
            
        Returns:
            TradeSignal with direction='LONG' or 'SHORT', or None
        """
        if not symbol:
            self.logger.warning("鏀跺埌绌虹鍙蜂俊鍙凤紝璺宠繃")
            return None
        
        # 鏍囧噯鍖栫鍙?
        symbol = self._normalize_symbol(symbol)
        
        # 妫€鏌ョ紦瀛樻槸鍚︽湁鏁?
        cache_expired = self.movement_cache._is_cache_expired()
        is_bullish = message_type in self.BULLISH_TYPES
        is_bearish = self._is_bearish_signal(message_type, predict_type)
        if cache_expired:
            if is_bullish:
                is_on_list = True
                self.logger.warning(
                    f"Movement list cache expired; assume {symbol} is on list for LONG signals"
                )
            elif is_bearish:
                is_on_list = False
                self.logger.warning(
                    f"Movement list cache expired; assume {symbol} is NOT on list for SHORT signals"
                )
            else:
                is_on_list = False
        else:
            is_on_list = self.movement_cache.is_on_movement_list(symbol)
        # 璁板綍淇″彿鎺ユ敹鏃ュ織
        self.logger.info(
            f"馃摠 鏀跺埌淇″彿: type={message_type}, symbol={symbol}, "
            f"predictType={predict_type}, 鍦ㄥ紓鍔ㄦ鍗?{is_on_list}, 缂撳瓨杩囨湡={cache_expired}"
        )
        
        # 鍋氬: (Alpha OR FOMO) - 鍗曚俊鍙峰嵆鍙紑鍗?
        if is_bullish:
            return self._process_bullish_signal(
                message_type, symbol, is_on_list
            )
        
        # 鍋氱┖: 鐪嬭穼淇″彿 AND 涓嶅湪姒滃崟涓?
        if is_bearish:
            return self._process_bearish_signal(
                message_type, symbol, is_on_list, predict_type
            )
        
        # 鍏朵粬淇″彿绫诲瀷锛屼笉澶勭悊
        self.logger.debug(f"Signal type {message_type} not handled")
        return None
    
    def _normalize_symbol(self, symbol: str) -> str:
        """鏍囧噯鍖栧竵绉嶇鍙?""
        symbol = symbol.upper().strip()
        # 鍘婚櫎甯歌鍚庣紑
        for suffix in ['/USDT', 'USDT', '/USD', 'USD']:
            if symbol.endswith(suffix):
                symbol = symbol[:-len(suffix)]
                break
        return symbol
    
    def _is_bearish_signal(self, message_type: int, 
                           predict_type: Optional[int]) -> bool:
        """鍒ゆ柇鏄惁涓虹湅璺屼俊鍙?""
        if message_type in self.BEARISH_TYPES:
            return True
        if message_type == 100 and predict_type in self.BEARISH_PREDICT_TYPES:
            return True
        return False
    
    def _process_bullish_signal(self, message_type: int, symbol: str,
                                 is_on_list: bool) -> Optional[TradeSignal]:
        """澶勭悊鐪嬫定淇″彿"""
        signal_name = "Alpha" if message_type == 110 else "FOMO"
        
        if not is_on_list:
            self.logger.info(
                f"鈴笍 璺宠繃鍋氬 {symbol}: {signal_name}淇″彿浣嗕笉鍦ㄥ紓鍔ㄦ鍗曚笂"
            )
            return None
        
        if not self.long_enabled:
            self.logger.info(
                f"鈴笍 璺宠繃鍋氬 {symbol}: {signal_name}淇″彿浣嗗仛澶氬凡绂佺敤"
            )
            return None
        
        # 鐢熸垚鍋氬淇″彿
        reason = f"{signal_name}淇″彿 + 鍦ㄥ紓鍔ㄦ鍗曚笂"
        self.logger.warning(
            f"馃煝 鐢熸垚鍋氬淇″彿: {symbol} ({reason})"
        )
        
        return TradeSignal(
            symbol=symbol,
            direction='LONG',
            signal_type=message_type,
            on_movement_list=True,
            reason=reason
        )
    
    def _process_bearish_signal(self, message_type: int, symbol: str,
                                 is_on_list: bool,
                                 predict_type: Optional[int]) -> Optional[TradeSignal]:
        """澶勭悊鐪嬭穼淇″彿"""
        # 鑾峰彇淇″彿鍚嶇О
        signal_names = {
            112: "FOMO鍔犲墽",
            111: "璧勯噾鍑洪€?,
        }
        if message_type == 100:
            predict_names = {7: "椋庨櫓澧炲姞", 24: "浠锋牸楂樼偣"}
            signal_name = predict_names.get(predict_type, f"Type100-{predict_type}")
        else:
            signal_name = signal_names.get(message_type, f"Type{message_type}")
        
        if is_on_list:
            self.logger.info(
                f"鈴笍 璺宠繃鍋氱┖ {symbol}: {signal_name}淇″彿浣嗗湪寮傚姩姒滃崟涓?
            )
            return None
        
        if not self.short_enabled:
            self.logger.info(
                f"鈴笍 璺宠繃鍋氱┖ {symbol}: {signal_name}淇″彿浣嗗仛绌哄凡绂佺敤"
            )
            return None
        
        # 鐢熸垚鍋氱┖淇″彿
        reason = f"{signal_name}淇″彿 + 涓嶅湪寮傚姩姒滃崟涓?
        self.logger.warning(
            f"馃敶 鐢熸垚鍋氱┖淇″彿: {symbol} ({reason})"
        )
        
        return TradeSignal(
            symbol=symbol,
            direction='SHORT',
            signal_type=message_type,
            predict_type=predict_type,
            on_movement_list=False,
            reason=reason
        )
    
    def update_config(self, long_enabled: bool = None, 
                      short_enabled: bool = None):
        """鏇存柊閰嶇疆"""
        if long_enabled is not None:
            self.long_enabled = long_enabled
            self.logger.info(f"鍋氬绛栫暐宸瞷'鍚敤' if long_enabled else '绂佺敤'}")
        if short_enabled is not None:
            self.short_enabled = short_enabled
            self.logger.info(f"鍋氱┖绛栫暐宸瞷'鍚敤' if short_enabled else '绂佺敤'}")


# 鍏ㄥ眬鍗曚緥
_processor_instance: Optional[TradingSignalProcessor] = None


def get_trading_signal_processor(
    long_enabled: bool = True,
    short_enabled: bool = False
) -> TradingSignalProcessor:
    """
    鑾峰彇鍏ㄥ眬浜ゆ槗淇″彿澶勭悊鍣ㄥ疄渚嬶紙鍗曚緥妯″紡锛?
    
    Args:
        long_enabled: 鏄惁鍚敤鍋氬
        short_enabled: 鏄惁鍚敤鍋氱┖
        
    Returns:
        TradingSignalProcessor: 澶勭悊鍣ㄥ疄渚?
    """
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = TradingSignalProcessor(
            long_enabled=long_enabled,
            short_enabled=short_enabled
        )
    return _processor_instance


if __name__ == "__main__":
    # 娴嬭瘯浠ｇ爜
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("娴嬭瘯浜ゆ槗淇″彿澶勭悊鍣?)
    print("=" * 60)
    
    # 鍒涘缓 mock 缂撳瓨
    class MockMovementListCache:
        def __init__(self, symbols_on_list=None):
            self.symbols = set(s.upper() for s in (symbols_on_list or []))
        
        def is_on_movement_list(self, symbol: str) -> bool:
            return symbol.upper() in self.symbols
        
        def _is_cache_expired(self) -> bool:
            return False
    
    # 娴嬭瘯鍋氬
    print("\n娴嬭瘯鍋氬淇″彿:")
    cache = MockMovementListCache(symbols_on_list=['BTC', 'ETH'])
    processor = TradingSignalProcessor(cache, long_enabled=True, short_enabled=False)
    
    # BTC 鍦ㄦ鍗曚笂锛屽簲璇ョ敓鎴愬仛澶氫俊鍙?
    signal = processor.process_signal(110, 'BTC')
    print(f"  BTC Alpha淇″彿: {signal}")
    
    # XRP 涓嶅湪姒滃崟涓婏紝涓嶅簲璇ョ敓鎴愪俊鍙?
    signal = processor.process_signal(113, 'XRP')
    print(f"  XRP FOMO淇″彿: {signal}")
    
    # 娴嬭瘯鍋氱┖
    print("\n娴嬭瘯鍋氱┖淇″彿:")
    processor = TradingSignalProcessor(cache, long_enabled=False, short_enabled=True)
    
    # XRP 涓嶅湪姒滃崟涓婏紝搴旇鐢熸垚鍋氱┖淇″彿
    signal = processor.process_signal(112, 'XRP')
    print(f"  XRP FOMO鍔犲墽淇″彿: {signal}")
    
    # BTC 鍦ㄦ鍗曚笂锛屼笉搴旇鐢熸垚鍋氱┖淇″彿
    signal = processor.process_signal(111, 'BTC')
    print(f"  BTC 璧勯噾鍑洪€冧俊鍙? {signal}")

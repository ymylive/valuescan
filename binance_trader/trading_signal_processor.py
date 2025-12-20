"""
交易信号处理器

根据 ValueScan 信号和异动榜单状态决定交易方向：
- 做多: Alpha(110) 或 FOMO(113) + 在异动榜单上
- 做空: 看跌信号(112/111/100) + 不在异动榜单上
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Set

import sys
from pathlib import Path

# 添加父目录到路径以导入 signal_monitor 模块
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from signal_monitor.movement_list_cache import MovementListCache, get_movement_list_cache
except ImportError:
    # 如果导入失败，定义一个占位类
    class MovementListCache:
        def is_on_movement_list(self, symbol: str) -> bool:
            return False
        def _is_cache_expired(self) -> bool:
            return True
    
    def get_movement_list_cache():
        return MovementListCache()


@dataclass
class TradeSignal:
    """交易信号"""
    symbol: str           # 币种符号 (如 "BTC")
    direction: str        # 'LONG' or 'SHORT'
    signal_type: int      # 原始信号类型 (110/113/112/111/100)
    predict_type: Optional[int] = None  # Type 100 的 predictType
    timestamp: datetime = field(default_factory=datetime.now)
    on_movement_list: bool = False  # 是否在异动榜单上
    reason: str = ""      # 信号生成原因


class TradingSignalProcessor:
    """
    交易信号处理器
    
    做多逻辑: Alpha(110) 或 FOMO(113) + 在异动榜单上
    做空逻辑: 看跌信号(112/111/100) + 不在异动榜单上
    """
    
    # 看涨信号类型
    BULLISH_TYPES: Set[int] = {110, 113}  # Alpha, FOMO
    
    # 看跌信号类型
    BEARISH_TYPES: Set[int] = {112, 111}  # FOMO加剧, 资金出逃
    
    # Type 100 的看跌 predictType
    BEARISH_PREDICT_TYPES: Set[int] = {7, 24}  # 风险增加, 价格高点
    
    def __init__(self, 
                 movement_cache: Optional[MovementListCache] = None,
                 long_enabled: bool = True,
                 short_enabled: bool = False):
        """
        初始化处理器
        
        Args:
            movement_cache: 异动榜单缓存实例，None 则使用全局单例
            long_enabled: 是否启用做多
            short_enabled: 是否启用做空
        """
        self.movement_cache = movement_cache or get_movement_list_cache()
        self.long_enabled = long_enabled
        self.short_enabled = short_enabled
        self.logger = logging.getLogger(__name__)
    
    def process_signal(self, message_type: int, symbol: str, 
                       predict_type: Optional[int] = None) -> Optional[TradeSignal]:
        """
        处理信号，返回交易信号或 None
        
        Args:
            message_type: 信号类型 (110/113/112/111/100)
            symbol: 币种符号
            predict_type: Type 100 的 predictType (7=风险增加, 24=价格高点)
            
        Returns:
            TradeSignal with direction='LONG' or 'SHORT', or None
        """
        if not symbol:
            self.logger.warning("收到空符号信号，跳过")
            return None
        
        # 标准化符号
        symbol = self._normalize_symbol(symbol)
        
        # 检查缓存是否有效
        cache_expired = self.movement_cache._is_cache_expired()
        
        # 如果缓存过期，对于做多信号假设在榜单上（允许开单）
        # 对于做空信号则跳过（保守策略）
        if cache_expired:
            is_on_list = True  # 假设在榜单上，允许做多
            self.logger.warning(
                f"⚠️ 异动榜单缓存已过期，假设 {symbol} 在榜单上"
            )
        else:
            is_on_list = self.movement_cache.is_on_movement_list(symbol)
        
        # 记录信号接收日志
        self.logger.info(
            f"📨 收到信号: type={message_type}, symbol={symbol}, "
            f"predictType={predict_type}, 在异动榜单={is_on_list}, 缓存过期={cache_expired}"
        )
        
        # 做多: (Alpha OR FOMO) - 单信号即可开单
        if message_type in self.BULLISH_TYPES:
            return self._process_bullish_signal(
                message_type, symbol, is_on_list
            )
        
        # 做空: 看跌信号 AND 不在榜单上
        is_bearish = self._is_bearish_signal(message_type, predict_type)
        if is_bearish:
            return self._process_bearish_signal(
                message_type, symbol, is_on_list, predict_type
            )
        
        # 其他信号类型，不处理
        self.logger.debug(f"信号类型 {message_type} 不在处理范围内")
        return None
    
    def _normalize_symbol(self, symbol: str) -> str:
        """标准化币种符号"""
        symbol = symbol.upper().strip()
        # 去除常见后缀
        for suffix in ['/USDT', 'USDT', '/USD', 'USD']:
            if symbol.endswith(suffix):
                symbol = symbol[:-len(suffix)]
                break
        return symbol
    
    def _is_bearish_signal(self, message_type: int, 
                           predict_type: Optional[int]) -> bool:
        """判断是否为看跌信号"""
        if message_type in self.BEARISH_TYPES:
            return True
        if message_type == 100 and predict_type in self.BEARISH_PREDICT_TYPES:
            return True
        return False
    
    def _process_bullish_signal(self, message_type: int, symbol: str,
                                 is_on_list: bool) -> Optional[TradeSignal]:
        """处理看涨信号"""
        signal_name = "Alpha" if message_type == 110 else "FOMO"
        
        if not is_on_list:
            self.logger.info(
                f"⏭️ 跳过做多 {symbol}: {signal_name}信号但不在异动榜单上"
            )
            return None
        
        if not self.long_enabled:
            self.logger.info(
                f"⏭️ 跳过做多 {symbol}: {signal_name}信号但做多已禁用"
            )
            return None
        
        # 生成做多信号
        reason = f"{signal_name}信号 + 在异动榜单上"
        self.logger.warning(
            f"🟢 生成做多信号: {symbol} ({reason})"
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
        """处理看跌信号"""
        # 获取信号名称
        signal_names = {
            112: "FOMO加剧",
            111: "资金出逃",
        }
        if message_type == 100:
            predict_names = {7: "风险增加", 24: "价格高点"}
            signal_name = predict_names.get(predict_type, f"Type100-{predict_type}")
        else:
            signal_name = signal_names.get(message_type, f"Type{message_type}")
        
        if is_on_list:
            self.logger.info(
                f"⏭️ 跳过做空 {symbol}: {signal_name}信号但在异动榜单上"
            )
            return None
        
        if not self.short_enabled:
            self.logger.info(
                f"⏭️ 跳过做空 {symbol}: {signal_name}信号但做空已禁用"
            )
            return None
        
        # 生成做空信号
        reason = f"{signal_name}信号 + 不在异动榜单上"
        self.logger.warning(
            f"🔴 生成做空信号: {symbol} ({reason})"
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
        """更新配置"""
        if long_enabled is not None:
            self.long_enabled = long_enabled
            self.logger.info(f"做多策略已{'启用' if long_enabled else '禁用'}")
        if short_enabled is not None:
            self.short_enabled = short_enabled
            self.logger.info(f"做空策略已{'启用' if short_enabled else '禁用'}")


# 全局单例
_processor_instance: Optional[TradingSignalProcessor] = None


def get_trading_signal_processor(
    long_enabled: bool = True,
    short_enabled: bool = False
) -> TradingSignalProcessor:
    """
    获取全局交易信号处理器实例（单例模式）
    
    Args:
        long_enabled: 是否启用做多
        short_enabled: 是否启用做空
        
    Returns:
        TradingSignalProcessor: 处理器实例
    """
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = TradingSignalProcessor(
            long_enabled=long_enabled,
            short_enabled=short_enabled
        )
    return _processor_instance


if __name__ == "__main__":
    # 测试代码
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("测试交易信号处理器")
    print("=" * 60)
    
    # 创建 mock 缓存
    class MockMovementListCache:
        def __init__(self, symbols_on_list=None):
            self.symbols = set(s.upper() for s in (symbols_on_list or []))
        
        def is_on_movement_list(self, symbol: str) -> bool:
            return symbol.upper() in self.symbols
        
        def _is_cache_expired(self) -> bool:
            return False
    
    # 测试做多
    print("\n测试做多信号:")
    cache = MockMovementListCache(symbols_on_list=['BTC', 'ETH'])
    processor = TradingSignalProcessor(cache, long_enabled=True, short_enabled=False)
    
    # BTC 在榜单上，应该生成做多信号
    signal = processor.process_signal(110, 'BTC')
    print(f"  BTC Alpha信号: {signal}")
    
    # XRP 不在榜单上，不应该生成信号
    signal = processor.process_signal(113, 'XRP')
    print(f"  XRP FOMO信号: {signal}")
    
    # 测试做空
    print("\n测试做空信号:")
    processor = TradingSignalProcessor(cache, long_enabled=False, short_enabled=True)
    
    # XRP 不在榜单上，应该生成做空信号
    signal = processor.process_signal(112, 'XRP')
    print(f"  XRP FOMO加剧信号: {signal}")
    
    # BTC 在榜单上，不应该生成做空信号
    signal = processor.process_signal(111, 'BTC')
    print(f"  BTC 资金出逃信号: {signal}")

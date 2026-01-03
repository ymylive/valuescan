"""
异动榜单缓存模块
缓存 valuescan.io 的 getFundsMovementPage API 数据
用于判断币种是否在异动榜单上（做空策略的前置条件）
"""

import json
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

try:
    from .logger import logger
except ImportError:
    from logger import logger

# 北京时区 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))

# 缓存文件路径
CACHE_FILE = Path(__file__).parent / "movement_list_cache.json"

# 缓存过期时间（秒）- 异动榜单更新频繁，设置较短的过期时间
CACHE_EXPIRE_TIME = 300  # 5分钟


@dataclass
class MovementItem:
    """异动榜单项"""
    symbol: str
    alpha: bool  # 是否有Alpha信号
    fomo: bool  # 是否有FOMO信号
    fomo_escalation: bool  # 是否FOMO加剧
    observe: bool  # 是否在观察列表
    gains: float  # 涨幅
    decline: float  # 跌幅
    bullish_ratio: float  # 看涨比例
    raw_data: Dict  # 原始数据


class MovementListCache:
    """
    异动榜单缓存
    
    用途：
    1. 缓存 getFundsMovementPage API 返回的数据
    2. 提供快速查询接口，判断币种是否在异动榜单上
    3. 做空策略的前置条件：只有不在异动榜单上的币种才能做空
    """

    def __init__(self, expire_time: int = CACHE_EXPIRE_TIME):
        """
        初始化缓存
        
        Args:
            expire_time: 缓存过期时间（秒）
        """
        self.expire_time = expire_time
        self._movement_map: Dict[str, MovementItem] = {}  # symbol -> MovementItem
        self._last_update_time: Optional[float] = None
        self._update_lock = threading.Lock()
        
        # 启动时尝试从缓存文件加载
        self._load_from_cache_file()
        
        logger.info(f"📊 异动榜单缓存已初始化 (过期时间: {expire_time}秒)")

    def _is_cache_expired(self) -> bool:
        """检查缓存是否过期"""
        if not self._last_update_time:
            return True
        elapsed = time.time() - self._last_update_time
        return elapsed >= self.expire_time

    def _load_from_cache_file(self):
        """从缓存文件加载"""
        if not CACHE_FILE.exists():
            return

        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)

            timestamp = data.get('timestamp', 0)
            items = data.get('items', [])

            # 检查缓存是否过期
            if time.time() - timestamp > self.expire_time * 2:
                logger.warning("异动榜单缓存文件过期，等待新数据")
                return

            self._movement_map.clear()
            for item_data in items:
                item = self._parse_item(item_data)
                if item:
                    self._movement_map[item.symbol.upper()] = item

            self._last_update_time = timestamp
            logger.info(f"✅ 从缓存文件加载 {len(self._movement_map)} 个异动币种")
        except Exception as e:
            logger.warning(f"加载异动榜单缓存文件失败: {e}")

    def _save_to_cache_file(self):
        """保存到缓存文件"""
        try:
            items = [item.raw_data for item in self._movement_map.values()]
            data = {
                'timestamp': self._last_update_time,
                'count': len(items),
                'items': items,
                'updated_at': datetime.now(BEIJING_TZ).isoformat()
            }

            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"异动榜单缓存已保存到文件")
        except Exception as e:
            logger.warning(f"保存异动榜单缓存文件失败: {e}")

    def _parse_item(self, data: Dict) -> Optional[MovementItem]:
        """解析单个异动项"""
        try:
            symbol = data.get('symbol', '')
            if not symbol:
                return None

            # 处理 alpha 字段（可能是 true/false/""）
            alpha_val = data.get('alpha', False)
            alpha = alpha_val is True or alpha_val == 'true'

            # 处理 fomo 字段
            fomo_val = data.get('fomo', False)
            fomo = fomo_val is True or fomo_val == 'true'

            # 处理 fomoEscalation 字段
            fomo_esc_val = data.get('fomoEscalation', False)
            fomo_escalation = fomo_esc_val is True or fomo_esc_val == 'true'

            # 处理 observe 字段
            observe_val = data.get('observe', False)
            observe = observe_val is True or observe_val == 'true'

            return MovementItem(
                symbol=symbol.upper(),
                alpha=alpha,
                fomo=fomo,
                fomo_escalation=fomo_escalation,
                observe=observe,
                gains=float(data.get('gains', 0) or 0),
                decline=float(data.get('decline', 0) or 0),
                bullish_ratio=float(data.get('bullishRatio', 0) or 0),
                raw_data=data
            )
        except Exception as e:
            logger.debug(f"解析异动项失败: {e}")
            return None

    def update_from_api_response(self, response_data: Dict) -> bool:
        """
        从 API 响应更新缓存
        
        Args:
            response_data: getFundsMovementPage API 的响应数据
            
        Returns:
            bool: 更新成功返回 True
        """
        with self._update_lock:
            try:
                # 检查响应格式
                if response_data.get('code') != 200:
                    logger.warning(f"异动榜单 API 返回错误: {response_data.get('msg')}")
                    return False

                data_list = response_data.get('data', [])
                if not isinstance(data_list, list):
                    logger.warning("异动榜单数据格式错误")
                    return False

                # 清空旧数据
                old_count = len(self._movement_map)
                self._movement_map.clear()

                # 解析新数据
                for item_data in data_list:
                    item = self._parse_item(item_data)
                    if item:
                        self._movement_map[item.symbol] = item

                self._last_update_time = time.time()
                self._save_to_cache_file()

                logger.info(
                    f"✅ 异动榜单缓存已更新: {len(self._movement_map)} 个币种 "
                    f"(旧: {old_count})"
                )
                return True

            except Exception as e:
                logger.error(f"更新异动榜单缓存失败: {e}")
                return False

    def is_on_movement_list(self, symbol: str) -> bool:
        """
        检查币种是否在异动榜单上
        
        Args:
            symbol: 币种符号（如 'BTC', 'ETH'）
            
        Returns:
            bool: 在榜单上返回 True，否则返回 False
        """
        if not symbol:
            return False

        symbol_upper = symbol.upper().strip()
        
        # 去除常见后缀
        for suffix in ['/USDT', 'USDT', '/USD', 'USD']:
            if symbol_upper.endswith(suffix):
                symbol_upper = symbol_upper[:-len(suffix)]
                break

        return symbol_upper in self._movement_map

    def get_movement_item(self, symbol: str) -> Optional[MovementItem]:
        """
        获取币种的异动信息
        
        Args:
            symbol: 币种符号
            
        Returns:
            MovementItem 或 None
        """
        if not symbol:
            return None

        symbol_upper = symbol.upper().strip()
        for suffix in ['/USDT', 'USDT', '/USD', 'USD']:
            if symbol_upper.endswith(suffix):
                symbol_upper = symbol_upper[:-len(suffix)]
                break

        return self._movement_map.get(symbol_upper)

    def get_all_symbols(self) -> List[str]:
        """获取所有在异动榜单上的币种"""
        return sorted(self._movement_map.keys())

    def get_symbols_with_alpha(self) -> List[str]:
        """获取有 Alpha 信号的币种"""
        return sorted([
            symbol for symbol, item in self._movement_map.items()
            if item.alpha
        ])

    def get_symbols_with_fomo(self) -> List[str]:
        """获取有 FOMO 信号的币种"""
        return sorted([
            symbol for symbol, item in self._movement_map.items()
            if item.fomo
        ])

    def get_symbols_with_fomo_escalation(self) -> List[str]:
        """获取 FOMO 加剧的币种"""
        return sorted([
            symbol for symbol, item in self._movement_map.items()
            if item.fomo_escalation
        ])

    def get_cache_info(self) -> Dict:
        """获取缓存信息"""
        return {
            'count': len(self._movement_map),
            'last_update': datetime.fromtimestamp(
                self._last_update_time, BEIJING_TZ
            ).isoformat() if self._last_update_time else None,
            'is_expired': self._is_cache_expired(),
            'expire_time': self.expire_time,
            'alpha_count': len(self.get_symbols_with_alpha()),
            'fomo_count': len(self.get_symbols_with_fomo()),
            'fomo_escalation_count': len(self.get_symbols_with_fomo_escalation())
        }

    def can_short(self, symbol: str) -> bool:
        """
        检查币种是否可以做空
        
        做空条件：币种不在异动榜单上
        
        Args:
            symbol: 币种符号
            
        Returns:
            bool: 可以做空返回 True
        """
        # 如果缓存过期，保守起见返回 False（不做空）
        if self._is_cache_expired():
            logger.warning(f"异动榜单缓存已过期，暂不允许做空 {symbol}")
            return False

        # 不在榜单上才能做空
        return not self.is_on_movement_list(symbol)


# 全局单例
_cache_instance: Optional[MovementListCache] = None


def get_movement_list_cache() -> MovementListCache:
    """
    获取全局异动榜单缓存实例（单例模式）
    
    Returns:
        MovementListCache: 缓存实例
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = MovementListCache()
    return _cache_instance


def is_on_movement_list(symbol: str) -> bool:
    """
    便捷函数: 检查币种是否在异动榜单上
    
    Args:
        symbol: 币种符号
        
    Returns:
        bool: 在榜单上返回 True
    """
    cache = get_movement_list_cache()
    return cache.is_on_movement_list(symbol)


def can_short_symbol(symbol: str) -> bool:
    """
    便捷函数: 检查币种是否可以做空
    
    Args:
        symbol: 币种符号
        
    Returns:
        bool: 可以做空返回 True
    """
    cache = get_movement_list_cache()
    return cache.can_short(symbol)


if __name__ == "__main__":
    # 测试代码
    print("测试异动榜单缓存模块")
    print("=" * 60)

    cache = get_movement_list_cache()

    # 显示缓存信息
    info = cache.get_cache_info()
    print(f"缓存信息: {json.dumps(info, indent=2, ensure_ascii=False)}")
    print()

    # 模拟 API 响应
    mock_response = {
        "code": 200,
        "msg": "success",
        "data": [
            {
                "symbol": "XRP",
                "alpha": True,
                "fomo": False,
                "fomoEscalation": False,
                "observe": True,
                "gains": 5.2,
                "decline": 0,
                "bullishRatio": 0.65
            },
            {
                "symbol": "BEAT",
                "alpha": False,
                "fomo": True,
                "fomoEscalation": True,
                "observe": False,
                "gains": 12.5,
                "decline": 0,
                "bullishRatio": 0.78
            }
        ]
    }

    print("模拟更新缓存...")
    cache.update_from_api_response(mock_response)
    print()

    # 测试查询
    test_symbols = ['XRP', 'BEAT', 'BTC', 'ETH']
    print("测试币种查询:")
    for symbol in test_symbols:
        on_list = cache.is_on_movement_list(symbol)
        can_short = cache.can_short(symbol)
        status = "📊 在榜单" if on_list else "❌ 不在榜单"
        short_status = "✅ 可做空" if can_short else "🚫 不可做空"
        print(f"  {symbol}: {status}, {short_status}")

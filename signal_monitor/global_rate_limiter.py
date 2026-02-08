"""
全局API限流管理器
使用令牌桶算法，支持多数据源的全局限流协调
"""

import time
import threading
from typing import Dict, Optional
from logger import logger


class GlobalRateLimiter:
    """全局API限流管理器 - 令牌桶算法"""

    def __init__(self):
        # 各数据源的限流配置 (每分钟请求数)
        self._limiters: Dict[str, Dict] = {
            'coingecko': {
                'limit': 45,           # 每分钟45次（保守）
                'window': 60,          # 时间窗口60秒
                'tokens': 45,          # 当前令牌数
                'last_refill': time.time()
            },
            'binance': {
                'limit': 1000,         # 每分钟1000次
                'window': 60,
                'tokens': 1000,
                'last_refill': time.time()
            },
            'coinmarketcap': {
                'limit': 30,           # 每分钟30次（保守）
                'window': 60,
                'tokens': 30,
                'last_refill': time.time()
            },
            'cmc': {                   # CMC别名
                'limit': 30,
                'window': 60,
                'tokens': 30,
                'last_refill': time.time()
            },
            'cryptocompare': {
                'limit': 100,          # 每分钟100次
                'window': 60,
                'tokens': 100,
                'last_refill': time.time()
            },
            'binance_futures': {
                'limit': 1000,         # 合约API限流
                'window': 60,
                'tokens': 1000,
                'last_refill': time.time()
            },
            'etherscan': {
                'limit': 250,          # 每分钟250次（5次/秒）
                'window': 60,
                'tokens': 250,
                'last_refill': time.time()
            },
            'defillama': {
                'limit': 300,          # DeFiLlama无限制，设置保守值
                'window': 60,
                'tokens': 300,
                'last_refill': time.time()
            },
        }
        self._lock = threading.Lock()
        self._stats: Dict[str, Dict] = {}  # 统计信息

    def acquire(self, source: str, tokens: int = 1) -> bool:
        """
        尝试获取令牌

        Args:
            source: 数据源名称
            tokens: 需要的令牌数

        Returns:
            bool: 是否成功获取令牌
        """
        source_lower = source.lower()

        with self._lock:
            limiter = self._limiters.get(source_lower)
            if not limiter:
                # 未知源，放行但记录日志
                logger.debug(f"[RateLimiter] Unknown source: {source}, allowing request")
                return True

            # 令牌桶补充
            now = time.time()
            elapsed = now - limiter['last_refill']

            # 计算应补充的令牌数
            if elapsed > 0:
                refill_rate = limiter['limit'] / limiter['window']
                refill_tokens = int(elapsed * refill_rate)

                if refill_tokens > 0:
                    limiter['tokens'] = min(limiter['limit'], limiter['tokens'] + refill_tokens)
                    limiter['last_refill'] = now

            # 尝试消耗令牌
            if limiter['tokens'] >= tokens:
                limiter['tokens'] -= tokens
                self._update_stats(source_lower, success=True)
                logger.debug(f"[RateLimiter] {source}: acquired {tokens} token(s), remaining: {limiter['tokens']}")
                return True
            else:
                self._update_stats(source_lower, success=False)
                logger.warning(f"[RateLimiter] {source}: rate limit exceeded, tokens: {limiter['tokens']}/{limiter['limit']}")
                return False

    def wait_and_acquire(self, source: str, tokens: int = 1, timeout: float = 30.0) -> bool:
        """
        等待并获取令牌（阻塞式）

        Args:
            source: 数据源名称
            tokens: 需要的令牌数
            timeout: 超时时间（秒）

        Returns:
            bool: 是否成功获取令牌

        Raises:
            TimeoutError: 超时未获取到令牌
        """
        start = time.time()
        attempt = 0

        while time.time() - start < timeout:
            if self.acquire(source, tokens):
                if attempt > 0:
                    logger.info(f"[RateLimiter] {source}: acquired after {attempt} attempts")
                return True

            attempt += 1
            time.sleep(0.5)  # 等待500ms后重试

        logger.error(f"[RateLimiter] {source}: timeout after {timeout}s")
        raise TimeoutError(f"Failed to acquire rate limit for {source} after {timeout}s")

    def _update_stats(self, source: str, success: bool):
        """更新统计信息"""
        if source not in self._stats:
            self._stats[source] = {
                'total_requests': 0,
                'successful_requests': 0,
                'rejected_requests': 0,
                'last_request_time': None
            }

        stats = self._stats[source]
        stats['total_requests'] += 1
        stats['last_request_time'] = time.time()

        if success:
            stats['successful_requests'] += 1
        else:
            stats['rejected_requests'] += 1

    def get_stats(self, source: Optional[str] = None) -> Dict:
        """
        获取统计信息

        Args:
            source: 数据源名称，None表示获取所有源的统计

        Returns:
            dict: 统计信息
        """
        with self._lock:
            if source:
                source_lower = source.lower()
                return {
                    'source': source,
                    'stats': self._stats.get(source_lower, {}),
                    'limiter': self._limiters.get(source_lower, {})
                }
            else:
                return {
                    'stats': dict(self._stats),
                    'limiters': {k: {'limit': v['limit'], 'tokens': v['tokens']}
                                for k, v in self._limiters.items()}
                }

    def reset_stats(self):
        """重置统计信息"""
        with self._lock:
            self._stats.clear()
            logger.info("[RateLimiter] Stats reset")

    def add_source(self, source: str, limit: int, window: int = 60):
        """
        动态添加数据源限流配置

        Args:
            source: 数据源名称
            limit: 每个时间窗口的请求限制
            window: 时间窗口（秒）
        """
        source_lower = source.lower()
        with self._lock:
            self._limiters[source_lower] = {
                'limit': limit,
                'window': window,
                'tokens': limit,
                'last_refill': time.time()
            }
            logger.info(f"[RateLimiter] Added source: {source}, limit: {limit}/{window}s")


# 全局单例
_global_limiter: Optional[GlobalRateLimiter] = None
_limiter_lock = threading.Lock()


def get_global_limiter() -> GlobalRateLimiter:
    """获取全局限流器单例"""
    global _global_limiter

    if _global_limiter is None:
        with _limiter_lock:
            if _global_limiter is None:
                _global_limiter = GlobalRateLimiter()
                logger.info("[RateLimiter] Global rate limiter initialized")

    return _global_limiter


def rate_limit_wrapper(source: str):
    """
    限流装饰器（兼容旧代码）

    Usage:
        @rate_limit_wrapper('binance')
        def fetch_data():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            limiter = get_global_limiter()
            limiter.wait_and_acquire(source)
            return func(*args, **kwargs)
        return wrapper
    return decorator


if __name__ == '__main__':
    # 测试代码
    limiter = get_global_limiter()

    # 测试获取令牌
    print("Testing rate limiter...")

    for i in range(50):
        success = limiter.acquire('coingecko')
        print(f"Request {i+1}: {'✓' if success else '✗'}")
        time.sleep(0.1)

    # 打印统计
    stats = limiter.get_stats()
    print("\nStats:", stats)

"""
币安 Alpha 与合约代币交集缓存模块
定期从 API 获取交集数据并缓存到内存
"""

import json
import os
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

try:
    from .logger import logger
except ImportError:
    from logger import logger

# 导入代理配置
try:
    from .config import SOCKS5_PROXY, HTTP_PROXY
except ImportError:
    try:
        from config import SOCKS5_PROXY, HTTP_PROXY
    except ImportError:
        SOCKS5_PROXY = ""
        HTTP_PROXY = ""

try:
    import requests
except ImportError:
    logger.error("❌ 需要安装 requests 库")
    logger.error("   运行: pip install requests")
    requests = None

# 北京时区 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))

# API URLs
ALPHA_API_URL = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list"
FUTURES_API_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"

# 缓存刷新间隔（秒）
CACHE_REFRESH_INTERVAL = 60 * 60  # 1小时

# 缓存文件路径（用于持久化，重启后可快速加载）
CACHE_FILE = Path(__file__).parent / "binance_alpha_intersection_cache.json"


def _get_proxies():
    """
    获取代理配置

    Returns:
        dict: requests库使用的代理配置，如果没有配置则返回None
    """
    if os.getenv("NOFX_NO_PROXY", "0") == "1":
        return None

    def _read_env_proxy(names):
        for name in names:
            val = os.getenv(name) or os.getenv(name.lower())
            if val and isinstance(val, str) and val.strip():
                return val.strip()
        return ""

    # 优先使用 SOCKS5 代理（配置文件）
    if SOCKS5_PROXY and isinstance(SOCKS5_PROXY, str) and SOCKS5_PROXY.strip():
        proxy_url = SOCKS5_PROXY.strip()
        return {
            'http': proxy_url,
            'https': proxy_url
        }

    # 其次使用 HTTP 代理（配置文件）
    if HTTP_PROXY and isinstance(HTTP_PROXY, str) and HTTP_PROXY.strip():
        proxy_url = HTTP_PROXY.strip()
        return {
            'http': proxy_url,
            'https': proxy_url
        }

    # 环境变量回退（systemd Environment= / export）
    env_socks = _read_env_proxy(["SOCKS5_PROXY", "ALL_PROXY"])
    if env_socks:
        return {'http': env_socks, 'https': env_socks}

    env_http = _read_env_proxy(["HTTPS_PROXY", "HTTP_PROXY"])
    if env_http:
        return {'http': env_http, 'https': env_http}

    return None


def _is_socks_dependency_error(exc: Exception, proxies: dict) -> bool:
    if not proxies:
        return False
    proxy_url = str(proxies.get("https") or proxies.get("http") or "").lower()
    if not proxy_url.startswith("socks"):
        return False

    req_exc = getattr(requests, "exceptions", None) if requests else None
    if req_exc and isinstance(exc, req_exc.InvalidSchema):
        return True

    text = str(exc).lower()
    return "socks" in text and (
        "dependency" in text or "missing" in text or "pysocks" in text
    )


class BinanceAlphaCache:
    """
    币安 Alpha 与合约代币交集缓存
    自动定期刷新，提供快速查询接口
    """

    def __init__(self, refresh_interval=CACHE_REFRESH_INTERVAL):
        """
        初始化缓存

        Args:
            refresh_interval: 缓存刷新间隔（秒），默认1小时
        """
        self.refresh_interval = refresh_interval
        self._intersection_set = set()  # 交集代币集合（大写）
        self._last_update_time = None
        self._update_lock = threading.Lock()
        self._refresh_thread = None
        self._stop_flag = threading.Event()

        # 显示代理配置（如果有）
        proxies = _get_proxies()
        if proxies:
            proxy_url = proxies.get('https', proxies.get('http', ''))
            # 隐藏密码部分
            if '@' in proxy_url:
                parts = proxy_url.split('@')
                if len(parts) == 2:
                    protocol_user = parts[0].split('//')
                    if len(protocol_user) == 2:
                        protocol = protocol_user[0]
                        user_part = protocol_user[1].split(':')[0] if ':' in protocol_user[1] else protocol_user[1]
                        masked_url = f"{protocol}//{user_part}:***@{parts[1]}"
                        logger.info(f"🌐 使用代理: {masked_url}")
            else:
                logger.info(f"🌐 使用代理: {proxy_url}")
        else:
            logger.debug("不使用代理（直连）")

        # 启动时尝试从缓存文件加载
        self._load_from_cache_file()

        # 如果缓存为空或过期，立即刷新
        if not self._intersection_set or self._is_cache_expired():
            logger.info("缓存为空或过期，立即获取币安Alpha交集...")
            self.refresh_now()

    def _is_cache_expired(self):
        """检查缓存是否过期"""
        if not self._last_update_time:
            return True
        elapsed = time.time() - self._last_update_time
        return elapsed >= self.refresh_interval

    def _load_from_cache_file(self):
        """从缓存文件加载（如果存在）"""
        if not CACHE_FILE.exists():
            return

        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)

            timestamp = data.get('timestamp', 0)
            tokens = data.get('tokens', [])

            # 检查缓存是否过期（超过2倍刷新间隔视为过期）
            if time.time() - timestamp > self.refresh_interval * 2:
                logger.warning(f"缓存文件过期，将重新获取")
                return

            self._intersection_set = set(token.upper() for token in tokens)
            self._last_update_time = timestamp

            logger.info(f"✅ 从缓存文件加载 {len(self._intersection_set)} 个币安Alpha交集代币")
        except Exception as e:
            logger.warning(f"加载缓存文件失败: {e}")

    def _save_to_cache_file(self):
        """保存到缓存文件"""
        try:
            data = {
                'timestamp': self._last_update_time,
                'tokens': sorted(self._intersection_set),
                'count': len(self._intersection_set),
                'updated_at': datetime.now(BEIJING_TZ).isoformat()
            }

            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"缓存已保存到文件: {CACHE_FILE}")
        except Exception as e:
            logger.warning(f"保存缓存文件失败: {e}")

    def _get_alpha_tokens(self):
        """获取币安 Alpha 代币列表"""
        if not requests:
            return set()

        proxies = _get_proxies()
        last_exc: Optional[Exception] = None

        for attempt in range(3):
            try:
                response = requests.get(
                    ALPHA_API_URL,
                    headers={"User-Agent": "Mozilla/5.0"},
                    proxies=proxies,
                    timeout=15,
                )
                response.raise_for_status()
                data = response.json()

                if data.get("code") != "000000":
                    raise RuntimeError(f"API 返回错误: {data.get('message')}")

                tokens = data.get("data", [])
                alpha_symbols = set()

                for token in tokens:
                    symbol = token.get("cexCoinName") or token.get("symbol")
                    if symbol:
                        alpha_symbols.add(symbol.upper().strip())

                logger.debug(f"获取到 {len(alpha_symbols)} 个 Alpha 代币")
                return alpha_symbols

            except Exception as e:
                last_exc = e
                if _is_socks_dependency_error(e, proxies or {}):
                    logger.warning(
                        "⚠️ 检测到 SOCKS5 代理但缺少 socks 支持，请安装: "
                        "pip3 install pysocks 或 pip3 install 'requests[socks]'"
                    )
                    break
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                break

        if last_exc:
            logger.warning(f"获取 Alpha 代币失败: {last_exc}")
        return set()

    def _get_futures_tokens(self):
        """获取币安合约代币列表（永续合约）"""
        if not requests:
            return set()

        proxies = _get_proxies()
        last_exc: Optional[Exception] = None

        for attempt in range(3):
            try:
                response = requests.get(
                    FUTURES_API_URL,
                    headers={"User-Agent": "Mozilla/5.0"},
                    proxies=proxies,
                    timeout=20,
                )
                response.raise_for_status()
                data = response.json()

                symbols_data = data.get("symbols", [])
                futures_symbols = set()

                for symbol_info in symbols_data:
                    status = symbol_info.get("status") or symbol_info.get("contractStatus")
                    if status != "TRADING":
                        continue

                    contract_type = str(symbol_info.get("contractType", "")).upper()
                    if contract_type != "PERPETUAL":
                        continue

                base_asset = symbol_info.get("baseAsset")
                if base_asset:
                    futures_symbols.add(base_asset.upper().strip())

                logger.debug(f"获取到 {len(futures_symbols)} 个合约代币")
                return futures_symbols

            except Exception as e:
                last_exc = e
                if _is_socks_dependency_error(e, proxies or {}):
                    logger.warning(
                        "⚠️ 检测到 SOCKS5 代理但缺少 socks 支持，请安装: "
                        "pip3 install pysocks 或 pip3 install 'requests[socks]'"
                    )
                    break
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                break

        if last_exc:
            logger.warning(f"获取合约代币失败: {last_exc}")
        return set()

    def refresh_now(self):
        """
        立即刷新缓存（同步方法）

        Returns:
            bool: 刷新成功返回 True，否则返回 False
        """
        with self._update_lock:
            logger.info("🔄 开始刷新币安Alpha交集缓存...")

            # 获取两个列表
            alpha_tokens = self._get_alpha_tokens()
            futures_tokens = self._get_futures_tokens()

            if not alpha_tokens or not futures_tokens:
                logger.warning("⚠️ 获取代币列表失败，保留旧缓存")
                return False

            # 计算交集
            intersection = alpha_tokens & futures_tokens

            if not intersection:
                logger.warning("⚠️ 未找到交集代币，保留旧缓存")
                return False

            # 更新缓存
            old_count = len(self._intersection_set)
            self._intersection_set = intersection
            self._last_update_time = time.time()

            # 保存到文件
            self._save_to_cache_file()

            logger.info(f"✅ 缓存刷新成功: {len(intersection)} 个交集代币 (旧: {old_count})")
            logger.info(f"   Alpha: {len(alpha_tokens)}, 合约: {len(futures_tokens)}")

            return True

    def is_in_intersection(self, symbol):
        """
        检查币种是否在币安Alpha与合约交集中

        Args:
            symbol: 币种符号（如 'BTC', 'ETH'，不区分大小写）

        Returns:
            bool: 在交集中返回 True，否则返回 False
        """
        if not symbol:
            return False

        # 统一转大写
        symbol_upper = symbol.upper().strip()

        # 去除常见后缀（如 /USDT, USDT）
        for suffix in ['/USDT', 'USDT', '/USD', 'USD']:
            if symbol_upper.endswith(suffix):
                symbol_upper = symbol_upper[:-len(suffix)]
                break

        return symbol_upper in self._intersection_set

    def get_intersection_list(self):
        """
        获取交集列表（排序后）

        Returns:
            list: 交集代币列表
        """
        return sorted(self._intersection_set)

    def get_cache_info(self):
        """
        获取缓存信息

        Returns:
            dict: 包含缓存统计信息的字典
        """
        return {
            'count': len(self._intersection_set),
            'last_update': datetime.fromtimestamp(self._last_update_time, BEIJING_TZ).isoformat() if self._last_update_time else None,
            'is_expired': self._is_cache_expired(),
            'refresh_interval': self.refresh_interval
        }

    def start_auto_refresh(self):
        """
        启动自动刷新后台线程
        """
        if self._refresh_thread and self._refresh_thread.is_alive():
            logger.warning("自动刷新线程已在运行")
            return

        self._stop_flag.clear()
        self._refresh_thread = threading.Thread(
            target=self._auto_refresh_loop,
            daemon=True,
            name="BinanceAlphaCacheRefresh"
        )
        self._refresh_thread.start()
        logger.info(f"✅ 启动币安Alpha缓存自动刷新线程（间隔: {self.refresh_interval / 60:.0f} 分钟）")

    def stop_auto_refresh(self):
        """
        停止自动刷新后台线程
        """
        if not self._refresh_thread or not self._refresh_thread.is_alive():
            return

        logger.info("停止币安Alpha缓存自动刷新线程...")
        self._stop_flag.set()

        # 等待线程结束（最多5秒）
        self._refresh_thread.join(timeout=5)

    def _auto_refresh_loop(self):
        """
        自动刷新循环（后台线程）
        """
        while not self._stop_flag.is_set():
            # 等待到下次刷新时间
            time_to_wait = self.refresh_interval
            if self._last_update_time:
                elapsed = time.time() - self._last_update_time
                time_to_wait = max(0, self.refresh_interval - elapsed)

            # 分段等待，方便快速响应停止信号
            wait_interval = 60  # 每分钟检查一次停止标志
            while time_to_wait > 0 and not self._stop_flag.is_set():
                sleep_time = min(wait_interval, time_to_wait)
                time.sleep(sleep_time)
                time_to_wait -= sleep_time

            # 检查是否需要停止
            if self._stop_flag.is_set():
                break

            # 执行刷新
            try:
                self.refresh_now()
            except Exception as e:
                logger.error(f"自动刷新币安Alpha缓存失败: {e}")

        logger.info("币安Alpha缓存自动刷新线程已停止")


# 全局单例
_cache_instance = None


def get_binance_alpha_cache():
    """
    获取全局币安Alpha缓存实例（单例模式）

    Returns:
        BinanceAlphaCache: 缓存实例
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = BinanceAlphaCache()
    return _cache_instance


def is_binance_alpha_symbol(symbol):
    """
    便捷函数: 检查币种是否在币安Alpha与合约交集中

    Args:
        symbol: 币种符号

    Returns:
        bool: 在交集中返回 True，否则返回 False
    """
    cache = get_binance_alpha_cache()
    return cache.is_in_intersection(symbol)


if __name__ == "__main__":
    # 测试代码
    print("测试币安Alpha缓存模块")
    print("=" * 60)

    cache = get_binance_alpha_cache()

    # 显示缓存信息
    info = cache.get_cache_info()
    print(f"缓存信息: {json.dumps(info, indent=2, ensure_ascii=False)}")
    print()

    # 测试查询
    test_symbols = ['BTC', 'ETH', 'SOL', 'DOGE', 'XYZ123']
    print("测试币种查询:")
    for symbol in test_symbols:
        is_alpha = cache.is_in_intersection(symbol)
        status = "✅" if is_alpha else "❌"
        print(f"  {status} {symbol}: {'在交集中' if is_alpha else '不在交集中'}")
    print()

    # 显示交集列表（前10个）
    intersection = cache.get_intersection_list()
    print(f"交集代币列表（共 {len(intersection)} 个）:")
    print(f"  {', '.join(intersection[:10])}")
    if len(intersection) > 10:
        print(f"  ... 还有 {len(intersection) - 10} 个")

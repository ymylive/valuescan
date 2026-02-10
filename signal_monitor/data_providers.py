"""
统一数据提供者模块
整合所有免费加密货币数据API
"""

import time
import requests
from functools import wraps
from logger import logger

# ==================== API配置 ====================
ETHERSCAN_API_KEY = "HDEJ9NFX5BN63E9CPAZ16QJJJDE5X91W75"

# ==================== 频率限制装饰器 ====================

def rate_limit(calls_per_minute):
    """频率限制装饰器"""
    min_interval = 60.0 / calls_per_minute
    last_called = [0.0]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_called[0] = time.time()
            return ret
        return wrapper
    return decorator


# ==================== 重试机制 ====================

def get_session_with_retry():
    """创建带重试机制的session"""
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


# ==================== 代理配置 ====================

def get_proxies():
    """获取代理配置"""
    proxies = {}
    try:
        from config import SOCKS5_PROXY
        if SOCKS5_PROXY:
            proxies = {'http': SOCKS5_PROXY, 'https': SOCKS5_PROXY}
    except:
        pass
    return proxies


# ==================== Binance API ====================
# 免费额度：1200次/分钟
# 无需API Key
# 需要代理（部分地区）

class BinanceProvider:
    """Binance 现货和合约数据提供者"""

    BASE_URL = "https://api.binance.com"
    FUTURES_URL = "https://fapi.binance.com"

    def __init__(self):
        self.session = get_session_with_retry()
        self.proxies = get_proxies()

    @rate_limit(calls_per_minute=1000)  # 保守限制
    def get_ticker(self, symbol):
        """获取24h行情"""
        try:
            url = f"{self.BASE_URL}/api/v3/ticker/24hr"
            response = self.session.get(url, params={'symbol': symbol},
                                       proxies=self.proxies, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.warning(f"Binance ticker获取失败: {e}")
        return None

    @rate_limit(calls_per_minute=1000)
    def get_klines(self, symbol, interval='15m', limit=200):
        """获取K线数据"""
        try:
            url = f"{self.BASE_URL}/api/v3/klines"
            response = self.session.get(url, params={
                'symbol': symbol, 'interval': interval, 'limit': limit
            }, proxies=self.proxies, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.warning(f"Binance K线获取失败: {e}")
        return None

    @rate_limit(calls_per_minute=1000)
    def get_orderbook(self, symbol, limit=500):
        """获取订单簿深度"""
        try:
            url = f"{self.BASE_URL}/api/v3/depth"
            response = self.session.get(url, params={
                'symbol': symbol, 'limit': limit
            }, proxies=self.proxies, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.warning(f"Binance 订单簿获取失败: {e}")
        return None

    @rate_limit(calls_per_minute=1000)
    def get_funding_rate(self, symbol):
        """获取资金费率（合约）"""
        try:
            url = f"{self.FUTURES_URL}/fapi/v1/fundingRate"
            response = self.session.get(url, params={'symbol': symbol, 'limit': 1},
                                       proxies=self.proxies, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data[0] if data else None
        except Exception as e:
            logger.warning(f"Binance 资金费率获取失败: {e}")
        return None

    @rate_limit(calls_per_minute=1000)
    def get_open_interest(self, symbol):
        """获取持仓量（合约）"""
        try:
            url = f"{self.FUTURES_URL}/fapi/v1/openInterest"
            response = self.session.get(url, params={'symbol': symbol},
                                       proxies=self.proxies, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.warning(f"Binance 持仓量获取失败: {e}")
        return None


# ==================== CoinGecko API ====================
# 免费额度：10-50次/分钟
# 无需API Key
# 无需代理

class CoinGeckoProvider:
    """CoinGecko 市值和基本信息提供者"""

    BASE_URL = "https://api.coingecko.com/api/v3"

    def __init__(self):
        self.session = get_session_with_retry()

    @rate_limit(calls_per_minute=45)  # 保守限制
    def get_coin_data(self, coin_id):
        """获取币种完整信息"""
        try:
            url = f"{self.BASE_URL}/coins/{coin_id}"
            response = self.session.get(url, params={
                'localization': 'false',
                'tickers': 'false',
                'market_data': 'true',
                'community_data': 'false',
                'developer_data': 'false'
            }, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.warning(f"CoinGecko 币种数据获取失败: {e}")
        return None

    @rate_limit(calls_per_minute=45)
    def get_markets(self, vs_currency='usd', per_page=100, page=1):
        """获取市场数据列表"""
        try:
            url = f"{self.BASE_URL}/coins/markets"
            response = self.session.get(url, params={
                'vs_currency': vs_currency,
                'per_page': per_page,
                'page': page,
                'order': 'market_cap_desc'
            }, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.warning(f"CoinGecko 市场数据获取失败: {e}")
        return None

    @rate_limit(calls_per_minute=45)
    def get_trending(self):
        """获取热门币种"""
        try:
            url = f"{self.BASE_URL}/search/trending"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.warning(f"CoinGecko 热门币种获取失败: {e}")
        return None


# ==================== DeFiLlama API ====================
# 免费额度：无限制
# 无需API Key
# 无需代理

class DeFiLlamaProvider:
    """DeFiLlama DeFi数据提供者"""

    BASE_URL = "https://api.llama.fi"

    def __init__(self):
        self.session = get_session_with_retry()

    def get_protocol(self, protocol_name):
        """获取协议TVL数据"""
        try:
            url = f"{self.BASE_URL}/protocol/{protocol_name}"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.warning(f"DeFiLlama 协议数据获取失败: {e}")
        return None

    def get_all_protocols(self):
        """获取所有协议列表"""
        try:
            url = f"{self.BASE_URL}/protocols"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.warning(f"DeFiLlama 协议列表获取失败: {e}")
        return None

    def get_chains(self):
        """获取所有链的TVL数据"""
        try:
            url = f"{self.BASE_URL}/chains"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.warning(f"DeFiLlama 链数据获取失败: {e}")
        return None


# ==================== Etherscan API ====================
# 免费额度：5次/秒（100,000次/天）
# 需要API Key

class EtherscanProvider:
    """Etherscan 以太坊链上数据提供者"""

    BASE_URL = "https://api.etherscan.io/api"

    def __init__(self):
        self.session = get_session_with_retry()
        self.api_key = ETHERSCAN_API_KEY

    @rate_limit(calls_per_minute=250)  # 保守限制：5次/秒 = 300次/分钟
    def get_gas_price(self):
        """获取Gas价格"""
        try:
            response = self.session.get(self.BASE_URL, params={
                'module': 'gastracker',
                'action': 'gasoracle',
                'apikey': self.api_key
            }, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == '1':
                    return data.get('result')
        except Exception as e:
            logger.warning(f"Etherscan Gas价格获取失败: {e}")
        return None


# ==================== 统一数据管理器 ====================

class UnifiedDataProvider:
    """统一数据提供者 - 整合所有数据源，支持API容错"""

    def __init__(self):
        self.binance = BinanceProvider()
        self.coingecko = CoinGeckoProvider()
        self.defillama = DeFiLlamaProvider()
        self.etherscan = EtherscanProvider()
        logger.info("✅ 统一数据提供者初始化完成")

    def _get_price_with_fallback(self, symbol, coin_id=None):
        """
        获取价格数据，支持API容错
        优先级：Binance -> CoinGecko
        """
        # 尝试Binance
        ticker = self.binance.get_ticker(symbol)
        if ticker:
            return {
                'price': float(ticker.get('lastPrice', 0)),
                'volume_24h': float(ticker.get('quoteVolume', 0)),
                'price_change_24h': float(ticker.get('priceChangePercent', 0)),
                'source': 'binance'
            }

        # Binance失败，尝试CoinGecko
        if coin_id:
            logger.warning(f"Binance API失败，尝试CoinGecko: {coin_id}")
            cg_data = self.coingecko.get_coin_data(coin_id)
            if cg_data and 'market_data' in cg_data:
                md = cg_data['market_data']
                return {
                    'price': md.get('current_price', {}).get('usd', 0),
                    'volume_24h': md.get('total_volume', {}).get('usd', 0),
                    'price_change_24h': md.get('price_change_percentage_24h', 0),
                    'source': 'coingecko'
                }

        return None

    def get_complete_market_data(self, symbol, coin_id=None):
        """
        获取币种完整市场数据（支持API容错）

        Args:
            symbol: 交易对符号，如 'BTCUSDT'
            coin_id: CoinGecko币种ID，如 'bitcoin'

        Returns:
            dict: 完整市场数据
        """
        result = {
            'symbol': symbol,
            'timestamp': time.time(),
            'binance': {},
            'coingecko': {},
            'etherscan': {},
            'success': False
        }

        # 1. 获取价格数据（带容错）
        price_data = self._get_price_with_fallback(symbol, coin_id)
        if price_data:
            source = price_data.pop('source')
            result[source].update(price_data)
            result['success'] = True

        # 2. Binance 合约数据（可选）
        funding = self.binance.get_funding_rate(symbol)
        if funding:
            result['binance']['funding_rate'] = float(funding.get('fundingRate', 0))

        oi = self.binance.get_open_interest(symbol)
        if oi:
            result['binance']['open_interest'] = float(oi.get('openInterest', 0))

        # 3. CoinGecko 市值数据（如果价格数据来自Binance）
        if coin_id and not result['coingecko'].get('price'):
            cg_data = self.coingecko.get_coin_data(coin_id)
            if cg_data and 'market_data' in cg_data:
                md = cg_data['market_data']
                result['coingecko']['market_cap'] = md.get('market_cap', {}).get('usd', 0)
                result['coingecko']['market_cap_rank'] = cg_data.get('market_cap_rank')
                result['coingecko']['total_volume'] = md.get('total_volume', {}).get('usd', 0)
                result['coingecko']['circulating_supply'] = md.get('circulating_supply', 0)

        # 4. Etherscan Gas数据（可选）
        gas_data = self.etherscan.get_gas_price()
        if gas_data:
            result['etherscan']['gas_price'] = gas_data

        return result


# ==================== 使用示例 ====================

if __name__ == '__main__':
    # 测试统一数据提供者
    provider = UnifiedDataProvider()

    # 获取BTC完整数据
    btc_data = provider.get_complete_market_data('BTCUSDT', 'bitcoin')
    print(f"BTC价格: ${btc_data['binance'].get('price', 0):,.2f}")
    print(f"BTC市值: ${btc_data['coingecko'].get('market_cap', 0):,.0f}")
    print(f"资金费率: {btc_data['binance'].get('funding_rate', 0):.4%}")

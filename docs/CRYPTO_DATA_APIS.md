# 最佳免费加密货币数据接口

## 1. 实时行情数据

### Binance API (推荐)
- **URL**: https://api.binance.com
- **优点**:
  - 完全免费，无需API Key
  - 数据最准确，延迟最低
  - 支持现货、合约、期权
- **限制**:
  - 需要代理访问（部分地区）
  - 请求频率限制：1200次/分钟
- **接口**:
  - K线: `/api/v3/klines`
  - 订单簿: `/api/v3/depth`
  - 24h行情: `/api/v3/ticker/24hr`

### Coinbase API
- **URL**: https://api.coinbase.com
- **优点**: 无需代理，全球可访问
- **限制**: 币种较少，主要是主流币

### Kraken API
- **URL**: https://api.kraken.com
- **优点**: 数据质量高，历史数据完整
- **限制**: 请求频率较低

## 2. 市值和基本信息

### CoinGecko API (推荐)
- **URL**: https://api.coingecko.com/api/v3
- **优点**:
  - 完全免费
  - 覆盖10000+币种
  - 市值、流通量、社交数据
- **限制**:
  - 免费版：10-50次/分钟
  - 数据延迟5-10分钟
- **接口**:
  - 币种信息: `/coins/{id}`
  - 市场数据: `/coins/markets`
  - 历史价格: `/coins/{id}/market_chart`
- **示例**:
```python
import requests
response = requests.get('https://api.coingecko.com/api/v3/coins/bitcoin')
data = response.json()
print(f"BTC价格: ${data['market_data']['current_price']['usd']}")
print(f"市值: ${data['market_data']['market_cap']['usd']}")
```

### CoinMarketCap API
- **URL**: https://pro-api.coinmarketcap.com
- **优点**: 数据权威，行业标准
- **限制**:
  - 免费版：333次/天
  - 需要注册API Key
- **接口**:
  - 最新行情: `/v1/cryptocurrency/listings/latest`
  - 币种信息: `/v2/cryptocurrency/info`

## 3. 链上数据和DeFi

### Etherscan API
- **URL**: https://api.etherscan.io/api
- **优点**:
  - 以太坊链上数据最全
  - Gas价格、交易记录、合约调用
- **限制**:
  - 免费版：5次/秒
  - 需要API Key
- **接口**:
  - Gas价格: `?module=gastracker&action=gasoracle`
  - ERC20余额: `?module=account&action=tokenbalance`

### DeFiLlama API
- **URL**: https://api.llama.fi
- **优点**:
  - 完全免费，无需API Key
  - TVL数据最全面
  - 覆盖所有主流DeFi协议
- **限制**: 无明显限制
- **接口**:
  - 协议TVL: `/protocol/{protocol}`
  - 所有协议: `/protocols`
  - 链TVL: `/chains`

## 4. 衍生品和合约数据

### Binance Futures API (推荐)
- **URL**: https://fapi.binance.com
- **优点**:
  - 完全免费
  - 资金费率、持仓量、多空比
  - 大户持仓、Taker买卖量
- **限制**: 需要代理访问（部分地区）
- **接口**:
  - 资金费率: `/fapi/v1/fundingRate`
  - 持仓量: `/futures/data/openInterestHist`
  - 多空比: `/futures/data/globalLongShortAccountRatio`
  - Taker买卖: `/futures/data/takerlongshortRatio`

### Coinglass API
- **URL**: https://open-api.coinglass.com
- **优点**:
  - 聚合多交易所数据
  - 清算数据、爆仓地图
- **限制**:
  - 免费版有限制
  - 需要API Key

## 5. 新闻和社交数据

### CryptoPanic API
- **URL**: https://cryptopanic.com/developers/api/
- **优点**:
  - 聚合加密货币新闻
  - 情绪分析标签
  - 免费版可用
- **限制**:
  - 免费版：有请求限制
  - 需要API Key
- **接口**:
  - 最新新闻: `/api/v1/posts/`
  - 按币种过滤: `/api/v1/posts/?currencies=BTC`

### LunarCrush API
- **URL**: https://lunarcrush.com/developers/api
- **优点**:
  - 社交媒体情绪分析
  - Twitter、Reddit数据
- **限制**:
  - 免费版：50次/天
  - 需要API Key

## 6. 历史数据和回测

### CryptoCompare API
- **URL**: https://min-api.cryptocompare.com
- **优点**:
  - 历史K线数据完整
  - 支持多交易所聚合
  - 免费版可用
- **限制**:
  - 免费版：100,000次/月
  - 需要API Key
- **接口**:
  - 历史K线: `/data/v2/histoday`
  - 实时价格: `/data/price`
- **示例**:
```python
import requests
url = 'https://min-api.cryptocompare.com/data/v2/histoday'
params = {'fsym': 'BTC', 'tsym': 'USD', 'limit': 100}
response = requests.get(url, params=params)
data = response.json()['Data']['Data']
```

### CCXT Library (推荐)
- **URL**: https://github.com/ccxt/ccxt
- **优点**:
  - 统一接口访问100+交易所
  - Python/JavaScript/PHP支持
  - 开源免费
- **限制**: 需要遵守各交易所限制
- **示例**:
```python
import ccxt
exchange = ccxt.binance()
ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=100)
ticker = exchange.fetch_ticker('BTC/USDT')
```

## 7. 最佳实践

### 数据源组合推荐

**方案1：完全免费方案**
- 实时行情：Binance API (需代理)
- 市值数据：CoinGecko API
- 链上数据：DeFiLlama API
- 优点：完全免费，无需API Key
- 缺点：需要代理，有频率限制

**方案2：混合方案（推荐）**
- 实时行情：CCXT + Binance
- 市值数据：CoinGecko API
- 衍生品数据：Binance Futures API
- 历史数据：CryptoCompare API
- 优点：数据全面，稳定性高
- 缺点：部分需要API Key

### 频率限制处理

```python
import time
from functools import wraps

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

@rate_limit(calls_per_minute=50)
def get_coingecko_data(coin_id):
    # CoinGecko限制50次/分钟
    pass
```

### 错误处理和重试

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def get_session_with_retry():
    """创建带重试机制的session"""
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

# 使用示例
session = get_session_with_retry()
response = session.get('https://api.coingecko.com/api/v3/ping')
```

### 代理配置

```python
# SOCKS5代理配置（推荐用于Binance）
proxies = {
    'http': 'socks5://127.0.0.1:7890',
    'https': 'socks5://127.0.0.1:7890'
}

# HTTP代理配置
proxies = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890'
}

# 使用代理
response = requests.get('https://api.binance.com/api/v3/ping', proxies=proxies)

# CCXT使用代理
import ccxt
exchange = ccxt.binance({
    'proxies': proxies,
    'enableRateLimit': True
})
```

### 数据缓存

```python
import time
from functools import lru_cache

# 简单内存缓存
cache = {}
CACHE_TTL = 60  # 60秒

def get_cached_data(key, fetch_func):
    """带TTL的缓存"""
    now = time.time()
    if key in cache:
        data, timestamp = cache[key]
        if now - timestamp < CACHE_TTL:
            return data

    # 缓存过期或不存在，重新获取
    data = fetch_func()
    cache[key] = (data, now)
    return data

# 使用装饰器缓存
@lru_cache(maxsize=128)
def get_coin_info(coin_id):
    # 注意：lru_cache不支持TTL，适合不常变化的数据
    pass
```

## 8. 完整示例

### 示例1：获取BTC完整数据

```python
import ccxt
import requests

def get_btc_complete_data():
    """获取BTC完整市场数据"""

    # 1. 实时价格和K线 (CCXT + Binance)
    exchange = ccxt.binance({'enableRateLimit': True})
    ticker = exchange.fetch_ticker('BTC/USDT')
    ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=100)

    # 2. 市值和基本信息 (CoinGecko)
    cg_url = 'https://api.coingecko.com/api/v3/coins/bitcoin'
    cg_data = requests.get(cg_url).json()

    # 3. 资金费率 (Binance Futures)
    funding_url = 'https://fapi.binance.com/fapi/v1/fundingRate'
    funding = requests.get(funding_url, params={'symbol': 'BTCUSDT', 'limit': 1}).json()

    return {
        'price': ticker['last'],
        'volume_24h': ticker['quoteVolume'],
        'market_cap': cg_data['market_data']['market_cap']['usd'],
        'funding_rate': funding[0]['fundingRate'] if funding else None,
        'ohlcv': ohlcv
    }
```

### 示例2：多币种批量获取

```python
def get_multiple_coins_data(symbols):
    """批量获取多个币种数据"""
    exchange = ccxt.binance({'enableRateLimit': True})
    results = {}

    for symbol in symbols:
        try:
            ticker = exchange.fetch_ticker(f'{symbol}/USDT')
            results[symbol] = {
                'price': ticker['last'],
                'change_24h': ticker['percentage'],
                'volume_24h': ticker['quoteVolume']
            }
            time.sleep(0.1)  # 避免频率限制
        except Exception as e:
            print(f"获取 {symbol} 失败: {e}")

    return results

# 使用示例
coins = ['BTC', 'ETH', 'SOL', 'BNB']
data = get_multiple_coins_data(coins)
```

## 9. 注意事项

### API限制对比

| API | 免费额度 | 需要Key | 代理 | 推荐度 |
|-----|---------|---------|------|--------|
| Binance API | 1200次/分钟 | ❌ | ✅ | ⭐⭐⭐⭐⭐ |
| CoinGecko | 10-50次/分钟 | ❌ | ❌ | ⭐⭐⭐⭐⭐ |
| CCXT | 取决于交易所 | ❌ | 部分 | ⭐⭐⭐⭐⭐ |
| CoinMarketCap | 333次/天 | ✅ | ❌ | ⭐⭐⭐ |
| CryptoCompare | 100K次/月 | ✅ | ❌ | ⭐⭐⭐⭐ |
| DeFiLlama | 无限制 | ❌ | ❌ | ⭐⭐⭐⭐ |

### 常见问题

**Q: 为什么Binance API返回451错误？**
A: 部分地区被限制访问，需要配置SOCKS5代理（如Clash）

**Q: CoinGecko API太慢怎么办？**
A: 使用缓存机制，避免频繁请求相同数据

**Q: 如何选择合适的数据源？**
A:
- 实时交易：优先Binance API + CCXT
- 市值排名：优先CoinGecko
- 历史回测：优先CryptoCompare
- DeFi数据：优先DeFiLlama

**Q: 如何避免被限流？**
A:
1. 使用频率限制装饰器
2. 实现请求缓存
3. 使用CCXT的enableRateLimit选项
4. 分散请求到多个数据源

## 10. 总结

### 推荐组合方案

**生产环境推荐配置：**
```python
# 主数据源
PRIMARY_SOURCES = {
    'price': 'CCXT + Binance',           # 实时价格
    'market_cap': 'CoinGecko',           # 市值数据
    'futures': 'Binance Futures API',    # 合约数据
    'defi': 'DeFiLlama',                 # DeFi数据
}

# 备用数据源
FALLBACK_SOURCES = {
    'price': 'Coinbase API',
    'market_cap': 'CoinMarketCap',
}
```

### 关键要点

1. **优先使用免费API**：Binance、CoinGecko、DeFiLlama完全免费且数据质量高
2. **实现容错机制**：主数据源失败时自动切换到备用源
3. **合理使用缓存**：减少API请求，提高响应速度
4. **遵守频率限制**：避免被封禁，使用rate limiting
5. **代理配置**：部分API需要代理访问（如Binance）

### 数据更新频率建议

| 数据类型 | 更新频率 | 推荐API |
|---------|---------|---------|
| 实时价格 | 1-5秒 | Binance API |
| K线数据 | 按周期 | CCXT |
| 市值排名 | 5-10分钟 | CoinGecko |
| 资金费率 | 8小时 | Binance Futures |
| 持仓量 | 5分钟 | Binance Futures |
| DeFi TVL | 1小时 | DeFiLlama |
| 新闻数据 | 10-30分钟 | CryptoPanic |

---

**文档版本**: v1.0
**最后更新**: 2025-12-25
**维护者**: ValueScan Team

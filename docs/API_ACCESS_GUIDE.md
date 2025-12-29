# API 获取和使用指南

本文档详细说明如何获取各个加密货币数据API的访问权限和使用额度。

## 📊 API 额度总览

| API | 免费额度 | 需要注册 | 需要API Key | 需要代理 | 获取难度 |
|-----|---------|---------|------------|---------|---------|
| **Binance API** | 1200次/分钟 | ❌ | ❌ | ✅ (部分地区) | ⭐ 极易 |
| **CoinGecko API** | 10-50次/分钟 | ❌ | ❌ | ❌ | ⭐ 极易 |
| **DeFiLlama API** | 无限制 | ❌ | ❌ | ❌ | ⭐ 极易 |
| **CoinMarketCap API** | 333次/天 | ✅ | ✅ | ❌ | ⭐⭐ 简单 |
| **CryptoCompare API** | 100,000次/月 | ✅ | ✅ | ❌ | ⭐⭐ 简单 |
| **Etherscan API** | 5次/秒 | ✅ | ✅ | ❌ | ⭐⭐ 简单 |

---

## 1. Binance API（推荐）

### 📌 基本信息
- **官网**: https://www.binance.com
- **文档**: https://binance-docs.github.io/apidocs/
- **免费额度**: 1200次/分钟（现货）、2400次/分钟（合约）
- **需要API Key**: ❌ 不需要（公开数据）
- **需要代理**: ✅ 部分地区需要

### 🔑 如何获取

**无需注册，直接使用！**

Binance的公开API（行情数据）无需任何注册或API Key，可以直接访问。

### 📝 使用示例

```python
import requests

# 获取BTC价格
url = "https://api.binance.com/api/v3/ticker/24hr"
response = requests.get(url, params={'symbol': 'BTCUSDT'})
data = response.json()
print(f"BTC价格: ${data['lastPrice']}")
```

### ⚠️ 注意事项

1. **地区限制**: 部分地区（如中国大陆）需要配置代理访问
2. **频率限制**:
   - 现货API: 1200次/分钟
   - 合约API: 2400次/分钟
   - 超过限制会返回429错误
3. **代理配置**: 使用SOCKS5代理（如Clash）

```python
proxies = {
    'http': 'socks5://127.0.0.1:7890',
    'https': 'socks5://127.0.0.1:7890'
}
response = requests.get(url, proxies=proxies)
```

### 📊 可用数据

- ✅ 实时价格和24h行情
- ✅ K线数据（1m, 5m, 15m, 1h, 4h, 1d等）
- ✅ 订单簿深度
- ✅ 资金费率（合约）
- ✅ 持仓量（合约）
- ✅ 多空比（合约）
- ✅ Taker买卖量（合约）

---

## 2. CoinGecko API（推荐）

### 📌 基本信息
- **官网**: https://www.coingecko.com
- **文档**: https://www.coingecko.com/en/api/documentation
- **免费额度**: 10-50次/分钟
- **需要API Key**: ❌ 不需要（免费版）
- **需要代理**: ❌ 不需要

### 🔑 如何获取

**无需注册，直接使用！**

CoinGecko的免费API无需注册，可以直接访问。

### 📝 使用示例

```python
import requests

# 获取BTC市值数据
url = "https://api.coingecko.com/api/v3/coins/bitcoin"
response = requests.get(url)
data = response.json()
print(f"BTC市值: ${data['market_data']['market_cap']['usd']:,.0f}")
```

### ⚠️ 注意事项

1. **频率限制**:
   - 免费版: 10-50次/分钟（官方未明确，实测约50次/分钟）
   - 超过限制会返回429错误
2. **数据延迟**: 免费版数据有5-10分钟延迟
3. **付费版本**:
   - Demo: $129/月，500次/分钟
   - Analyst: $499/月，1000次/分钟

### 📊 可用数据

- ✅ 市值和市值排名
- ✅ 流通量和总供应量
- ✅ 24h交易量
- ✅ 历史价格数据
- ✅ 社交媒体数据
- ✅ 热门币种排行

---

## 3. DeFiLlama API（推荐）

### 📌 基本信息
- **官网**: https://defillama.com
- **文档**: https://defillama.com/docs/api
- **免费额度**: 无限制
- **需要API Key**: ❌ 不需要
- **需要代理**: ❌ 不需要

### 🔑 如何获取

**无需注册，直接使用！**

DeFiLlama完全免费，无需任何注册。

### 📝 使用示例

```python
import requests

# 获取Uniswap TVL
url = "https://api.llama.fi/protocol/uniswap"
response = requests.get(url)
data = response.json()
print(f"Uniswap TVL: ${data['tvl']:,.0f}")
```

### ⚠️ 注意事项

1. **无频率限制**: 完全免费，无明显频率限制
2. **数据更新**: TVL数据每小时更新一次
3. **覆盖范围**: 覆盖所有主流DeFi协议和链

### 📊 可用数据

- ✅ 协议TVL（总锁仓量）
- ✅ 所有协议列表
- ✅ 各链TVL数据
- ✅ 历史TVL数据

---

## 4. CoinMarketCap API

### 📌 基本信息
- **官网**: https://coinmarketcap.com
- **文档**: https://coinmarketcap.com/api/documentation/v1/
- **免费额度**: 333次/天（10,000次/月）
- **需要API Key**: ✅ 需要
- **需要代理**: ❌ 不需要

### 🔑 如何获取

1. 访问 https://pro.coinmarketcap.com/signup/
2. 注册账号（邮箱验证）
3. 登录后访问 https://pro.coinmarketcap.com/account
4. 点击 "Copy API Key" 获取API Key

### 📝 使用示例

```python
import requests

headers = {
    'X-CMC_PRO_API_KEY': 'your-api-key-here'
}

url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
response = requests.get(url, headers=headers)
data = response.json()
```

### ⚠️ 注意事项

1. **免费版限制**:
   - 333次/天（约10,000次/月）
   - 每分钟30次
2. **付费版本**:
   - Hobbyist: $29/月，10,000次/月
   - Startup: $79/月，30,000次/月
   - Standard: $299/月，100,000次/月

---

## 5. CryptoCompare API

### 📌 基本信息
- **官网**: https://www.cryptocompare.com
- **文档**: https://min-api.cryptocompare.com/documentation
- **免费额度**: 100,000次/月
- **需要API Key**: ✅ 需要
- **需要代理**: ❌ 不需要

### 🔑 如何获取

1. 访问 https://www.cryptocompare.com/cryptopian/api-keys
2. 注册账号
3. 创建API Key
4. 复制API Key使用

### 📝 使用示例

```python
import requests

url = "https://min-api.cryptocompare.com/data/v2/histoday"
params = {
    'fsym': 'BTC',
    'tsym': 'USD',
    'limit': 100,
    'api_key': 'your-api-key-here'
}
response = requests.get(url, params=params)
data = response.json()
```

### ⚠️ 注意事项

1. **免费版限制**:
   - 100,000次/月
   - 每秒50次
2. **历史数据**: 免费版可访问完整历史数据
3. **付费版本**:
   - Professional: $99/月，500,000次/月

---

## 6. Etherscan API

### 📌 基本信息
- **官网**: https://etherscan.io
- **文档**: https://docs.etherscan.io/
- **免费额度**: 5次/秒（100,000次/天）
- **需要API Key**: ✅ 需要
- **需要代理**: ❌ 不需要

### 🔑 如何获取

1. 访问 https://etherscan.io/register
2. 注册账号
3. 访问 https://etherscan.io/myapikey
4. 创建API Key

### 📝 使用示例

```python
import requests

url = "https://api.etherscan.io/api"
params = {
    'module': 'gastracker',
    'action': 'gasoracle',
    'apikey': 'your-api-key-here'
}
response = requests.get(url, params=params)
data = response.json()
```

### ⚠️ 注意事项

1. **免费版限制**: 5次/秒，100,000次/天
2. **链支持**: 以太坊主网、测试网
3. **其他链**: BSCScan、PolygonScan等有独立API

---

## 📋 推荐使用方案

### 方案1：完全免费（推荐）

**适合**: 个人项目、小型应用

| 数据类型 | API | 额度 |
|---------|-----|------|
| 实时价格 | Binance API | 1200次/分钟 |
| 市值数据 | CoinGecko API | 50次/分钟 |
| DeFi数据 | DeFiLlama API | 无限制 |

**优点**: 完全免费，无需注册
**缺点**: 需要代理访问Binance（部分地区）

### 方案2：混合方案

**适合**: 中型应用、需要更多数据

| 数据类型 | API | 额度 |
|---------|-----|------|
| 实时价格 | Binance API | 1200次/分钟 |
| 市值数据 | CoinGecko API | 50次/分钟 |
| 历史数据 | CryptoCompare API | 100,000次/月 |
| 链上数据 | Etherscan API | 5次/秒 |

**优点**: 数据更全面，稳定性高
**缺点**: 需要注册多个API Key

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install requests ccxt pycoingecko
```

### 2. 使用统一数据提供者

```python
from signal_monitor.data_providers import UnifiedDataProvider

# 初始化
provider = UnifiedDataProvider()

# 获取BTC完整数据
data = provider.get_complete_market_data('BTCUSDT', 'bitcoin')

print(f"价格: ${data['binance']['price']:,.2f}")
print(f"市值: ${data['coingecko']['market_cap']:,.0f}")
print(f"资金费率: {data['binance']['funding_rate']:.4%}")
```

---

## 📞 技术支持

如有问题，请参考：
- Binance API文档: https://binance-docs.github.io/apidocs/
- CoinGecko API文档: https://www.coingecko.com/en/api/documentation
- DeFiLlama API文档: https://defillama.com/docs/api

---

**文档版本**: v1.0
**最后更新**: 2025-12-25
**维护者**: ValueScan Team


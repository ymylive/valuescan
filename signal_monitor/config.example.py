"""
Signal Monitor API 监听工具配置文件示例
请复制此文件为 config.py 并填入您的配置
"""

# ==================== Telegram Bot 配置 ====================
# Telegram Bot Token (从 @BotFather 获取)
# 获取方式: 在 Telegram 中找到 @BotFather，发送 /newbot 创建机器人
TELEGRAM_BOT_TOKEN = ""

# Telegram 目标用户 ID
# 频道 ID 格式：-100 开头的数字
# 获取方式: 在 Telegram 中找到 @userinfobot，发送任意消息获取您的 ID
TELEGRAM_CHAT_ID = ""

# ==================== 消息发送开关 ====================
# 是否启用 Telegram 通知功能（总开关）
# False: 完全跳过 Telegram 发送，但不影响数据库存储和 IPC 转发
# True: 尝试发送 Telegram 通知
ENABLE_TELEGRAM = True

# 是否发送 TG 消息（需要 ENABLE_TELEGRAM = True 才有效）
SEND_TG_IN_MODE_1 = True

# ==================== 浏览器配置 ====================
# Chrome 远程调试端口
CHROME_DEBUG_PORT = 9222

# 无头模式（不显示浏览器窗口）
# True: 后台运行，不显示浏览器界面（推荐服务器使用）
# False: 显示浏览器窗口（需要手动登录账号）
HEADLESS_MODE = False

# ==================== API 配置 ====================
# 监听的 API 路径（部分匹配）
API_PATH = "api/account/message/getWarnMessage"
AI_API_PATH = "api/account/message/aiMessagePage"

# ==================== Language ====================
LANGUAGE = "zh"

# ==================== 外部数据 API 密钥 ====================
# CoinMarketCap API Key (用于获取市场数据)
COINMARKETCAP_API_KEY = "28fb263977514cb79b2ba80200c671c0"

# CryptoCompare API Key (用于获取价格和市场数据)
CRYPTOCOMPARE_API_KEY = "fa599edd81742a6f284cc6db8f98574ede3b92dbb608b418c44715a83f1dab9b"

# CoinGecko API Key (用于获取趋势币种和市场数据)
COINGECKO_API_KEY = "CG-6itS45epruuSZZpR9Mpp3Ui8"

# Etherscan API Key (可选，用于链上数据查询)
ETHERSCAN_API_KEY = ""

# FRED API Key (宏观数据)
FRED_API_KEY = ""

# GitHub Token (项目基本面，提升速率)
GITHUB_TOKEN = ""


# CCXT 数据源（可选）
NOFX_CCXT_ENABLED = True
NOFX_CCXT_EXCHANGE = "binance"
NOFX_CCXT_MARKET_TYPE = "spot"
NOFX_CCXT_ORDERBOOK_LIMIT = 20

# FRED 关注指标（逗号分隔）
NOFX_FRED_SERIES = "PAYEMS,CPIAUCSL,UNRATE,FEDFUNDS"

# FRED 发布日历（release_id 列表，可选）
NOFX_FRED_RELEASE_IDS = "10,46,50,53,54,101"

# ERC20 合约地址映射（可选，JSON）
NOFX_ERC20_CONTRACTS = "{\"USDT\":\"0xdAC17F958D2ee523a2206206994597C13D831ec7\",\"USDC\":\"0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48\",\"DAI\":\"0x6B175474E89094C44Da98b954EedeAC495271d0F\",\"LINK\":\"0x514910771AF9Ca656af840dff83E8264EcF986CA\",\"UNI\":\"0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984\",\"AAVE\":\"0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9\",\"LDO\":\"0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32\",\"MKR\":\"0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2\",\"COMP\":\"0xc00e94Cb662C3520282E6f5717214004A7f26888\"}"

# GDELT data (macro/policy/geopolitics)
NOFX_GDELT_ENABLED = True
NOFX_GDELT_QUERY = "(crypto OR bitcoin OR ethereum OR regulation OR policy OR fed OR inflation OR cpi OR payroll OR geopolitics OR war OR sanctions)"
NOFX_GDELT_MAX_RECORDS = 8
NOFX_GDELT_TIMESPAN = "1d"


# ==================== 轮询监控配置 ====================
# 轮询间隔（秒）- 每隔多少秒轮询一次 signal API
POLL_INTERVAL = 10

# 请求超时（秒）- API 请求超时时间
REQUEST_TIMEOUT = 15

# 最大连续失败次数 - 触发冷却前允许的最大连续失败次数
MAX_CONSECUTIVE_FAILURES = 5

# 失败冷却时间（秒）- 连续失败后的冷却等待时间
FAILURE_COOLDOWN = 60

# 自动重新登录 - Token 过期时自动尝试重新登录
AUTO_RELOGIN = False

# 重新登录冷却时间（秒）- 两次自动登录尝试之间的最小间隔
AUTO_RELOGIN_COOLDOWN = 1800

# 启动时信号最大年龄（秒）- 启动时过滤超过此时间的旧信号
STARTUP_SIGNAL_MAX_AGE_SECONDS = 600

# 运行时信号最大年龄（秒）- 运行时过滤超过此时间的信号
SIGNAL_MAX_AGE_SECONDS = 600

# ==================== Scheduled AI Signals ====================
# Interval minutes for scheduled AI signal push
AI_SIGNAL_INTERVAL_MINUTES = 30

# Comma-separated symbols for scheduled AI signal push
AI_SIGNAL_SYMBOLS = ["BTC", "ETH", "BNB", "SOL", "XAUUSD", "XAGUSD"]

# Delay between symbols (seconds)
AI_SIGNAL_SYMBOL_DELAY = 2

# Suppress duplicate scheduled AI signals within this window (seconds)
AI_SIGNAL_DEDUP_SECONDS = 120

# Lookback hours for recent signal signals fed into AI analysis
AI_SIGNAL_LOOKBACK_HOURS = 24

# Max recent signals to include in AI analysis (0 = no limit)
AI_SIGNAL_RECENT_LIMIT = 0


# ==================== Token 刷新器配置 ====================
# Token 刷新间隔（小时）- Token 刷新间隔时间
TOKEN_REFRESH_INTERVAL_HOURS = 0.8

# 安全边际时间（秒）- Token 过期前提前刷新的时间
TOKEN_REFRESH_SAFETY_SECONDS = 300

# 登录方法 - Token 刷新使用的登录方法 (auto/http/cdp/browser)
LOGIN_METHOD = "auto"

# 刷新窗口开始时间（小时，24小时制）- Token 刷新的首选时间段开始
REFRESH_WINDOW_START = 0

# 刷新窗口结束时间（小时，24小时制）- Token 刷新的首选时间段结束
REFRESH_WINDOW_END = 6


# ==================== AI 市场总结增强配置 ====================
# AI API 代理 - AI API 调用使用的代理地址
AI_SUMMARY_PROXY = "http://127.0.0.1:7890"


# ==================== 本地 IPC 转发 ====================
# 是否将捕获到的信号通过本地 IPC 转发给交易模块
ENABLE_IPC_FORWARDING = True

try:
    # 与交易端共享的 IPC 基础配置
    from ipc_config import IPC_HOST, IPC_PORT, IPC_CONNECT_TIMEOUT, IPC_RETRY_DELAY, IPC_MAX_RETRIES
except ImportError:
    IPC_HOST = "127.0.0.1"
    IPC_PORT = 8765
    IPC_CONNECT_TIMEOUT = 1.5
    IPC_RETRY_DELAY = 2.0
    IPC_MAX_RETRIES = 3

# ==================== 网络代理配置 ====================
# SOCKS5 代理（用于访问币安API获取Alpha交集）
# 格式: "socks5://username:password@host:port"
# 留空则不使用代理
SOCKS5_PROXY = ""
# 示例: SOCKS5_PROXY = "socks5://user:pass@proxy.example.com:1080"

# HTTP/HTTPS 代理（备选方案）
# 格式: {"http": "http://proxy:port", "https": "http://proxy:port"}
# 留空则不使用代理
HTTP_PROXY = ""
# 示例: HTTP_PROXY = "http://proxy.example.com:8080"

# ==================== Pro 图表配置（本地生成） ====================
# 是否启用 Pro 图表（本地生成K线+热力图+资金流）
ENABLE_PRO_CHART = True


# ==================== AI 绘制辅助线/主力位 ====================
# True: 使用 AI 输出的主力位/辅助线坐标
# False: 使用本地算法计算主力位/辅助线
ENABLE_AI_KEY_LEVELS = False
ENABLE_AI_OVERLAYS = False
# True: 启用 AI 单币简评（用于 Telegram 异步补全）
ENABLE_AI_SIGNAL_ANALYSIS = True

# ==================== TradingView 图表配置 ====================
# 是否启用 TradingView 图表生成（融合信号时自动生成图表）
ENABLE_TRADINGVIEW_CHART = True

# chart-img.com API Key
# 获取方式: https://www.chart-img.com/
CHART_IMG_API_KEY = ""

# TradingView 布局 ID（需要公开分享的布局）
# 获取方式:
#   1. 在 TradingView 中创建并保存你的图表布局
#   2. 点击右上角 "分享" 按钮，选择 "Make chart public"
#   3. 布局 URL 中的最后一部分就是 Layout ID
#   例如: https://www.tradingview.com/chart/oeTZqtUR/ -> Layout ID = oeTZqtUR
CHART_IMG_LAYOUT_ID = "oeTZqtUR"

# 图表尺寸（像素）
# 根据您的订阅计划选择合适的分辨率：
# 免费/基础计划：最大 800x600
# MEGA 订阅：最大 1920x1600，推荐 1920x1200 或 1600x1000
CHART_IMG_WIDTH = 800
CHART_IMG_HEIGHT = 600

# 图表生成超时时间（秒，建议 60-90 秒）
CHART_IMG_TIMEOUT = 90

# 自动删除生成的图表文件
# True: 发送后自动删除 (默认)
# False: 保留文件 (用于调试)
AUTO_DELETE_CHARTS = True

# 贵金属 K 线数据源优先级（逗号分隔）
# 可选: binance, oanda, twelvedata
NOFX_METALS_KLINE_PROVIDERS = "binance"
# OANDA API Key (可用于 XAU_USD / XAG_USD 蜡烛)
NOFX_OANDA_API_KEY = ""
# OANDA 环境: practice 或 live
NOFX_OANDA_ENV = "practice"
# Twelve Data API Key (支持 XAU/USD, XAG/USD time_series)
NOFX_TWELVEDATA_API_KEY = ""
# 贵金属 K 线缓存秒数
NOFX_METALS_KLINES_TTL = 60

# ==================== 日志配置 ====================
# 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
# DEBUG: 详细的调试信息
# INFO: 一般信息（推荐）
# WARNING: 警告信息
# ERROR: 错误信息
# CRITICAL: 严重错误
LOG_LEVEL = "INFO"

# 是否输出日志到文件
LOG_TO_FILE = True

# 日志文件路径
LOG_FILE = "signal_monitor.log"

# 日志文件最大大小（字节）10MB
LOG_MAX_SIZE = 10 * 1024 * 1024

# 保留的日志文件数量（日志轮转）
LOG_BACKUP_COUNT = 5

# 日志格式
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"

# 日期格式
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

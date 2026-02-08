"""
ValuesCan API 监听工具配置文件示例
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

# Crypto News API Key (可选，用于获取加密货币新闻)
CRYPTO_NEWS_API_KEY = ""


# ==================== 轮询监控配置 ====================
# 轮询间隔（秒）- 每隔多少秒轮询一次 ValueScan API
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

# AI 简评等待超时（秒）
AI_BRIEF_WAIT_TIMEOUT_SECONDS = 90

# 看涨/看跌信号有效期（秒）
BULL_BEAR_SIGNAL_TTL_SECONDS = 86400

# ValuScan 主力位/分析有效期（天）
VALUESCAN_KEY_LEVELS_DAYS = 7
VALUESCAN_AI_ANALYSIS_DAYS = 15

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
LOG_FILE = "valuescan.log"

# 日志文件最大大小（字节）10MB
LOG_MAX_SIZE = 10 * 1024 * 1024

# 保留的日志文件数量（日志轮转）
LOG_BACKUP_COUNT = 5

# 日志格式
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"

# 日期格式
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

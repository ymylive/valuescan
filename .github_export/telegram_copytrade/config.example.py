"""
Telegram 跟单交易配置模板
复制此文件为 config.py 并填入你的实际配置
"""

# ============ Telegram 配置 ============
# Telegram API 凭证（从 https://my.telegram.org 获取）
TELEGRAM_API_ID = 12345678  # 你的 API ID
TELEGRAM_API_HASH = "your_api_hash_here"  # 你的 API Hash

# 监控的群组/频道 ID
# 获取方式：将群组消息转发给 @userinfobot 获取群组ID
# 例如: -1001234567890
MONITOR_GROUP_IDS = [
    -1001234567890,  # 示例群组ID（负数）
]

# 信号来源用户ID过滤（可选，留空则接收所有用户的信号）
# 填入用户ID，只接收这些用户发的信号
SIGNAL_USER_IDS = []

# ============ 跟单配置 ============
# 是否启用跟单交易
COPYTRADE_ENABLED = True

# 是否跟随平仓信号
# True: 当信号源平仓时，自动平掉对应仓位
# False: 只跟开仓，自己管理止盈止损
FOLLOW_CLOSE_SIGNAL = False

# 跟单模式
# "OPEN_ONLY": 只跟开仓，不跟平仓（自己管理止盈止损）
# "FULL": 完全跟随，开仓和平仓都跟
COPYTRADE_MODE = "OPEN_ONLY"

# 仓位模式
# "FIXED": 固定仓位金额
# "RATIO": 按比例跟随
POSITION_MODE = "FIXED"

# 跟单比例（相对于信号仓位）
# 例如: 0.1 表示跟10%的仓位
POSITION_RATIO = 0.1

# 固定仓位金额（USDT），如果设置则忽略 POSITION_RATIO
# 例如: 100 表示每次开仓固定使用 100 USDT
FIXED_POSITION_SIZE = 100.0

# ============ 杠杆配置 ============
# 杠杆倍数 (1-125)
# "FOLLOW": 跟随信号的杠杆
# 数字: 使用固定杠杆
LEVERAGE = 10

# 保证金模式
# "ISOLATED": 逐仓模式（推荐）
# "CROSSED": 全仓模式
MARGIN_TYPE = "ISOLATED"

# ============ 止损止盈配置 ============
# 止损百分比（基于开仓价格）
STOP_LOSS_PERCENT = 3.0

# 止盈目标（分批止盈）
TAKE_PROFIT_1_PERCENT = 5.0   # 第一目标，平仓30%
TAKE_PROFIT_2_PERCENT = 10.0  # 第二目标，平仓30%
TAKE_PROFIT_3_PERCENT = 15.0  # 第三目标，全部平仓

# 是否启用追踪止损
ENABLE_TRAILING_STOP = True
TRAILING_STOP_ACTIVATION = 3.0  # 盈利3%后启动
TRAILING_STOP_CALLBACK = 2.0    # 回调2%触发

# ============ 风险控制 ============
# 单币种最大仓位（占总资金百分比）
MAX_POSITION_PERCENT = 10.0

# 总仓位上限（占总资金百分比）
MAX_TOTAL_POSITION_PERCENT = 50.0

# 单笔最大金额（USDT）
MAX_SINGLE_TRADE_VALUE = 500.0

# 每日最大交易次数
MAX_DAILY_TRADES = 20

# 每日最大亏损百分比
MAX_DAILY_LOSS_PERCENT = 10.0

# ============ 信号过滤 ============
# 最小杠杆倍数（低于此值的信号忽略）
MIN_LEVERAGE = 1

# 最大杠杆倍数（高于此值的信号忽略）
MAX_LEVERAGE = 50

# 只跟做多/做空
# "BOTH": 两个方向都跟
# "LONG": 只跟做多
# "SHORT": 只跟做空
DIRECTION_FILTER = "BOTH"

# 币种白名单（留空则不限制）
SYMBOL_WHITELIST = []

# 币种黑名单
SYMBOL_BLACKLIST = []

# 信号延迟容忍（秒），超过此时间的信号忽略
MAX_SIGNAL_DELAY = 60

# ============ 币安 API 配置 ============
# 可以单独配置，也可以复用 binance_trader 的配置
# 如果留空，将尝试从 binance_trader/config.py 读取
BINANCE_API_KEY = ""
BINANCE_API_SECRET = ""

# 是否使用测试网
USE_TESTNET = True

# SOCKS5 代理（可选）
SOCKS5_PROXY = ""

# ============ 通知配置 ============
# Telegram 通知 Bot
NOTIFY_BOT_TOKEN = ""
NOTIFY_CHAT_ID = ""

# 通知类型
NOTIFY_NEW_SIGNAL = True      # 新信号通知
NOTIFY_OPEN_POSITION = True   # 开仓通知
NOTIFY_CLOSE_POSITION = True  # 平仓通知
NOTIFY_ERRORS = True          # 错误通知

# ============ 日志配置 ============
LOG_LEVEL = "INFO"
LOG_FILE = "logs/telegram_copytrade.log"

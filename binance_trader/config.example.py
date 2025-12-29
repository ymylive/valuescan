"""
Binance 合约自动化交易配置文件示例
复制此文件为 config.py 并填入你的实际配置
"""

import os

# ============ Binance API 配置 ============
# 从币安官网获取: https://www.binance.com/en/my/settings/api-management
# ⚠️ 重要：合约交易需要启用 "Enable Futures" 权限
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "your_api_key_here")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "your_api_secret_here")

# 是否使用测试网（强烈建议先用测试网验证策略）
# 合约测试网: https://testnet.binancefuture.com/
# 优先读取环境变量 BINANCE_USE_TESTNET (true/false)
USE_TESTNET = os.getenv("BINANCE_USE_TESTNET", "true").lower() == "true"

# SOCKS5 代理配置（可选）
# 格式: socks5://用户名:密码@主机:端口
# 例如: socks5://user:pass@proxy.example.com:1080
# 优先读取环境变量 SOCKS5_PROXY 或 VALUESCAN_SOCKS5_PROXY
SOCKS5_PROXY = os.getenv("SOCKS5_PROXY") or os.getenv("VALUESCAN_SOCKS5_PROXY") or None

# 是否自动使用本地 SOCKS5 代理（例如 proxy-checker/xray 提供的 127.0.0.1:1080）
# 当 SOCKS5_PROXY 未配置时，如果检测到本地代理端口可用，则自动启用。
AUTO_PROXY_BINANCE = True

# 代理失败时是否自动切换直连（推荐开启，避免代理不稳定导致 API 全部超时）
ENABLE_PROXY_FALLBACK = True

# ============ 合约交易配置 ============
# 交易对后缀（合约通常是 USDT）
SYMBOL_SUFFIX = "USDT"

# 杠杆倍数 (1-125倍，建议不超过20倍)
# 高杠杆 = 高收益 + 高风险
LEVERAGE = 10  # 10倍杠杆

# 保证金模式
# "ISOLATED": 逐仓模式 - 每个仓位独立保证金（推荐，风险隔离）
# "CROSSED": 全仓模式 - 所有仓位共享保证金（风险较高）
MARGIN_TYPE = "ISOLATED"  # 推荐逐仓模式

# 持仓方向（暂时只支持做多）
# "LONG": 做多（买涨）
# "SHORT": 做空（买跌）- 未来版本支持
POSITION_SIDE = "LONG"

# ============ 币种黑名单配置 ============
# 交易系统币种黑名单（大写，不带后缀）
# 黑名单中的币种将被完全忽略，不会开仓
COIN_BLACKLIST = []  # 例如: ["DOGE", "SHIB", "PEPE"]

# ============ AI 托管模式配置 ============
# 是否启用 AI 托管模式
# True: 完全由 AI 信号分析决定交易，手动策略不生效
# False: 使用传统的信号聚合策略（FOMO + Alpha）
ENABLE_AI_MODE = False

# AI 托管模式下是否启用 AI 仓位管理子代理
# True: AI 会实时分析是否需要加仓、减仓、平仓
# False: 仅使用固定的止盈止损策略
ENABLE_AI_POSITION_AGENT = False

# AI 仓位管理检查间隔（秒）
AI_POSITION_CHECK_INTERVAL = 300  # 每5分钟检查一次

# AI 仓位管理 API 配置（如果为空，使用 ai_signal_config.json 中的配置）
AI_POSITION_API_KEY = ""
AI_POSITION_API_URL = ""
AI_POSITION_MODEL = ""

# ============ AI 自我进化配置 ============
# 是否启用 AI 自我进化系统
# True: AI 会分析交易数据，自动优化策略参数
# False: 使用固定参数，不进行自我学习
ENABLE_AI_EVOLUTION = False

# AI 进化策略配置
# 可选值:
#   - conservative_scalping: 稳健剥头皮 (低风险超短线)
#   - conservative_swing: 稳健波段 (低风险中线)
#   - balanced_day: 平衡日内 (平衡风险日内交易) [推荐]
#   - balanced_swing: 平衡波段 (平衡风险波段交易)
#   - aggressive_scalping: 激进剥头皮 (高频高风险)
#   - aggressive_day: 激进日内 (激进日内交易)
AI_EVOLUTION_PROFILE = "balanced_day"

# AI 进化最少交易数（达到此数量才开始学习）
AI_EVOLUTION_MIN_TRADES = 50

# AI 进化学习周期（天）
AI_EVOLUTION_LEARNING_PERIOD_DAYS = 30

# AI 进化间隔（小时）
AI_EVOLUTION_INTERVAL_HOURS = 24

# 是否启用 A/B 测试
# True: 新策略先在部分交易中测试
# False: 直接应用新策略
ENABLE_AI_AB_TESTING = True

# A/B 测试比例（0-1）
AI_AB_TEST_RATIO = 0.2  # 20% 使用新策略

# AI 进化 API 配置（如果为空，使用 ai_signal_config.json 中的配置）
AI_EVOLUTION_API_KEY = ""
AI_EVOLUTION_API_URL = ""
AI_EVOLUTION_MODEL = ""

# ============ 做多策略配置 ============
# 是否启用做多策略（仅在非 AI 模式下生效）
# 条件: Alpha(110) 或 FOMO(113) 信号 + 币种在异动榜单上
LONG_TRADING_ENABLED = True

# ============ 做空策略配置 ============
# 是否启用做空策略（仅在非 AI 模式下生效）
# 条件: 看跌信号(112/111/100) + 币种不在异动榜单上
SHORT_TRADING_ENABLED = False

# 做空止损百分比（基于开仓价格，向上）
SHORT_STOP_LOSS_PERCENT = 2.0

# 做空止盈百分比（基于开仓价格，向下）
# 仅在 SHORT_ENABLE_PYRAMIDING_EXIT = False 时使用
SHORT_TAKE_PROFIT_PERCENT = 3.0

# 是否启用做空金字塔退出（分批止盈）
SHORT_ENABLE_PYRAMIDING_EXIT = True

# 做空分批止盈策略：[(下跌百分比, 平仓比例), ...]
# 例如：下跌2%时平50%，下跌3%时再平50%，下跌5%时全平
SHORT_PYRAMIDING_EXIT_LEVELS = [
    (2.0, 0.5),   # 下跌2% → 平仓50%
    (3.0, 0.5),   # 下跌3% → 再平50%
    (5.0, 1.0),   # 下跌5% → 全部平仓
]

# ============ 信号聚合配置 ============
# 信号匹配时间窗口（秒）
# FOMO 和 Alpha 信号在此时间内出现才视为有效聚合信号
SIGNAL_TIME_WINDOW = 300  # 5分钟

# 最低信号评分阈值（0-1）
# 低于此评分的聚合信号将被忽略
MIN_SIGNAL_SCORE = 0.6

# 是否持久化信号状态，防止程序重启后丢失未处理信号
ENABLE_SIGNAL_STATE_CACHE = True

# 信号状态存储文件（相对路径相对于项目根目录）
SIGNAL_STATE_FILE = "data/signal_state.json"

# 持久化的已处理信号ID数量上限（用于防重复）
MAX_PROCESSED_SIGNAL_IDS = 5000

# 是否启用 FOMO 加剧信号 (Type 112)
# True: Type 112 作为风险信号，可用于止盈判断
# False: 忽略 Type 112 信号
ENABLE_FOMO_INTENSIFY = True

# ⚠️ 重要：信号类型说明
# Type 113 (FOMO) + Type 110 (Alpha) = 买入信号 ✅
# Type 112 (FOMO加剧) = 风险信号，建议止盈 ⚠️
#
# FOMO加剧表示市场情绪过热，可能接近顶部，不适合开仓
# 如果已有持仓，收到FOMO加剧信号应考虑止盈离场

# ============ 风险管理配置 ============
# 单个标的最大仓位比例（占总资金百分比）
# 注意：这是本金比例，实际仓位会乘以杠杆
# 例如：10% 本金 × 10倍杠杆 = 100% 仓位
MAX_POSITION_PERCENT = 5.0  # 单币种最多5%本金（合约建议更保守）

# 总仓位比例上限（占总资金百分比）
MAX_TOTAL_POSITION_PERCENT = 30.0  # 所有持仓合计不超过30%本金

# Separate caps for major vs alt positions (set None to use MAX_TOTAL_POSITION_PERCENT)
MAJOR_TOTAL_POSITION_PERCENT = 30.0
ALT_TOTAL_POSITION_PERCENT = 30.0

# 每日最大交易次数
MAX_DAILY_TRADES = 15  # 合约交易建议减少频率

# 每日最大亏损比例（达到后自动停止交易）
MAX_DAILY_LOSS_PERCENT = 5.0  # 单日亏损5%停止交易

# ============ 止损止盈配置 ============
# 固定止损百分比（基于开仓价格）
STOP_LOSS_PERCENT = 2.0  # 亏损2%止损（合约建议更严格）

# 第一目标盈利（减半仓位）
TAKE_PROFIT_1_PERCENT = 3.0  # 盈利3%减半仓位

# 第二目标盈利（清空仓位）
TAKE_PROFIT_2_PERCENT = 6.0  # 盈利6%全部平仓

# ============ 移动止损配置 ============
# 是否启用移动止损（Trailing Stop）
ENABLE_TRAILING_STOP = True

# 移动止损激活阈值（盈利达到此比例后启动移动止损）
# 例如：盈利2%后开始跟踪，此后如果回撤1.5%则触发止损
TRAILING_STOP_ACTIVATION = 2.0  # 盈利2%启动

# 移动止损回调比例（从最高点回撤多少触发止损）
TRAILING_STOP_CALLBACK = 1.5  # 回撤1.5%触发

# 移动止损更新间隔（秒）
TRAILING_STOP_UPDATE_INTERVAL = 10  # 每10秒检查一次

# 移动止损类型
# "PERCENTAGE": 百分比回撤
# "FIXED": 固定金额回撤（未来支持）
TRAILING_STOP_TYPE = "PERCENTAGE"

# ============ 分批止盈配置 ============
# 是否启用分批止盈（金字塔式平仓）
ENABLE_PYRAMIDING_EXIT = True

# 金字塔止盈执行方式:
# - "orders": 开仓时一次性挂多级止盈单（前端的止盈1/2/3会映射到 PYRAMIDING_EXIT_LEVELS）
# - "market": 由程序监控价格触发市价部分平仓（不在交易所显示挂单）
PYRAMIDING_EXIT_EXECUTION = "orders"

# 分批止盈策略：[(盈利百分比, 平仓比例), ...]
# 例如：盈利3%时平50%（剩余仓位的一半），盈利5%时再平50%，盈利8%时全平
PYRAMIDING_EXIT_LEVELS = [
    (3.0, 0.5),   # 盈利3% → 平仓50%
    (5.0, 0.5),   # 盈利5% → 再平50%
    (8.0, 1.0),   # 盈利8% → 全部平仓
]

# ============ 主流币独立策略配置 ============
# 主流币波动较小，需要更保守的止盈止损策略
# 可以自定义哪些币种属于"主流币"

# 主流币列表（大写，不带后缀）
# 这些币种将使用独立的止盈止损策略
MAJOR_COINS = ["BTC", "ETH", "BNB", "SOL", "XRP"]

# 是否启用主流币独立策略
ENABLE_MAJOR_COIN_STRATEGY = True

# 主流币杠杆倍数 (None 表示使用全局 LEVERAGE)
MAJOR_COIN_LEVERAGE = None

# 主流币最大仓位比例 (None 表示使用全局 MAX_POSITION_PERCENT)
MAJOR_COIN_MAX_POSITION_PERCENT = None

# 主流币止损百分比（通常比山寨币更宽松，因为波动小）
MAJOR_COIN_STOP_LOSS_PERCENT = 1.5  # 主流币止损1.5%

# 主流币金字塔止盈策略（通常止盈点更低，因为波动小）
# 格式：[(盈利百分比, 平仓比例), ...]
MAJOR_COIN_PYRAMIDING_EXIT_LEVELS = [
    (1.5, 0.3),   # 盈利1.5% → 平仓30%
    (2.5, 0.4),   # 盈利2.5% → 再平40%
    (4.0, 1.0),   # 盈利4.0% → 全部平仓
]

# 主流币移动止损配置
MAJOR_COIN_ENABLE_TRAILING_STOP = True  # 主流币是否启用移动止损
MAJOR_COIN_TRAILING_STOP_ACTIVATION = 1.0  # 盈利1%启动移动止损
MAJOR_COIN_TRAILING_STOP_CALLBACK = 0.8    # 回撤0.8%触发

# ============ 交易执行配置 ============
# 是否启用自动交易
# True: 发现聚合信号后自动执行交易
# False: 仅记录信号，不执行交易（观察模式）
AUTO_TRADING_ENABLED = False  # 默认关闭，确认策略后再开启

# 订单类型
# "MARKET": 市价单（立即成交，有滑点）
# "LIMIT": 限价单（指定价格，可能不成交）
ORDER_TYPE = "MARKET"

# 开仓前是否自动清理历史止盈/止损挂单（建议开启，避免旧单残留）
# 注意：仅在确认当前无持仓时才会执行，避免误删正在保护持仓的订单
CANCEL_EXIT_ORDERS_BEFORE_ENTRY = True

# 识别为“退出类挂单”的订单类型（用于精确取消，避免误删其它委托）
EXIT_ORDER_TYPES_TO_CANCEL = [
    "STOP_MARKET",
    "TAKE_PROFIT_MARKET",
    "STOP",
    "TAKE_PROFIT",
    "TRAILING_STOP_MARKET",
]

# 仓位精度（小数点后几位）
# 自动从交易所获取，这里是默认值
POSITION_PRECISION = 3

# ============ 监控配置 ============
# 持仓监控间隔（秒）
# 合约需要更频繁监控，特别是启用移动止损时
POSITION_MONITOR_INTERVAL = 10  # 每10秒检查一次持仓

# 余额更新间隔（秒）
BALANCE_UPDATE_INTERVAL = 60  # 每分钟更新一次余额

# 强平风险监控阈值（保证金率低于此值时告警）
LIQUIDATION_WARNING_MARGIN_RATIO = 30.0  # 保证金率 < 30% 时告警

# ============ 日志配置 ============
# 日志级别: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL = "INFO"

# 日志文件路径
LOG_FILE = "logs/binance_futures_trader.log"

# ============ Telegram 通知配置（可选）============
# 如果需要接收交易通知，填入 Telegram 配置
# 留空则不发送通知
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""

# 是否发送重要通知（开仓、平仓、止损触发等）
ENABLE_TELEGRAM_ALERTS = True

# ============ 高级配置 ============
# 价格滑点容忍度（百分比）
SLIPPAGE_TOLERANCE = 0.5  # 0.5%

# API 请求重试次数
API_RETRY_COUNT = 3

# API 请求超时（秒）
API_TIMEOUT = 30

# Binance 时间同步配置（避免 APIError(code=-1021): Timestamp ahead）
# 允许的最大时间窗口（毫秒），越大越不容易因为抖动触发 -1021（Binance 上限一般为 60000）
BINANCE_RECV_WINDOW_MS = 10000
# 自动对时间隔（秒），会定期调用 futures_time 同步 timestamp_offset
BINANCE_TIME_SYNC_INTERVAL = 300
# 安全余量（毫秒）：把签名时间戳保持在服务器时间稍后，避免边界条件“ahead”
BINANCE_TIME_SYNC_SAFETY_MS = 1500

# 是否使用对冲模式（Hedge Mode）
# True: 可以同时持有多空仓位
# False: 单向持仓模式（推荐）
USE_HEDGE_MODE = False

# ============ 安全配置 ============
# 最大单笔交易金额（USDT）
# 防止程序错误导致的大额交易
MAX_SINGLE_TRADE_VALUE = 1000.0  # 单笔最多1000 USDT

# 强制平仓保证金率（低于此值强制平仓所有持仓）
FORCE_CLOSE_MARGIN_RATIO = 20.0  # 保证金率 < 20% 强制平仓

# 是否启用紧急停止按钮（检测特定文件存在则停止交易）
ENABLE_EMERGENCY_STOP = True
EMERGENCY_STOP_FILE = "STOP_TRADING"  # 创建此文件即停止交易

# ============ 性能优化配置 ============
# 是否启用 WebSocket 实时价格推送（更快，推荐）
ENABLE_WEBSOCKET = True

# WebSocket 重连间隔（秒）
WEBSOCKET_RECONNECT_INTERVAL = 5

# ============ Telegram 通知配置 ============
# 是否启用交易通知
ENABLE_TRADE_NOTIFICATIONS = True

# Telegram Bot Token（从 @BotFather 获取）
# 如果留空，将尝试从信号监控模块的配置中读取
TELEGRAM_BOT_TOKEN = ""  # 留空则自动从 ../signal_monitor/config.py 读取

# Telegram Chat ID（你的用户 ID 或频道 ID）
# 如果留空，将尝试从信号监控模块的配置中读取
TELEGRAM_CHAT_ID = ""  # 留空则自动从 ../signal_monitor/config.py 读取

# 通知事件类型
NOTIFY_OPEN_POSITION = True      # 开仓通知
NOTIFY_CLOSE_POSITION = True     # 平仓通知
NOTIFY_STOP_LOSS = True          # 止损触发通知
NOTIFY_TAKE_PROFIT = True        # 止盈触发通知
NOTIFY_PARTIAL_CLOSE = True      # 部分平仓通知
NOTIFY_ERRORS = True             # 错误通知

# ============ 回测配置（未来版本）============
# 是否启用回测模式
ENABLE_BACKTEST = False

# 回测起始日期
BACKTEST_START_DATE = "2024-01-01"

# 回测结束日期
BACKTEST_END_DATE = "2024-12-31"

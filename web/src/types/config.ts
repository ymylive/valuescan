/**
 * ValueScan Configuration Types
 *
 * Type definitions for all ValueScan module configurations
 */

// ==================== AI Module Config ====================

/**
 * AI模块基础配置接口
 */
export interface AIModuleConfig {
  enabled: boolean
  api_key: string
  api_url: string
  model: string
}

/**
 * AI简评配置
 */
export interface AISignalConfig extends AIModuleConfig {
  interval_hours?: number
  lookback_hours?: number
}

/**
 * AI主力位配置
 */
export interface AILevelsConfig extends AIModuleConfig {
  // 可扩展特定字段
}

/**
 * AI辅助线/叠加层配置
 */
export interface AIOverlaysConfig extends AIModuleConfig {
  // 可扩展特定字段
}

/**
 * AI市场分析配置
 */
export interface AIMarketConfig extends AIModuleConfig {
  interval_hours: number
  lookback_hours: number
}

/**
 * API测试结果
 */
export interface AITestResult {
  success: boolean
  message?: string
  error?: string
}

// ==================== Signal Monitor Config ====================

export interface SignalMonitorConfig {
  // Telegram
  telegram_bot_token: string
  telegram_chat_id: string
  enable_telegram: boolean
  send_tg_in_mode_1: boolean

  // Browser
  chrome_debug_port: number
  headless_mode: boolean

  // API
  api_path: string
  ai_api_path: string

  // Language
  language: 'zh' | 'en'

  // IPC
  enable_ipc_forwarding: boolean
  ipc_host: string
  ipc_port: number
  ipc_connect_timeout: number
  ipc_retry_delay: number
  ipc_max_retries: number

  // Proxy
  socks5_proxy: string
  http_proxy: string

  // Chart
  enable_tradingview_chart: boolean
  enable_pro_chart: boolean
  auto_delete_charts: boolean
  chart_img_api_key: string
  chart_img_layout_id: string
  chart_img_width: number
  chart_img_height: number
  chart_img_timeout: number
  enable_ai_key_levels: boolean
  enable_ai_overlays: boolean
  enable_ai_signal_analysis: boolean

  // Logging
  log_level: string
  log_to_file: boolean
  log_file: string
  log_max_size: number
  log_backup_count: number
  log_format: string
  log_date_format: string

  // AI Market Summary (旧配置，保持兼容)
  ai_summary_enabled: boolean
  ai_summary_interval_hours: number
  ai_summary_api_key: string
  ai_summary_api_url: string
  ai_summary_model: string
  ai_summary_lookback_hours: number

  // AI模块独立配置
  ai_signal_config?: AISignalConfig
  ai_levels_config?: AILevelsConfig
  ai_overlays_config?: AIOverlaysConfig
  ai_market_config?: AIMarketConfig

  // External Data API Keys
  coinmarketcap_api_key: string
  cryptocompare_api_key: string
  coingecko_api_key: string
  etherscan_api_key: string
  crypto_news_api_key: string

  // Polling & Monitoring
  poll_interval: number
  request_timeout: number
  max_consecutive_failures: number
  failure_cooldown: number
  auto_relogin: boolean
  auto_relogin_cooldown: number

  // Token Refresher
  token_refresh_interval_hours: number
  token_refresh_safety_seconds: number
  login_method: 'auto' | 'http' | 'cdp' | 'browser'
  refresh_window_start: number
  refresh_window_end: number

  // AI Market Summary Enhanced
  ai_summary_proxy: string

  // Signal Filtering
  startup_signal_max_age_seconds: number
  signal_max_age_seconds: number
}

// ==================== Trader Config ====================

export interface TraderConfig {
  // API
  binance_api_key: string
  binance_api_secret: string
  use_testnet: boolean
  socks5_proxy: string | null
  auto_proxy_binance: boolean
  enable_proxy_fallback: boolean

  // Trading
  symbol_suffix: string
  leverage: number
  margin_type: 'ISOLATED' | 'CROSSED'
  position_side: 'LONG' | 'SHORT' | 'BOTH'

  // Coin Blacklist
  coin_blacklist: string[]

  // AI Mode
  enable_ai_mode: boolean
  enable_ai_position_agent: boolean
  ai_position_check_interval: number
  ai_position_api_key: string
  ai_position_api_url: string
  ai_position_model: string

  // AI Evolution
  enable_ai_evolution: boolean
  ai_evolution_profile: string
  ai_evolution_min_trades: number
  ai_evolution_learning_period_days: number
  ai_evolution_interval_hours: number
  enable_ai_ab_testing: boolean
  ai_ab_test_ratio: number
  ai_evolution_api_key: string
  ai_evolution_api_url: string
  ai_evolution_model: string

  // Long Strategy
  long_trading_enabled: boolean

  // Short Strategy
  short_trading_enabled: boolean
  short_stop_loss_percent: number
  short_take_profit_percent: number
  short_enable_pyramiding_exit: boolean
  short_pyramiding_exit_levels: [number, number][]

  // Signal Aggregation
  signal_time_window: number
  min_signal_score: number
  enable_signal_state_cache: boolean
  signal_state_file: string
  max_processed_signal_ids: number
  enable_fomo_intensify: boolean

  // Risk Management
  max_position_percent: number
  max_total_position_percent: number
  major_total_position_percent: number
  alt_total_position_percent: number
  max_daily_trades: number
  max_daily_loss_percent: number

  // Stop Loss / Take Profit
  stop_loss_percent: number
  take_profit_1_percent: number
  take_profit_2_percent: number
  take_profit_3_percent: number

  // Trailing Stop
  enable_trailing_stop: boolean
  trailing_stop_activation: number
  trailing_stop_callback: number
  trailing_stop_update_interval: number
  trailing_stop_type: string

  // Pyramiding Exit
  enable_pyramiding_exit: boolean
  pyramiding_exit_execution: 'orders' | 'market'
  pyramiding_exit_levels: [number, number][]

  // Execution
  auto_trading_enabled: boolean
  order_type: 'MARKET' | 'LIMIT'
  cancel_exit_orders_before_entry: boolean
  exit_order_types_to_cancel: string[]
  position_precision: number

  // Monitoring
  position_monitor_interval: number
  balance_update_interval: number
  liquidation_warning_margin_ratio: number

  // Safety
  max_single_trade_value: number
  force_close_margin_ratio: number
  enable_emergency_stop: boolean
  emergency_stop_file: string

  // WebSocket
  enable_websocket: boolean
  websocket_reconnect_interval: number

  // Notifications
  enable_trade_notifications: boolean
  enable_telegram_alerts: boolean
  telegram_bot_token: string
  telegram_chat_id: string
  notify_open_position: boolean
  notify_close_position: boolean
  notify_stop_loss: boolean
  notify_take_profit: boolean
  notify_partial_close: boolean
  notify_errors: boolean

  // API Settings
  slippage_tolerance: number
  api_retry_count: number
  api_timeout: number
  binance_recv_window_ms: number
  binance_time_sync_interval: number
  binance_time_sync_safety_ms: number
  use_hedge_mode: boolean

  // Major Coin Strategy
  major_coins: string[]
  enable_major_coin_strategy: boolean
  major_coin_leverage: number
  major_coin_max_position_percent: number
  major_coin_stop_loss_percent: number
  major_coin_pyramiding_exit_levels: [number, number][]
  major_coin_enable_trailing_stop: boolean
  major_coin_trailing_stop_activation: number
  major_coin_trailing_stop_callback: number

  // Logging
  log_level: string
  log_file: string

  // Backtest
  enable_backtest: boolean
  backtest_start_date: string
  backtest_end_date: string
}

// ==================== CopyTrade Config ====================

export interface CopyTradeConfig {
  // Telegram API
  telegram_api_id: number
  telegram_api_hash: string
  monitor_group_ids: number[]
  signal_user_ids: number[]

  // Position
  copytrade_enabled: boolean
  follow_close_signal: boolean
  copytrade_mode: 'OPEN_ONLY' | 'FULL'
  position_mode: 'FIXED' | 'RATIO'
  position_ratio: number
  fixed_position_size: number

  // Leverage
  leverage: number | 'FOLLOW'
  margin_type: 'ISOLATED' | 'CROSSED'

  // Stop Loss / Take Profit
  stop_loss_percent: number
  take_profit_1_percent: number
  take_profit_2_percent: number
  take_profit_3_percent: number
  enable_trailing_stop: boolean
  trailing_stop_activation: number
  trailing_stop_callback: number

  // Risk Control
  max_position_percent: number
  max_total_position_percent: number
  max_single_trade_value: number
  max_daily_trades: number
  max_daily_loss_percent: number

  // Signal Filter
  min_leverage: number
  max_leverage: number
  direction_filter: 'BOTH' | 'LONG' | 'SHORT'
  symbol_whitelist: string[]
  symbol_blacklist: string[]
  max_signal_delay: number

  // Binance API
  binance_api_key: string
  binance_api_secret: string
  use_testnet: boolean
  socks5_proxy: string

  // Notifications
  notify_bot_token: string
  notify_chat_id: string
  notify_new_signal: boolean
  notify_open_position: boolean
  notify_close_position: boolean
  notify_errors: boolean

  // Logging
  log_level: string
  log_file: string
}

// ==================== Keepalive Config ====================

export interface KeepaliveGlobalConfig {
  check_interval: number
  restart_cooldown: number
  log_file: string
}

export interface KeepaliveTelegramConfig {
  enabled: boolean
  bot_token: string
  chat_id: string
}

export interface KeepaliveServiceConfig {
  name: string
  display_name: string
  check_interval?: number
  restart_cooldown?: number
  no_log_threshold: number | null
  enabled: boolean
}

export interface KeepaliveConfig {
  global: KeepaliveGlobalConfig
  telegram: KeepaliveTelegramConfig
  services: KeepaliveServiceConfig[]
}

// ==================== All Config ====================

export interface AllConfig {
  signal: Partial<SignalMonitorConfig>
  trader: Partial<TraderConfig>
  copytrade: Partial<CopyTradeConfig>
}

// ==================== Field Schema ====================

export interface FieldSchema {
  key: string
  type: 'string' | 'number' | 'boolean' | 'array' | 'object'
  label: string
  description?: string
  sensitive?: boolean
  required?: boolean
  min?: number
  max?: number
  options?: { value: string | number | boolean; label: string }[]
  pattern?: string
  group?: string
}

// ==================== Config Groups ====================

export const CONFIG_GROUPS = {
  signal: ['telegram', 'browser', 'api', 'ipc', 'proxy', 'chart', 'logging'],
  trader: [
    'api',
    'trading',
    'signal_aggregation',
    'risk',
    'stop_loss',
    'trailing_stop',
    'pyramiding',
    'execution',
    'monitoring',
    'safety',
    'websocket',
    'notifications',
  ],
  copytrade: [
    'telegram_api',
    'position',
    'leverage',
    'stop_loss',
    'risk',
    'signal_filter',
    'binance_api',
    'notifications',
    'logging',
  ],
  keepalive: ['global', 'telegram', 'services'],
} as const

// ==================== Service Status ====================

export type ServiceStatus = 'running' | 'stopped' | 'error'

export interface ServiceStatusData {
  signal_monitor: ServiceStatus
  trader: ServiceStatus
  copytrade: ServiceStatus
  keepalive: ServiceStatus
}

// ==================== API Response Types ====================

export interface ConfigSaveResult {
  success: boolean
  saved?: Record<string, boolean>
  errors?: string[]
  restarted?: Record<string, boolean>
  restart_errors?: string[]
  config?: Partial<AllConfig>
  needs_restart?: string[]
}

export interface KeepaliveConfigResponse {
  success: boolean
  config?: KeepaliveConfig
  path?: string
  error?: string
  errors?: string[]
  needs_restart?: string[]
}

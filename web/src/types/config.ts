/**
 * ValueScan Configuration Types
 *
 * Type definitions for all ValueScan module configurations
 */

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
  chart_img_api_key: string
  chart_img_layout_id: string
  chart_img_width: number
  chart_img_height: number
  chart_img_timeout: number

  // Logging
  log_level: string
  log_to_file: boolean
  log_file: string
  log_max_size: number
  log_backup_count: number

  // AI Market Summary
  ai_summary_enabled: boolean
  ai_summary_interval_hours: number
  ai_summary_api_key: string
  ai_summary_api_url: string
  ai_summary_model: string
  ai_summary_lookback_hours: number
}

// ==================== Trader Config ====================

export interface TraderConfig {
  // API
  binance_api_key: string
  binance_api_secret: string
  use_testnet: boolean
  socks5_proxy: string | null
  enable_proxy_fallback: boolean

  // Trading
  symbol_suffix: string
  leverage: number
  margin_type: 'ISOLATED' | 'CROSSED'
  position_side: 'LONG' | 'SHORT' | 'BOTH'

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

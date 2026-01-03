// Configuration types for ValueScan platform

// AI Service Configuration
export interface AIServiceConfig {
  // AI Position Management
  ai_position_api_key: string;
  ai_position_api_url: string;
  ai_position_model: string;
  enable_ai_position_agent: boolean;
  ai_position_check_interval: number;

  // AI Evolution
  ai_evolution_api_key: string;
  ai_evolution_api_url: string;
  ai_evolution_model: string;
  enable_ai_evolution: boolean;
  ai_evolution_profile: string;
  ai_evolution_min_trades: number;
  ai_evolution_learning_period_days: number;
  ai_evolution_interval_hours: number;
  enable_ai_ab_testing: boolean;
  ai_ab_test_ratio: number;

  // AI Signal Analysis (单币简评)
  ai_signal_analysis_api_key: string;
  ai_signal_analysis_api_url: string;
  ai_signal_analysis_model: string;
  enable_ai_signal_analysis_service: boolean;
  ai_signal_analysis_interval: number;
  ai_signal_analysis_lookback_hours: number;

  // AI Key Levels (主力位分析)
  ai_key_levels_api_key: string;
  ai_key_levels_api_url: string;
  ai_key_levels_model: string;
  enable_ai_key_levels_service: boolean;

  // AI Overlays (图表叠加层)
  ai_overlays_api_key: string;
  ai_overlays_api_url: string;
  ai_overlays_model: string;
  enable_ai_overlays_service: boolean;

  // AI Market Analysis (市场宏观分析)
  ai_market_analysis_api_key: string;
  ai_market_analysis_api_url: string;
  ai_market_analysis_model: string;
  enable_ai_market_analysis: boolean;
  ai_market_analysis_interval: number;
  ai_market_analysis_lookback_hours: number;

  // AI Summary Proxy
  ai_summary_proxy: string;
}

// Signal Monitor Configuration
export interface SignalMonitorConfig {
  // Telegram Bot
  telegram_bot_token: string;
  telegram_chat_id: string;
  enable_telegram: boolean;
  send_tg_in_mode_1: boolean;

  // Browser
  chrome_debug_port: number;
  headless_mode: boolean;

  // API
  api_path: string;
  ai_api_path: string;
  language: string;

  // External Data APIs
  coinmarketcap_api_key: string;
  cryptocompare_api_key: string;
  coingecko_api_key: string;
  etherscan_api_key: string;
  crypto_news_api_key: string;

  // Polling
  poll_interval: number;
  request_timeout: number;
  max_consecutive_failures: number;
  failure_cooldown: number;
  startup_signal_max_age_seconds: number;
  signal_max_age_seconds: number;

  // IPC Forwarding
  enable_ipc_forwarding: boolean;
  ipc_host: string;
  ipc_port: number;
  ipc_connect_timeout: number;
  ipc_retry_delay: number;
  ipc_max_retries: number;

  // Network Proxy
  socks5_proxy: string;
  http_proxy: string;

  // Chart Features
  enable_pro_chart: boolean;
  enable_ai_key_levels: boolean;
  enable_ai_overlays: boolean;
  enable_ai_signal_analysis: boolean;
  ai_brief_wait_timeout_seconds: number;  // AI简评等待超时（秒）
  bull_bear_signal_ttl_seconds: number;  // 看涨/看跌信号有效期（秒）
  enable_tradingview_chart: boolean;
  chart_img_api_key: string;
  chart_img_layout_id: string;
  chart_img_width: number;
  chart_img_height: number;
  chart_img_timeout: number;
  auto_delete_charts: boolean;

  // ValuScan Data Source
  enable_valuescan_key_levels: boolean;
  valuescan_key_levels_as_primary: boolean;
  valuescan_key_levels_days: number;  // 图像生成主力位有效期（天）
  valuescan_ai_analysis_days: number;  // AI分析模块有效期（天）
}

// Trading Bot Configuration
export interface TradingBotConfig {
  // Binance API
  binance_api_key: string;
  binance_api_secret: string;
  use_testnet: boolean;
  socks5_proxy: string;
  auto_proxy_binance: boolean;
  enable_proxy_fallback: boolean;

  // Contract Trading
  symbol_suffix: string;
  leverage: number;
  margin_type: string;
  position_side: string;

  // Coin Blacklist
  coin_blacklist: string[];

  // AI Mode
  enable_ai_mode: boolean;

  // Trading Strategies
  long_trading_enabled: boolean;
  short_trading_enabled: boolean;
  short_stop_loss_percent: number;
  short_take_profit_percent: number;
  short_enable_pyramiding_exit: boolean;
  short_pyramiding_exit_levels: [number, number][];

  // Signal Aggregation
  signal_time_window: number;
  min_signal_score: number;
  enable_signal_state_cache: boolean;
  signal_state_file: string;
  max_processed_signal_ids: number;
  enable_fomo_intensify: boolean;

  // Risk Management
  max_position_percent: number;
  max_total_position_percent: number;
  major_total_position_percent: number;
  alt_total_position_percent: number;
  max_daily_trades: number;
  max_daily_loss_percent: number;

  // Stop Loss & Take Profit
  stop_loss_percent: number;
  take_profit_1_percent: number;
  take_profit_2_percent: number;

  // Trailing Stop
  enable_trailing_stop: boolean;
  trailing_stop_activation: number;
  trailing_stop_callback: number;
  trailing_stop_update_interval: number;
  trailing_stop_type: string;

  // Pyramiding Exit
  enable_pyramiding_exit: boolean;
  pyramiding_exit_execution: string;
  pyramiding_exit_levels: [number, number][];

  // Major Coins Strategy
  major_coins: string[];
  enable_major_coin_strategy: boolean;
  major_coin_leverage: number | null;
  major_coin_max_position_percent: number | null;
  major_coin_stop_loss_percent: number;
  major_coin_pyramiding_exit_levels: [number, number][];
  major_coin_enable_trailing_stop: boolean;
  major_coin_trailing_stop_activation: number;
  major_coin_trailing_stop_callback: number;

  // Trading Execution
  auto_trading_enabled: boolean;
  order_type: string;
  cancel_exit_orders_before_entry: boolean;
  exit_order_types_to_cancel: string[];
  position_precision: number;

  // Monitoring
  position_monitor_interval: number;
  balance_update_interval: number;
  liquidation_warning_margin_ratio: number;

  // Telegram Notifications
  enable_telegram_alerts: boolean;
  enable_trade_notifications: boolean;
  notify_open_position: boolean;
  notify_close_position: boolean;
  notify_stop_loss: boolean;
  notify_take_profit: boolean;
  notify_partial_close: boolean;
  notify_errors: boolean;

  // Advanced
  slippage_tolerance: number;
  api_retry_count: number;
  api_timeout: number;
  binance_recv_window_ms: number;
  binance_time_sync_interval: number;
  binance_time_sync_safety_ms: number;
  use_hedge_mode: boolean;

  // Safety
  max_single_trade_value: number;
  force_close_margin_ratio: number;
  enable_emergency_stop: boolean;
  emergency_stop_file: string;

  // Performance
  enable_websocket: boolean;
  websocket_reconnect_interval: number;

  // Backtest
  enable_backtest: boolean;
  backtest_start_date: string;
  backtest_end_date: string;
}

// System Configuration
export interface SystemConfig {
  // Server
  nofx_backend_port: number;
  nofx_frontend_port: number;
  nofx_timezone: string;

  // Authentication
  jwt_secret: string;
  data_encryption_key: string;
  rsa_private_key: string;
  transport_encryption: boolean;

  // External Services
  binance_socks5_proxy: string;
  binance_http_proxy: string;
  telegram_bot_token: string;
  telegram_chat_id: string;
}

// Logging Configuration
export interface LoggingConfig {
  log_level: string;
  log_to_file: boolean;
  log_file: string;
  log_max_size: number;
  log_backup_count: number;
  log_format: string;
  log_date_format: string;
}

// Telegram Copy Trade Configuration
export interface CopyTradeConfig {
  // Telegram API
  telegram_api_id: number;
  telegram_api_hash: string;
  monitor_group_ids: number[];
  signal_user_ids: number[];

  // Copy Trade Settings
  copytrade_enabled: boolean;
  follow_close_signal: boolean;
  copytrade_mode: 'OPEN_ONLY' | 'FULL';
  position_mode: 'FIXED' | 'RATIO';
  position_ratio: number;
  fixed_position_size: number;

  // Stop Loss & Take Profit
  take_profit_3_percent: number;

  // Signal Filtering
  min_leverage: number;
  max_leverage: number;
  direction_filter: 'BOTH' | 'LONG' | 'SHORT';
  symbol_whitelist: string[];
  symbol_blacklist: string[];
  max_signal_delay: number;

  // Notifications
  notify_bot_token: string;
  notify_chat_id: string;
  notify_new_signal: boolean;
}

// Keepalive Configuration
export interface KeepaliveConfig {
  keepalive_config_path: string;
  keepalive_check_interval: number;
  keepalive_restart_delay: number;
  keepalive_max_restarts: number;
  keepalive_services: ServiceConfig[];
}

// Service Configuration for Keepalive
export interface ServiceConfig {
  name: string;
  enabled: boolean;
  command: string;
  working_directory: string;
  health_check_url?: string;
  health_check_interval?: number;
}

// Environment Variables Configuration
export interface EnvironmentConfig {
  // Database
  valuescan_db_path: string;
  valuescan_performance_db_path: string;

  // Proxy
  binance_default_socks5: string;
  valuescan_socks5_proxy: string;
  valuescan_proxy: string;
  valuescan_vps_password: string;

  // Login Credentials
  valuescan_email: string;
  valuescan_password: string;
}

// Complete Configuration
export interface CompleteConfig {
  ai_service: AIServiceConfig;
  signal_monitor: SignalMonitorConfig;
  trading_bot: TradingBotConfig;
  copytrade: CopyTradeConfig;
  keepalive: KeepaliveConfig;
  system: SystemConfig;
  logging: LoggingConfig;
  environment: EnvironmentConfig;
}

// AI Evolution Profile Options
export const AI_EVOLUTION_PROFILES = [
  { value: 'conservative_scalping', label: '稳健剥头皮（低风险超短线）' },
  { value: 'conservative_swing', label: '稳健波段（低风险中线）' },
  { value: 'balanced_day', label: '平衡日内（推荐）' },
  { value: 'balanced_swing', label: '平衡波段' },
  { value: 'aggressive_scalping', label: '激进剥头皮' },
  { value: 'aggressive_day', label: '激进日内' },
];

// Log Level Options
export const LOG_LEVELS = [
  { value: 'DEBUG', label: 'DEBUG' },
  { value: 'INFO', label: 'INFO' },
  { value: 'WARNING', label: 'WARNING' },
  { value: 'ERROR', label: 'ERROR' },
  { value: 'CRITICAL', label: 'CRITICAL' },
];

// Margin Type Options
export const MARGIN_TYPES = [
  { value: 'ISOLATED', label: '逐仓' },
  { value: 'CROSSED', label: '全仓' },
];

// Position Side Options
export const POSITION_SIDES = [
  { value: 'LONG', label: '做多' },
  { value: 'SHORT', label: '做空' },
];

// Order Type Options
export const ORDER_TYPES = [
  { value: 'MARKET', label: '市价单' },
  { value: 'LIMIT', label: '限价单' },
];

// Trailing Stop Type Options
export const TRAILING_STOP_TYPES = [
  { value: 'PERCENTAGE', label: '百分比' },
  { value: 'CALLBACK_RATE', label: '回调率' },
];

// Copy Trade Mode Options
export const COPYTRADE_MODES = [
  { value: 'OPEN_ONLY', label: '仅开仓' },
  { value: 'FULL', label: '完全跟单（含平仓）' },
];

// Position Mode Options
export const POSITION_MODES = [
  { value: 'FIXED', label: '固定仓位' },
  { value: 'RATIO', label: '比例仓位' },
];

// Direction Filter Options
export const DIRECTION_FILTERS = [
  { value: 'BOTH', label: '做多和做空' },
  { value: 'LONG', label: '仅做多' },
  { value: 'SHORT', label: '仅做空' },
];

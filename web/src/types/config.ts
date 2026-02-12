// Configuration types for the platform

export type AIProtocol = 'auto' | 'compatible' | 'responses';

export interface AIServiceConfig {
  // AI Signal Analysis
  ai_signal_analysis_api_key: string;
  ai_signal_analysis_api_url: string;
  ai_signal_analysis_api_protocol: AIProtocol;
  ai_signal_analysis_model: string;
  ai_signal_analysis_secondary_api_key: string;
  ai_signal_analysis_secondary_api_url: string;
  ai_signal_analysis_secondary_api_protocol: AIProtocol;
  ai_signal_analysis_secondary_model: string;
  ai_signal_analysis_tertiary_api_key: string;
  ai_signal_analysis_tertiary_api_url: string;
  ai_signal_analysis_tertiary_api_protocol: AIProtocol;
  ai_signal_analysis_tertiary_model: string;
  ai_signal_analysis_mcp_enabled: boolean;
  ai_signal_analysis_mcp_query_template: string;
  ai_signal_analysis_mcp_max_results: number;
  ai_signal_analysis_mcp_timeout_sec: number;
  ai_signal_analysis_mcp_cache_ttl_sec: number;
  ai_signal_analysis_mcp_max_prompt_chars: number;
  ai_signal_analysis_mcp_source_primary_enabled: boolean;
  ai_signal_analysis_mcp_source_primary_name: string;
  ai_signal_analysis_mcp_source_primary_command: string;
  ai_signal_analysis_mcp_source_primary_args: string;
  ai_signal_analysis_mcp_source_primary_tool_name: string;
  ai_signal_analysis_mcp_source_primary_env_json: string;
  ai_signal_analysis_mcp_source_secondary_enabled: boolean;
  ai_signal_analysis_mcp_source_secondary_name: string;
  ai_signal_analysis_mcp_source_secondary_command: string;
  ai_signal_analysis_mcp_source_secondary_args: string;
  ai_signal_analysis_mcp_source_secondary_tool_name: string;
  ai_signal_analysis_mcp_source_secondary_env_json: string;
  enable_ai_signal_analysis_service: boolean;
  ai_signal_analysis_interval_hours: number;
  ai_signal_analysis_lookback_hours: number;

  // AI Key Levels
  ai_key_levels_api_key: string;
  ai_key_levels_api_url: string;
  ai_key_levels_api_protocol: AIProtocol;
  ai_key_levels_model: string;
  enable_ai_key_levels_service: boolean;

  // AI Overlays
  ai_overlays_api_key: string;
  ai_overlays_api_url: string;
  ai_overlays_api_protocol: AIProtocol;
  ai_overlays_model: string;
  enable_ai_overlays_service: boolean;

  // AI Market Analysis
  ai_market_analysis_api_key: string;
  ai_market_analysis_api_url: string;
  ai_market_analysis_api_protocol: AIProtocol;
  ai_market_analysis_model: string;
  enable_ai_market_analysis: boolean;
  ai_market_analysis_interval_hours: number;
  ai_market_analysis_lookback_hours: number;

  // AI Summary Proxy
  ai_summary_proxy: string;
}

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

  // Polling
  poll_interval: number;
  request_timeout: number;
  max_consecutive_failures: number;
  failure_cooldown: number;
  auto_relogin?: boolean;
  auto_relogin_cooldown?: number;
  startup_signal_max_age_seconds: number;
  signal_max_age_seconds: number;

  // Scheduled AI Signals
  ai_signal_interval_minutes: number;
  realtime_market_enabled: boolean;

  // Token Refresh
  token_refresh_interval_hours?: number;
  token_refresh_safety_seconds?: number;
  login_method?: string;
  refresh_window_start?: number;
  refresh_window_end?: number;

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
  ai_brief_wait_timeout_seconds: number;
  bull_bear_signal_ttl_seconds: number;
  enable_tradingview_chart: boolean;
  chart_img_api_key: string;
  chart_img_layout_id: string;
  chart_img_width: number;
  chart_img_height: number;
  chart_img_timeout: number;
  auto_delete_charts: boolean;
}

export interface SystemConfig {
  nofx_backend_port: number;
  nofx_frontend_port: number;
  nofx_timezone: string;
  jwt_secret: string;
  data_encryption_key: string;
  rsa_private_key: string;
  transport_encryption: boolean;
}

export interface LoggingConfig {
  log_level: string;
  log_to_file: boolean;
  log_file: string;
  log_max_size: number;
  log_backup_count: number;
  log_format: string;
  log_date_format: string;
}

export interface EnvironmentConfig {
  valuescan_email: string;
  valuescan_password: string;
  valuescan_vps_password: string;
}

export interface CompleteConfig {
  ai_service: AIServiceConfig;
  signal_monitor: SignalMonitorConfig;
  system: SystemConfig;
  logging: LoggingConfig;
  environment: EnvironmentConfig;
  anomaly: AnomalyDetectorConfig;
  us_market: USMarketConfig;
}

export const LOGIN_METHODS = [
  { value: 'auto', label: '自动' },
  { value: 'http', label: 'HTTP' },
  { value: 'cdp', label: 'CDP' },
  { value: 'browser', label: '浏览器' },
];

export const LOG_LEVELS = [
  { value: 'DEBUG', label: 'DEBUG' },
  { value: 'INFO', label: 'INFO' },
  { value: 'WARNING', label: 'WARNING' },
  { value: 'ERROR', label: 'ERROR' },
  { value: 'CRITICAL', label: 'CRITICAL' },
];

// 异动源类型
export type AnomalySource = 'local';

// 异动检测配置
export interface AnomalyDetectorConfig {
  // 异动源选择
  anomaly_source: AnomalySource;
  // 基础设置
  symbols: string[];
  // 量价检测
  vol_spike_threshold: number;
  vol_zscore_threshold: number;
  price_change_threshold: number;
  // 衍生品检测
  funding_warn_negative: number;
  funding_warn_positive: number;
  funding_extreme_negative: number;
  funding_extreme_positive: number;
  oi_change_warn: number;
  oi_change_extreme: number;
  // 盘口分析
  imbalance_threshold: number;
  whale_wall_usd: number;
  spread_warn: number;
  // 相关性过滤
  correlation_window_minutes: number;
  independence_threshold: number;
  // 情绪检测
  fear_extreme: number;
  greed_extreme: number;
  // 动态阈值
  use_dynamic_threshold: boolean;
  zscore_threshold: number;
  atr_multiplier: number;
  // 评分系统
  scoring_enabled: boolean;
  scoring_weights: {
    volume_price: number;
    derivatives: number;
    fund_flow: number;
    orderbook: number;
    sentiment: number;
  };
  scoring_thresholds: {
    info: number;
    warning: number;
    alert: number;
  };
}

// 美股监控配置
export interface USMarketConfig {
  enabled: boolean;
  check_after_open_minutes: number;
  categories: {
    indices: string[];
    tech: string[];
    crypto_stocks: string[];
    macro: string[];
  };
  vix_symbol: string;
  ai_analysis_enabled: boolean;
}

// 默认异动检测配置
export const DEFAULT_ANOMALY_CONFIG: AnomalyDetectorConfig = {
  anomaly_source: 'local',
  symbols: ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE'],
  vol_spike_threshold: 6.0,
  vol_zscore_threshold: 3.5,
  price_change_threshold: 3.5,
  funding_warn_negative: -0.015,
  funding_warn_positive: 0.05,
  funding_extreme_negative: -0.04,
  funding_extreme_positive: 0.12,
  oi_change_warn: 5.0,
  oi_change_extreme: 12.0,
  imbalance_threshold: 4.0,
  whale_wall_usd: 4000000,
  spread_warn: 0.001,
  correlation_window_minutes: 60,
  independence_threshold: 0.6,
  fear_extreme: 20,
  greed_extreme: 80,
  use_dynamic_threshold: true,
  zscore_threshold: 3.5,
  atr_multiplier: 3.5,
  scoring_enabled: true,
  scoring_weights: {
    volume_price: 0.30,
    derivatives: 0.25,
    fund_flow: 0.20,
    orderbook: 0.15,
    sentiment: 0.10,
  },
  scoring_thresholds: {
    info: 55,
    warning: 70,
    alert: 85,
  },
};

// 默认美股监控配置
export const DEFAULT_US_MARKET_CONFIG: USMarketConfig = {
  enabled: true,
  check_after_open_minutes: 5,
  categories: {
    indices: ['SPY', 'QQQ', 'DIA', 'IWM'],
    tech: ['NVDA', 'AAPL', 'MSFT', 'GOOGL', 'META', 'AMZN', 'TSLA'],
    crypto_stocks: ['COIN', 'MSTR', 'MARA', 'RIOT'],
    macro: ['GLD', 'TLT'],
  },
  vix_symbol: '^VIX',
  ai_analysis_enabled: true,
};

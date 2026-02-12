import {
  DEFAULT_ANOMALY_CONFIG,
  DEFAULT_US_MARKET_CONFIG,
  type AIServiceConfig,
  type CompleteConfig,
  type LoggingConfig,
  type SignalMonitorConfig,
  type SystemConfig,
} from '../types/config';

const AI_SERVICE_DEFAULTS: AIServiceConfig = {
  ai_signal_analysis_api_key: '',
  ai_signal_analysis_api_url: '',
  ai_signal_analysis_api_protocol: 'auto',
  ai_signal_analysis_model: '',
  ai_signal_analysis_secondary_api_key: '',
  ai_signal_analysis_secondary_api_url: '',
  ai_signal_analysis_secondary_api_protocol: 'auto',
  ai_signal_analysis_secondary_model: '',
  ai_signal_analysis_tertiary_api_key: '',
  ai_signal_analysis_tertiary_api_url: '',
  ai_signal_analysis_tertiary_api_protocol: 'auto',
  ai_signal_analysis_tertiary_model: '',
  ai_signal_analysis_mcp_enabled: false,
  ai_signal_analysis_mcp_query_template:
    '{symbol} crypto latest market news macro policy risk funding open interest sentiment',
  ai_signal_analysis_mcp_max_results: 5,
  ai_signal_analysis_mcp_timeout_sec: 25,
  ai_signal_analysis_mcp_cache_ttl_sec: 900,
  ai_signal_analysis_mcp_max_prompt_chars: 2500,
  ai_signal_analysis_mcp_source_primary_enabled: true,
  ai_signal_analysis_mcp_source_primary_name: 'brave',
  ai_signal_analysis_mcp_source_primary_command: 'npx',
  ai_signal_analysis_mcp_source_primary_args: '-y @modelcontextprotocol/server-brave-search',
  ai_signal_analysis_mcp_source_primary_tool_name: 'brave_web_search',
  ai_signal_analysis_mcp_source_primary_env_json: '{"BRAVE_API_KEY":""}',
  ai_signal_analysis_mcp_source_secondary_enabled: false,
  ai_signal_analysis_mcp_source_secondary_name: 'exa',
  ai_signal_analysis_mcp_source_secondary_command: 'npx',
  ai_signal_analysis_mcp_source_secondary_args: '-y exa-mcp-server',
  ai_signal_analysis_mcp_source_secondary_tool_name: 'web_search_exa',
  ai_signal_analysis_mcp_source_secondary_env_json: '{"EXA_API_KEY":""}',
  enable_ai_signal_analysis_service: false,
  ai_signal_analysis_interval_hours: 1,
  ai_signal_analysis_lookback_hours: 24,
  ai_key_levels_api_key: '',
  ai_key_levels_api_url: '',
  ai_key_levels_api_protocol: 'auto',
  ai_key_levels_model: '',
  enable_ai_key_levels_service: false,
  ai_overlays_api_key: '',
  ai_overlays_api_url: '',
  ai_overlays_api_protocol: 'auto',
  ai_overlays_model: '',
  enable_ai_overlays_service: false,
  ai_market_analysis_api_key: '',
  ai_market_analysis_api_url: '',
  ai_market_analysis_api_protocol: 'auto',
  ai_market_analysis_model: '',
  enable_ai_market_analysis: false,
  ai_market_analysis_interval_hours: 1,
  ai_market_analysis_lookback_hours: 24,
  ai_summary_proxy: 'http://127.0.0.1:7890',
};

const SIGNAL_MONITOR_DEFAULTS: SignalMonitorConfig = {
  telegram_bot_token: '',
  telegram_chat_id: '',
  enable_telegram: true,
  send_tg_in_mode_1: true,
  language: 'zh',
  coinmarketcap_api_key: '',
  cryptocompare_api_key: '',
  coingecko_api_key: '',
  etherscan_api_key: '',
  startup_signal_max_age_seconds: 600,
  signal_max_age_seconds: 600,
  ai_signal_interval_minutes: 30,
  realtime_market_enabled: false,
  enable_ipc_forwarding: true,
  ipc_host: '127.0.0.1',
  ipc_port: 8765,
  ipc_connect_timeout: 1.5,
  ipc_retry_delay: 2.0,
  ipc_max_retries: 3,
  socks5_proxy: '',
  http_proxy: '',
  enable_pro_chart: true,
  enable_ai_key_levels: false,
  enable_ai_overlays: false,
  enable_ai_signal_analysis: true,
  ai_brief_wait_timeout_seconds: 90,
  bull_bear_signal_ttl_seconds: 86400,
  enable_tradingview_chart: true,
  chart_img_api_key: '',
  chart_img_layout_id: 'oeTZqtUR',
  chart_img_width: 800,
  chart_img_height: 600,
  chart_img_timeout: 90,
  auto_delete_charts: true,
};

const SYSTEM_DEFAULTS: SystemConfig = {
  nofx_backend_port: 8080,
  nofx_frontend_port: 3000,
  nofx_timezone: 'Asia/Shanghai',
  jwt_secret: '',
  data_encryption_key: '',
  rsa_private_key: '',
  transport_encryption: false,
};

const LOGGING_DEFAULTS: LoggingConfig = {
  log_level: 'INFO',
  log_to_file: true,
  log_file: 'signal_monitor.log',
  log_max_size: 10485760,
  log_backup_count: 5,
  log_format: '%(asctime)s [%(levelname)s] %(message)s',
  log_date_format: '%Y-%m-%d %H:%M:%S',
};

export const createDefaultAiServiceConfig = (): AIServiceConfig => ({
  ...AI_SERVICE_DEFAULTS,
});

export const createDefaultSignalMonitorConfig = (): SignalMonitorConfig => ({
  ...SIGNAL_MONITOR_DEFAULTS,
});

export const createDefaultSystemConfig = (): SystemConfig => ({
  ...SYSTEM_DEFAULTS,
});

export const createDefaultLoggingConfig = (): LoggingConfig => ({
  ...LOGGING_DEFAULTS,
});

export const createDefaultConfiguration = (): CompleteConfig => ({
  ai_service: createDefaultAiServiceConfig(),
  signal_monitor: createDefaultSignalMonitorConfig(),
  system: createDefaultSystemConfig(),
  logging: createDefaultLoggingConfig(),
  anomaly: {
    ...DEFAULT_ANOMALY_CONFIG,
    scoring_weights: { ...DEFAULT_ANOMALY_CONFIG.scoring_weights },
    scoring_thresholds: { ...DEFAULT_ANOMALY_CONFIG.scoring_thresholds },
  },
  us_market: {
    ...DEFAULT_US_MARKET_CONFIG,
    categories: { ...DEFAULT_US_MARKET_CONFIG.categories },
  },
});

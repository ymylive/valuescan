import api, { toApiError, type ApiError } from './api';
import {
  AIServiceConfig,
  SignalMonitorConfig,
  SystemConfig,
  LoggingConfig,
  EnvironmentConfig,
  CompleteConfig,
  AnomalyDetectorConfig,
  USMarketConfig,
  DEFAULT_ANOMALY_CONFIG,
  DEFAULT_US_MARKET_CONFIG,
} from '../types/config';

interface BackendConfig {
  signal?: Record<string, unknown>;
  logging?: Record<string, unknown>;
  system?: Record<string, unknown>;
  environment?: Record<string, unknown>;
  anomaly?: Record<string, unknown>;
  us_market?: Record<string, unknown>;
}

export interface SaveConfigurationResult {
  localSaved: boolean;
  backendSaved: boolean;
  backendError?: ApiError;
}

export class ConfigService {
  private readonly LOCAL_STORAGE_KEY = 'app_config';

  async loadConfiguration(): Promise<CompleteConfig> {
    try {
      const backendConfig = await api.get('/config') as BackendConfig;
      return this.normalizeConfiguration(this.transformBackendToFrontend(backendConfig));
    } catch (error) {
      console.warn('Failed to load configuration from backend, using local storage:', toApiError(error));

      const localConfig = this.loadFromLocalStorage();
      if (localConfig) {
        return this.normalizeConfiguration(localConfig);
      }

      return this.getDefaultConfiguration();
    }
  }

  async saveConfiguration(config: CompleteConfig): Promise<SaveConfigurationResult> {
    this.saveToLocalStorage(config);

    try {
      const backendConfig = this.transformFrontendToBackend(config);
      await api.post('/config', backendConfig);
      return {
        localSaved: true,
        backendSaved: true,
      };
    } catch (error) {
      const backendError = toApiError(error);
      console.warn('Failed to save configuration to backend, saved to local storage only:', backendError);
      return {
        localSaved: true,
        backendSaved: false,
        backendError,
      };
    }
  }

  private loadFromLocalStorage(): CompleteConfig | null {
    try {
      const stored = localStorage.getItem(this.LOCAL_STORAGE_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch (error) {
      console.error('Failed to load from local storage:', error);
    }
    return null;
  }

  private saveToLocalStorage(config: CompleteConfig): void {
    try {
      localStorage.setItem(this.LOCAL_STORAGE_KEY, JSON.stringify(config));
    } catch (error) {
      console.error('Failed to save to local storage:', error);
    }
  }

  private normalizeConfiguration(config: Partial<CompleteConfig>): CompleteConfig {
    const defaults = this.getDefaultConfiguration();
    const anomaly = (config.anomaly || {}) as Partial<AnomalyDetectorConfig>;
    const usMarket = (config.us_market || {}) as Partial<USMarketConfig>;
    return {
      ...defaults,
      ...config,
      ai_service: { ...defaults.ai_service, ...(config.ai_service || {}) },
      signal_monitor: { ...defaults.signal_monitor, ...(config.signal_monitor || {}) },
      system: { ...defaults.system, ...(config.system || {}) },
      logging: { ...defaults.logging, ...(config.logging || {}) },
      environment: { ...defaults.environment, ...(config.environment || {}) },
      anomaly: {
        ...DEFAULT_ANOMALY_CONFIG,
        ...anomaly,
        scoring_weights: {
          ...DEFAULT_ANOMALY_CONFIG.scoring_weights,
          ...(anomaly.scoring_weights || {}),
        },
        scoring_thresholds: {
          ...DEFAULT_ANOMALY_CONFIG.scoring_thresholds,
          ...(anomaly.scoring_thresholds || {}),
        },
      },
      us_market: {
        ...DEFAULT_US_MARKET_CONFIG,
        ...usMarket,
        categories: {
          ...DEFAULT_US_MARKET_CONFIG.categories,
          ...(usMarket.categories || {}),
        },
      },
    };
  }

  private getDefaultConfiguration(): CompleteConfig {
    return {
      ai_service: {
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
      },
      signal_monitor: {
        telegram_bot_token: '',
        telegram_chat_id: '',
        enable_telegram: true,
        send_tg_in_mode_1: true,
        chrome_debug_port: 9222,
        headless_mode: false,
        api_path: 'api/account/message/getWarnMessage',
        ai_api_path: 'api/account/message/aiMessagePage',
        language: 'zh',
        coinmarketcap_api_key: '',
        cryptocompare_api_key: '',
        coingecko_api_key: '',
        etherscan_api_key: '',
        poll_interval: 10,
        request_timeout: 15,
        max_consecutive_failures: 5,
        failure_cooldown: 60,
        auto_relogin: false,
        auto_relogin_cooldown: 1800,
        startup_signal_max_age_seconds: 600,
        signal_max_age_seconds: 600,
        ai_signal_interval_minutes: 30,
        realtime_market_enabled: false,
        token_refresh_interval_hours: 0.8,
        token_refresh_safety_seconds: 300,
        login_method: 'auto',
        refresh_window_start: 0,
        refresh_window_end: 6,
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
      },
      system: {
        nofx_backend_port: 8080,
        nofx_frontend_port: 3000,
        nofx_timezone: 'Asia/Shanghai',
        jwt_secret: '',
        data_encryption_key: '',
        rsa_private_key: '',
        transport_encryption: false,
      },
      logging: {
        log_level: 'INFO',
        log_to_file: true,
        log_file: 'signal_monitor.log',
        log_max_size: 10485760,
        log_backup_count: 5,
        log_format: '%(asctime)s [%(levelname)s] %(message)s',
        log_date_format: '%Y-%m-%d %H:%M:%S',
      },
      environment: {
        valuescan_email: '',
        valuescan_password: '',
        valuescan_vps_password: '',
      },
      anomaly: {
        ...DEFAULT_ANOMALY_CONFIG,
        scoring_weights: { ...DEFAULT_ANOMALY_CONFIG.scoring_weights },
        scoring_thresholds: { ...DEFAULT_ANOMALY_CONFIG.scoring_thresholds },
      },
      us_market: {
        ...DEFAULT_US_MARKET_CONFIG,
        categories: { ...DEFAULT_US_MARKET_CONFIG.categories },
      },
    };
  }

  private transformBackendToFrontend(data: BackendConfig): CompleteConfig {
    const signal = data.signal || {};
    const logging = data.logging || {};
    const system = data.system || {};
    const environment = data.environment || {};

    const ai_service: AIServiceConfig = {
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
      ai_summary_proxy: (signal as Record<string, unknown>).ai_summary_proxy as string || 'http://127.0.0.1:7890',
    };

    const signal_monitor: SignalMonitorConfig = {
      telegram_bot_token: (signal as Record<string, unknown>).telegram_bot_token as string || '',
      telegram_chat_id: (signal as Record<string, unknown>).telegram_chat_id as string || '',
      enable_telegram: (signal as Record<string, unknown>).enable_telegram !== false,
      send_tg_in_mode_1: (signal as Record<string, unknown>).send_tg_in_mode_1 !== false,
      chrome_debug_port: (signal as Record<string, unknown>).chrome_debug_port as number || 9222,
      headless_mode: (signal as Record<string, unknown>).headless_mode as boolean || false,
      api_path: (signal as Record<string, unknown>).api_path as string || 'api/account/message/getWarnMessage',
      ai_api_path: (signal as Record<string, unknown>).ai_api_path as string || 'api/account/message/aiMessagePage',
      language: (signal as Record<string, unknown>).language as string || 'zh',
      coinmarketcap_api_key: (signal as Record<string, unknown>).coinmarketcap_api_key as string || '',
      cryptocompare_api_key: (signal as Record<string, unknown>).cryptocompare_api_key as string || '',
      coingecko_api_key: (signal as Record<string, unknown>).coingecko_api_key as string || '',
      etherscan_api_key: (signal as Record<string, unknown>).etherscan_api_key as string || '',
      poll_interval: (signal as Record<string, unknown>).poll_interval as number || 10,
      request_timeout: (signal as Record<string, unknown>).request_timeout as number || 15,
      max_consecutive_failures: (signal as Record<string, unknown>).max_consecutive_failures as number || 5,
      failure_cooldown: (signal as Record<string, unknown>).failure_cooldown as number || 60,
      auto_relogin: (signal as Record<string, unknown>).auto_relogin as boolean || false,
      auto_relogin_cooldown: (signal as Record<string, unknown>).auto_relogin_cooldown as number || 1800,
      startup_signal_max_age_seconds: (signal as Record<string, unknown>).startup_signal_max_age_seconds as number || 600,
      signal_max_age_seconds: (signal as Record<string, unknown>).signal_max_age_seconds as number || 600,
      ai_signal_interval_minutes: (signal as Record<string, unknown>).ai_signal_interval_minutes as number || 30,
      realtime_market_enabled: (signal as Record<string, unknown>).realtime_market_enabled === true,
      token_refresh_interval_hours: (signal as Record<string, unknown>).token_refresh_interval_hours as number || 0.8,
      token_refresh_safety_seconds: (signal as Record<string, unknown>).token_refresh_safety_seconds as number || 300,
      login_method: (signal as Record<string, unknown>).login_method as string || 'auto',
      refresh_window_start: (signal as Record<string, unknown>).refresh_window_start as number || 0,
      refresh_window_end: (signal as Record<string, unknown>).refresh_window_end as number || 6,
      enable_ipc_forwarding: (signal as Record<string, unknown>).enable_ipc_forwarding !== false,
      ipc_host: (signal as Record<string, unknown>).ipc_host as string || '127.0.0.1',
      ipc_port: (signal as Record<string, unknown>).ipc_port as number || 8765,
      ipc_connect_timeout: (signal as Record<string, unknown>).ipc_connect_timeout as number || 1.5,
      ipc_retry_delay: (signal as Record<string, unknown>).ipc_retry_delay as number || 2.0,
      ipc_max_retries: (signal as Record<string, unknown>).ipc_max_retries as number || 3,
      socks5_proxy: (signal as Record<string, unknown>).socks5_proxy as string || '',
      http_proxy: (signal as Record<string, unknown>).http_proxy as string || '',
      enable_pro_chart: (signal as Record<string, unknown>).enable_pro_chart !== false,
      enable_ai_key_levels: (signal as Record<string, unknown>).enable_ai_key_levels as boolean || false,
      enable_ai_overlays: (signal as Record<string, unknown>).enable_ai_overlays as boolean || false,
      enable_ai_signal_analysis: (signal as Record<string, unknown>).enable_ai_signal_analysis !== false,
      ai_brief_wait_timeout_seconds: (signal as Record<string, unknown>).ai_brief_wait_timeout_seconds as number || 90,
      bull_bear_signal_ttl_seconds: (signal as Record<string, unknown>).bull_bear_signal_ttl_seconds as number || 86400,
      enable_tradingview_chart: (signal as Record<string, unknown>).enable_tradingview_chart !== false,
      chart_img_api_key: (signal as Record<string, unknown>).chart_img_api_key as string || '',
      chart_img_layout_id: (signal as Record<string, unknown>).chart_img_layout_id as string || 'oeTZqtUR',
      chart_img_width: (signal as Record<string, unknown>).chart_img_width as number || 800,
      chart_img_height: (signal as Record<string, unknown>).chart_img_height as number || 600,
      chart_img_timeout: (signal as Record<string, unknown>).chart_img_timeout as number || 90,
      auto_delete_charts: (signal as Record<string, unknown>).auto_delete_charts !== false,
    };

    const system_config: SystemConfig = {
      nofx_backend_port: (system as Record<string, unknown>).nofx_backend_port as number || 8080,
      nofx_frontend_port: (system as Record<string, unknown>).nofx_frontend_port as number || 3000,
      nofx_timezone: (system as Record<string, unknown>).nofx_timezone as string || 'Asia/Shanghai',
      jwt_secret: (system as Record<string, unknown>).jwt_secret as string || '',
      data_encryption_key: (system as Record<string, unknown>).data_encryption_key as string || '',
      rsa_private_key: (system as Record<string, unknown>).rsa_private_key as string || '',
      transport_encryption: (system as Record<string, unknown>).transport_encryption as boolean || false,
    };

    const logging_config: LoggingConfig = {
      log_level: (logging as Record<string, unknown>).log_level as string
        || (signal as Record<string, unknown>).log_level as string
        || 'INFO',
      log_to_file: (logging as Record<string, unknown>).log_to_file as boolean
        ?? (signal as Record<string, unknown>).log_to_file as boolean
        ?? true,
      log_file: (logging as Record<string, unknown>).log_file as string
        || (signal as Record<string, unknown>).log_file as string
        || 'signal_monitor.log',
      log_max_size: (logging as Record<string, unknown>).log_max_size as number
        || (signal as Record<string, unknown>).log_max_size as number
        || 10485760,
      log_backup_count: (logging as Record<string, unknown>).log_backup_count as number
        || (signal as Record<string, unknown>).log_backup_count as number
        || 5,
      log_format: (logging as Record<string, unknown>).log_format as string
        || (signal as Record<string, unknown>).log_format as string
        || '%(asctime)s [%(levelname)s] %(message)s',
      log_date_format: (logging as Record<string, unknown>).log_date_format as string
        || (signal as Record<string, unknown>).log_date_format as string
        || '%Y-%m-%d %H:%M:%S',
    };

    const environment_config: EnvironmentConfig = {
      valuescan_email: (environment as Record<string, unknown>).valuescan_email as string || '',
      valuescan_password: (environment as Record<string, unknown>).valuescan_password as string || '',
      valuescan_vps_password: (environment as Record<string, unknown>).valuescan_vps_password as string || '',
    };

    const anomaly_raw = (data.anomaly || {}) as Record<string, unknown>;
    const anomaly_config: AnomalyDetectorConfig = {
      ...DEFAULT_ANOMALY_CONFIG,
      ...anomaly_raw,
      symbols: Array.isArray(anomaly_raw.symbols) ? anomaly_raw.symbols as string[] : DEFAULT_ANOMALY_CONFIG.symbols,
      scoring_weights: {
        ...DEFAULT_ANOMALY_CONFIG.scoring_weights,
        ...(anomaly_raw.scoring_weights as Record<string, number> | undefined),
      },
      scoring_thresholds: {
        ...DEFAULT_ANOMALY_CONFIG.scoring_thresholds,
        ...(anomaly_raw.scoring_thresholds as Record<string, number> | undefined),
      },
    };

    const us_market_raw = (data.us_market || {}) as Record<string, unknown>;
    const us_market_config: USMarketConfig = {
      ...DEFAULT_US_MARKET_CONFIG,
      ...us_market_raw,
      categories: {
        ...DEFAULT_US_MARKET_CONFIG.categories,
        ...(us_market_raw.categories as Record<string, string[]> | undefined),
      },
    };

    return {
      ai_service,
      signal_monitor,
      system: system_config,
      logging: logging_config,
      environment: environment_config,
      anomaly: anomaly_config,
      us_market: us_market_config,
    };
  }

  private transformFrontendToBackend(config: CompleteConfig): BackendConfig {
    const { ai_service, signal_monitor, logging, system, environment, anomaly, us_market } = config;
    const signal = {
      ...this.signalMonitorToBackend(signal_monitor),
      ai_summary_proxy: ai_service.ai_summary_proxy,
    };

    return {
      signal,
      logging: {
        log_level: logging.log_level,
        log_to_file: logging.log_to_file,
        log_file: logging.log_file,
        log_max_size: logging.log_max_size,
        log_backup_count: logging.log_backup_count,
        log_format: logging.log_format,
        log_date_format: logging.log_date_format,
      },
      system: {
        nofx_backend_port: system.nofx_backend_port,
        nofx_frontend_port: system.nofx_frontend_port,
        nofx_timezone: system.nofx_timezone,
        jwt_secret: system.jwt_secret,
        data_encryption_key: system.data_encryption_key,
        rsa_private_key: system.rsa_private_key,
        transport_encryption: system.transport_encryption,
      },
      environment: {
        valuescan_email: environment.valuescan_email,
        valuescan_password: environment.valuescan_password,
        valuescan_vps_password: environment.valuescan_vps_password,
      },
      anomaly: anomaly as unknown as Record<string, unknown>,
      us_market: us_market as unknown as Record<string, unknown>,
    };
  }

  private signalMonitorToBackend(config: SignalMonitorConfig): Record<string, unknown> {
    return {
      telegram_bot_token: config.telegram_bot_token,
      telegram_chat_id: config.telegram_chat_id,
      enable_telegram: config.enable_telegram,
      send_tg_in_mode_1: config.send_tg_in_mode_1,
      chrome_debug_port: config.chrome_debug_port,
      headless_mode: config.headless_mode,
      api_path: config.api_path,
      ai_api_path: config.ai_api_path,
      language: config.language,
      coinmarketcap_api_key: config.coinmarketcap_api_key,
      cryptocompare_api_key: config.cryptocompare_api_key,
      coingecko_api_key: config.coingecko_api_key,
      etherscan_api_key: config.etherscan_api_key,
      poll_interval: config.poll_interval,
      request_timeout: config.request_timeout,
      max_consecutive_failures: config.max_consecutive_failures,
      failure_cooldown: config.failure_cooldown,
      auto_relogin: config.auto_relogin,
      auto_relogin_cooldown: config.auto_relogin_cooldown,
      startup_signal_max_age_seconds: config.startup_signal_max_age_seconds,
      signal_max_age_seconds: config.signal_max_age_seconds,
      ai_signal_interval_minutes: config.ai_signal_interval_minutes,
      realtime_market_enabled: config.realtime_market_enabled,
      token_refresh_interval_hours: config.token_refresh_interval_hours,
      token_refresh_safety_seconds: config.token_refresh_safety_seconds,
      login_method: config.login_method,
      refresh_window_start: config.refresh_window_start,
      refresh_window_end: config.refresh_window_end,
      enable_ipc_forwarding: config.enable_ipc_forwarding,
      ipc_host: config.ipc_host,
      ipc_port: config.ipc_port,
      ipc_connect_timeout: config.ipc_connect_timeout,
      ipc_retry_delay: config.ipc_retry_delay,
      ipc_max_retries: config.ipc_max_retries,
      socks5_proxy: config.socks5_proxy,
      http_proxy: config.http_proxy,
      enable_pro_chart: config.enable_pro_chart,
      enable_ai_key_levels: config.enable_ai_key_levels,
      enable_ai_overlays: config.enable_ai_overlays,
      enable_ai_signal_analysis: config.enable_ai_signal_analysis,
      ai_brief_wait_timeout_seconds: config.ai_brief_wait_timeout_seconds,
      bull_bear_signal_ttl_seconds: config.bull_bear_signal_ttl_seconds,
      enable_tradingview_chart: config.enable_tradingview_chart,
      chart_img_api_key: config.chart_img_api_key,
      chart_img_layout_id: config.chart_img_layout_id,
      chart_img_width: config.chart_img_width,
      chart_img_height: config.chart_img_height,
      chart_img_timeout: config.chart_img_timeout,
      auto_delete_charts: config.auto_delete_charts,
    };
  }

  exportConfiguration(config: CompleteConfig): void {
    const dataStr = JSON.stringify(config, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `config-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  async importConfiguration(file: File): Promise<CompleteConfig> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const config = JSON.parse(e.target?.result as string);
          resolve(this.normalizeConfiguration(config));
        } catch {
          reject(new Error('Invalid configuration file'));
        }
      };
      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsText(file);
    });
  }
}

export const configService = new ConfigService();

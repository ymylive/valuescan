import api, { toApiError, type ApiError } from './api';
import {
  AIServiceConfig,
  SignalMonitorConfig,
  SystemConfig,
  LoggingConfig,
  CompleteConfig,
  AnomalyDetectorConfig,
  USMarketConfig,
  DEFAULT_ANOMALY_CONFIG,
  DEFAULT_US_MARKET_CONFIG,
} from '../types/config';
import {
  createDefaultAiServiceConfig,
  createDefaultConfiguration,
  createDefaultLoggingConfig,
  createDefaultSignalMonitorConfig,
  createDefaultSystemConfig,
} from './configDefaults';

interface BackendConfig {
  signal?: Record<string, unknown>;
  logging?: Record<string, unknown>;
  system?: Record<string, unknown>;
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
    return createDefaultConfiguration();
  }

  private transformBackendToFrontend(data: BackendConfig): CompleteConfig {
    const signal = data.signal || {};
    const logging = data.logging || {};
    const system = data.system || {};
    const aiDefaults = createDefaultAiServiceConfig();
    const signalDefaults = createDefaultSignalMonitorConfig();
    const systemDefaults = createDefaultSystemConfig();
    const loggingDefaults = createDefaultLoggingConfig();

    const ai_service: AIServiceConfig = {
      ...aiDefaults,
      ai_summary_proxy: (signal as Record<string, unknown>).ai_summary_proxy as string || aiDefaults.ai_summary_proxy,
    };

    const signal_monitor: SignalMonitorConfig = {
      telegram_bot_token: (signal as Record<string, unknown>).telegram_bot_token as string || signalDefaults.telegram_bot_token,
      telegram_chat_id: (signal as Record<string, unknown>).telegram_chat_id as string || signalDefaults.telegram_chat_id,
      enable_telegram: (signal as Record<string, unknown>).enable_telegram !== false,
      send_tg_in_mode_1: (signal as Record<string, unknown>).send_tg_in_mode_1 !== false,
      language: (signal as Record<string, unknown>).language as string || signalDefaults.language,
      coinmarketcap_api_key: (signal as Record<string, unknown>).coinmarketcap_api_key as string || signalDefaults.coinmarketcap_api_key,
      cryptocompare_api_key: (signal as Record<string, unknown>).cryptocompare_api_key as string || signalDefaults.cryptocompare_api_key,
      coingecko_api_key: (signal as Record<string, unknown>).coingecko_api_key as string || signalDefaults.coingecko_api_key,
      etherscan_api_key: (signal as Record<string, unknown>).etherscan_api_key as string || signalDefaults.etherscan_api_key,
      startup_signal_max_age_seconds: (signal as Record<string, unknown>).startup_signal_max_age_seconds as number || signalDefaults.startup_signal_max_age_seconds,
      signal_max_age_seconds: (signal as Record<string, unknown>).signal_max_age_seconds as number || signalDefaults.signal_max_age_seconds,
      ai_signal_interval_minutes: (signal as Record<string, unknown>).ai_signal_interval_minutes as number || signalDefaults.ai_signal_interval_minutes,
      realtime_market_enabled: (signal as Record<string, unknown>).realtime_market_enabled === true,
      enable_ipc_forwarding: (signal as Record<string, unknown>).enable_ipc_forwarding !== false,
      ipc_host: (signal as Record<string, unknown>).ipc_host as string || signalDefaults.ipc_host,
      ipc_port: (signal as Record<string, unknown>).ipc_port as number || signalDefaults.ipc_port,
      ipc_connect_timeout: (signal as Record<string, unknown>).ipc_connect_timeout as number || signalDefaults.ipc_connect_timeout,
      ipc_retry_delay: (signal as Record<string, unknown>).ipc_retry_delay as number || signalDefaults.ipc_retry_delay,
      ipc_max_retries: (signal as Record<string, unknown>).ipc_max_retries as number || signalDefaults.ipc_max_retries,
      socks5_proxy: (signal as Record<string, unknown>).socks5_proxy as string || signalDefaults.socks5_proxy,
      http_proxy: (signal as Record<string, unknown>).http_proxy as string || signalDefaults.http_proxy,
      enable_pro_chart: (signal as Record<string, unknown>).enable_pro_chart !== false,
      enable_ai_key_levels: (signal as Record<string, unknown>).enable_ai_key_levels as boolean || signalDefaults.enable_ai_key_levels,
      enable_ai_overlays: (signal as Record<string, unknown>).enable_ai_overlays as boolean || signalDefaults.enable_ai_overlays,
      enable_ai_signal_analysis: (signal as Record<string, unknown>).enable_ai_signal_analysis !== false,
      ai_brief_wait_timeout_seconds: (signal as Record<string, unknown>).ai_brief_wait_timeout_seconds as number || signalDefaults.ai_brief_wait_timeout_seconds,
      bull_bear_signal_ttl_seconds: (signal as Record<string, unknown>).bull_bear_signal_ttl_seconds as number || signalDefaults.bull_bear_signal_ttl_seconds,
      enable_tradingview_chart: (signal as Record<string, unknown>).enable_tradingview_chart !== false,
      chart_img_api_key: (signal as Record<string, unknown>).chart_img_api_key as string || signalDefaults.chart_img_api_key,
      chart_img_layout_id: (signal as Record<string, unknown>).chart_img_layout_id as string || signalDefaults.chart_img_layout_id,
      chart_img_width: (signal as Record<string, unknown>).chart_img_width as number || signalDefaults.chart_img_width,
      chart_img_height: (signal as Record<string, unknown>).chart_img_height as number || signalDefaults.chart_img_height,
      chart_img_timeout: (signal as Record<string, unknown>).chart_img_timeout as number || signalDefaults.chart_img_timeout,
      auto_delete_charts: (signal as Record<string, unknown>).auto_delete_charts !== false,
    };

    const system_config: SystemConfig = {
      nofx_backend_port: (system as Record<string, unknown>).nofx_backend_port as number || systemDefaults.nofx_backend_port,
      nofx_frontend_port: (system as Record<string, unknown>).nofx_frontend_port as number || systemDefaults.nofx_frontend_port,
      nofx_timezone: (system as Record<string, unknown>).nofx_timezone as string || systemDefaults.nofx_timezone,
      jwt_secret: (system as Record<string, unknown>).jwt_secret as string || systemDefaults.jwt_secret,
      data_encryption_key: (system as Record<string, unknown>).data_encryption_key as string || systemDefaults.data_encryption_key,
      rsa_private_key: (system as Record<string, unknown>).rsa_private_key as string || systemDefaults.rsa_private_key,
      transport_encryption: (system as Record<string, unknown>).transport_encryption as boolean || systemDefaults.transport_encryption,
    };

    const logging_config: LoggingConfig = {
      log_level: (logging as Record<string, unknown>).log_level as string
        || (signal as Record<string, unknown>).log_level as string
        || loggingDefaults.log_level,
      log_to_file: (logging as Record<string, unknown>).log_to_file as boolean
        ?? (signal as Record<string, unknown>).log_to_file as boolean
        ?? loggingDefaults.log_to_file,
      log_file: (logging as Record<string, unknown>).log_file as string
        || (signal as Record<string, unknown>).log_file as string
        || loggingDefaults.log_file,
      log_max_size: (logging as Record<string, unknown>).log_max_size as number
        || (signal as Record<string, unknown>).log_max_size as number
        || loggingDefaults.log_max_size,
      log_backup_count: (logging as Record<string, unknown>).log_backup_count as number
        || (signal as Record<string, unknown>).log_backup_count as number
        || loggingDefaults.log_backup_count,
      log_format: (logging as Record<string, unknown>).log_format as string
        || (signal as Record<string, unknown>).log_format as string
        || loggingDefaults.log_format,
      log_date_format: (logging as Record<string, unknown>).log_date_format as string
        || (signal as Record<string, unknown>).log_date_format as string
        || loggingDefaults.log_date_format,
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
      anomaly: anomaly_config,
      us_market: us_market_config,
    };
  }

  private transformFrontendToBackend(config: CompleteConfig): BackendConfig {
    const { ai_service, signal_monitor, logging, system, anomaly, us_market } = config;
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
      language: config.language,
      coinmarketcap_api_key: config.coinmarketcap_api_key,
      cryptocompare_api_key: config.cryptocompare_api_key,
      coingecko_api_key: config.coingecko_api_key,
      etherscan_api_key: config.etherscan_api_key,
      startup_signal_max_age_seconds: config.startup_signal_max_age_seconds,
      signal_max_age_seconds: config.signal_max_age_seconds,
      ai_signal_interval_minutes: config.ai_signal_interval_minutes,
      realtime_market_enabled: config.realtime_market_enabled,
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

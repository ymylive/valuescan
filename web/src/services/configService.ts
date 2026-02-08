import api, { toApiError } from './api';
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
  CONFIG_VERSION,
} from '../types/config';

/**
 * Pick fields from a raw object using a defaults template.
 * For each key in `defaults`, use the value from `source` if present and
 * of a compatible type, otherwise fall back to the default.
 */
function pickWithDefaults<T extends Record<string, unknown>>(
  source: Record<string, unknown>,
  defaults: T,
): T {
  const result = { ...defaults };
  for (const key of Object.keys(defaults) as Array<keyof T>) {
    const raw = source[key as string];
    if (raw !== undefined && raw !== null) {
      (result as Record<string, unknown>)[key as string] = raw;
    }
  }
  return result;
}

interface BackendConfig {
  signal?: Record<string, unknown>;
  logging?: Record<string, unknown>;
  system?: Record<string, unknown>;
  environment?: Record<string, unknown>;
  anomaly?: Record<string, unknown>;
  us_market?: Record<string, unknown>;
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

  async saveConfiguration(config: CompleteConfig): Promise<void> {
    this.saveToLocalStorage(config);

    try {
      const backendConfig = this.transformFrontendToBackend(config);
      await api.post('/config', backendConfig);
    } catch (error) {
      console.warn('Failed to save configuration to backend, saved to local storage only:', toApiError(error));
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
      version: config.version || CONFIG_VERSION,
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
      version: CONFIG_VERSION,
      ai_service: {
        ai_signal_analysis_api_key: '',
        ai_signal_analysis_api_url: '',
        ai_signal_analysis_api_protocol: 'auto',
        ai_signal_analysis_model: '',
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
    const defaults = this.getDefaultConfiguration();
    const signal = data.signal || {};

    // AI service config: backend doesn't store AI service fields in a separate section,
    // only ai_summary_proxy lives in signal
    const ai_service: AIServiceConfig = {
      ...defaults.ai_service,
      ai_summary_proxy: (signal as Record<string, unknown>).ai_summary_proxy as string
        || defaults.ai_service.ai_summary_proxy,
    };

    // Signal monitor: pick all fields from backend signal section, fall back to defaults
    const signal_monitor = pickWithDefaults<SignalMonitorConfig>(
      signal as Record<string, unknown>,
      defaults.signal_monitor,
    );

    // System, logging, environment: pick from their respective backend sections
    const system_config = pickWithDefaults<SystemConfig>(
      (data.system || {}) as Record<string, unknown>,
      defaults.system,
    );

    // Logging: also check signal section for legacy configs that stored logging fields there
    const loggingRaw = data.logging || {};
    const loggingMerged = { ...signal, ...loggingRaw } as Record<string, unknown>;
    const logging_config = pickWithDefaults<LoggingConfig>(
      loggingMerged,
      defaults.logging,
    );

    const environment_config = pickWithDefaults<EnvironmentConfig>(
      (data.environment || {}) as Record<string, unknown>,
      defaults.environment,
    );

    // Anomaly: deep merge scoring sub-objects
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

    // US market: deep merge categories
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
      version: CONFIG_VERSION,
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
    return {
      signal: {
        ...signal_monitor,
        ai_summary_proxy: ai_service.ai_summary_proxy,
      },
      logging: { ...logging },
      system: { ...system },
      environment: { ...environment },
      anomaly: anomaly as unknown as Record<string, unknown>,
      us_market: us_market as unknown as Record<string, unknown>,
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

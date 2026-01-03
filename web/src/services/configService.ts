import api from './api';
import {
  AIServiceConfig,
  SignalMonitorConfig,
  TradingBotConfig,
  SystemConfig,
  LoggingConfig,
  CopyTradeConfig,
  KeepaliveConfig,
  EnvironmentConfig,
  CompleteConfig,
} from '../types/config';

// Backend API response format
interface BackendConfig {
  signal: Record<string, any>;
  trader: Record<string, any>;
  copytrade?: Record<string, any>;
  beta_mode?: boolean;
  registration_enabled?: boolean;
}

interface SaveConfigResponse {
  success?: boolean;
  errors?: string[];
  validation_errors?: Record<string, string[]>;
  error?: string;
}

// Configuration adapter service
export class ConfigService {
  private readonly LOCAL_STORAGE_KEY = 'valuescan_config';

  // Load configuration from backend or local storage
  async loadConfiguration(): Promise<CompleteConfig> {
    try {
      const data = await api.get('/config') as any;
      const backendConfig = data as BackendConfig;

      return this.transformBackendToFrontend(backendConfig);
    } catch (error) {
      console.warn('Failed to load configuration from backend, using local storage:', error);

      // Try to load from local storage
      const localConfig = this.loadFromLocalStorage();
      if (localConfig) {
        return localConfig;
      }

      // Return default configuration
      return this.getDefaultConfiguration();
    }
  }

  // Save configuration to backend and local storage
  async saveConfiguration(config: CompleteConfig): Promise<void> {
    // Always save to local storage first
    this.saveToLocalStorage(config);

    try {
      const backendConfig = this.transformFrontendToBackend(config);
      const response = await api.post('/config', backendConfig) as SaveConfigResponse;
      if (response && response.success === false) {
        const detail = this.extractBackendError(response);
        throw new Error(detail || 'Backend save failed');
      }
    } catch (error) {
      const detail = this.formatSaveError(error);
      console.warn('Failed to save configuration to backend, saved to local storage only:', error);
      throw new Error(detail);
    }
  }

  // Load from local storage
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

  // Save to local storage
  private saveToLocalStorage(config: CompleteConfig): void {
    try {
      localStorage.setItem(this.LOCAL_STORAGE_KEY, JSON.stringify(config));
    } catch (error) {
      console.error('Failed to save to local storage:', error);
    }
  }

  // Get default configuration
  private getDefaultConfiguration(): CompleteConfig {
    return {
      ai_service: {
        ai_position_api_key: '',
        ai_position_api_url: '',
        ai_position_model: '',
        enable_ai_position_agent: false,
        ai_position_check_interval: 300,
        ai_evolution_api_key: '',
        ai_evolution_api_url: '',
        ai_evolution_model: '',
        enable_ai_evolution: false,
        ai_evolution_profile: 'balanced_day',
        ai_evolution_min_trades: 50,
        ai_evolution_learning_period_days: 30,
        ai_evolution_interval_hours: 24,
        enable_ai_ab_testing: true,
        ai_ab_test_ratio: 0.2,
        ai_signal_analysis_api_key: '',
        ai_signal_analysis_api_url: '',
        ai_signal_analysis_model: '',
        enable_ai_signal_analysis_service: false,
        ai_signal_analysis_interval: 3600,
        ai_signal_analysis_lookback_hours: 24,
        ai_key_levels_api_key: '',
        ai_key_levels_api_url: '',
        ai_key_levels_model: '',
        enable_ai_key_levels_service: false,
        ai_overlays_api_key: '',
        ai_overlays_api_url: '',
        ai_overlays_model: '',
        enable_ai_overlays_service: false,
        ai_market_analysis_api_key: '',
        ai_market_analysis_api_url: '',
        ai_market_analysis_model: '',
        enable_ai_market_analysis: false,
        ai_market_analysis_interval: 3600,
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
        crypto_news_api_key: '',
        poll_interval: 10,
        request_timeout: 15,
        max_consecutive_failures: 5,
        failure_cooldown: 60,
        startup_signal_max_age_seconds: 600,
        signal_max_age_seconds: 600,
        enable_ipc_forwarding: true,
        ipc_host: '127.0.0.1',
        ipc_port: 8765,
        ipc_connect_timeout: 1.5,
        ipc_retry_delay: 2.0,
        ipc_max_retries: 3,
        socks5_proxy: '',
        http_proxy: '',
        enable_pro_chart: true,
        enable_ai_key_levels: false,  // 默认关闭AI主力位
        enable_ai_overlays: false,  // 默认关闭AI覆盖层
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
        enable_valuescan_key_levels: true,  // 启用ValuScan数据
        valuescan_key_levels_as_primary: true,  // ValuScan作为主数据源
        valuescan_key_levels_days: 7,  // chart key levels days (default 7)
        valuescan_ai_analysis_days: 15,  // AI analysis key levels days
      },
      trading_bot: {
        binance_api_key: '',
        binance_api_secret: '',
        use_testnet: true,
        socks5_proxy: '',
        auto_proxy_binance: true,
        enable_proxy_fallback: true,
        symbol_suffix: 'USDT',
        leverage: 10,
        margin_type: 'ISOLATED',
        position_side: 'LONG',
        coin_blacklist: [],
        enable_ai_mode: false,
        long_trading_enabled: true,
        short_trading_enabled: false,
        short_stop_loss_percent: 2.0,
        short_take_profit_percent: 3.0,
        short_enable_pyramiding_exit: true,
        short_pyramiding_exit_levels: [[2.0, 0.5], [3.0, 0.5], [5.0, 1.0]],
        signal_time_window: 300,
        min_signal_score: 0.6,
        enable_signal_state_cache: true,
        signal_state_file: 'data/signal_state.json',
        max_processed_signal_ids: 5000,
        enable_fomo_intensify: true,
        max_position_percent: 5.0,
        max_total_position_percent: 30.0,
        major_total_position_percent: 30.0,
        alt_total_position_percent: 30.0,
        max_daily_trades: 15,
        max_daily_loss_percent: 5.0,
        stop_loss_percent: 2.0,
        take_profit_1_percent: 3.0,
        take_profit_2_percent: 6.0,
        enable_trailing_stop: true,
        trailing_stop_activation: 2.0,
        trailing_stop_callback: 1.5,
        trailing_stop_update_interval: 10,
        trailing_stop_type: 'PERCENTAGE',
        enable_pyramiding_exit: true,
        pyramiding_exit_execution: 'orders',
        pyramiding_exit_levels: [[3.0, 0.5], [5.0, 0.5], [8.0, 1.0]],
        major_coins: ['BTC', 'ETH', 'BNB', 'SOL', 'XRP'],
        enable_major_coin_strategy: true,
        major_coin_leverage: null,
        major_coin_max_position_percent: null,
        major_coin_stop_loss_percent: 1.5,
        major_coin_pyramiding_exit_levels: [[1.5, 0.3], [2.5, 0.4], [4.0, 1.0]],
        major_coin_enable_trailing_stop: true,
        major_coin_trailing_stop_activation: 1.0,
        major_coin_trailing_stop_callback: 0.8,
        auto_trading_enabled: false,
        order_type: 'MARKET',
        cancel_exit_orders_before_entry: true,
        exit_order_types_to_cancel: ['STOP_MARKET', 'TAKE_PROFIT_MARKET', 'LIMIT', 'STOP', 'TAKE_PROFIT'],
        position_precision: 3,
        position_monitor_interval: 10,
        balance_update_interval: 60,
        liquidation_warning_margin_ratio: 30.0,
        enable_telegram_alerts: true,
        enable_trade_notifications: true,
        notify_open_position: true,
        notify_close_position: true,
        notify_stop_loss: true,
        notify_take_profit: true,
        notify_partial_close: true,
        notify_errors: true,
        slippage_tolerance: 0.5,
        api_retry_count: 3,
        api_timeout: 30,
        binance_recv_window_ms: 10000,
        binance_time_sync_interval: 300,
        binance_time_sync_safety_ms: 1500,
        use_hedge_mode: false,
        max_single_trade_value: 1000.0,
        force_close_margin_ratio: 20.0,
        enable_emergency_stop: true,
        emergency_stop_file: 'STOP_TRADING',
        enable_websocket: true,
        websocket_reconnect_interval: 5,
        enable_backtest: false,
        backtest_start_date: '2024-01-01',
        backtest_end_date: '2024-12-31',
      },
      system: {
        nofx_backend_port: 8080,
        nofx_frontend_port: 3000,
        nofx_timezone: 'Asia/Shanghai',
        jwt_secret: '',
        data_encryption_key: '',
        rsa_private_key: '',
        transport_encryption: false,
        binance_socks5_proxy: '',
        binance_http_proxy: '',
        telegram_bot_token: '',
        telegram_chat_id: '',
      },
      logging: {
        log_level: 'INFO',
        log_to_file: true,
        log_file: 'valuescan.log',
        log_max_size: 10485760,
        log_backup_count: 5,
        log_format: '%(asctime)s [%(levelname)s] %(message)s',
        log_date_format: '%Y-%m-%d %H:%M:%S',
      },
      copytrade: {
        telegram_api_id: 0,
        telegram_api_hash: '',
        monitor_group_ids: [],
        signal_user_ids: [],
        copytrade_enabled: false,
        follow_close_signal: false,
        copytrade_mode: 'OPEN_ONLY',
        position_mode: 'FIXED',
        position_ratio: 1.0,
        fixed_position_size: 100,
        take_profit_3_percent: 3.0,
        min_leverage: 1,
        max_leverage: 20,
        direction_filter: 'BOTH',
        symbol_whitelist: [],
        symbol_blacklist: [],
        max_signal_delay: 300,
        notify_bot_token: '',
        notify_chat_id: '',
        notify_new_signal: false,
      },
      keepalive: {
        keepalive_config_path: 'config/keepalive.json',
        keepalive_check_interval: 60,
        keepalive_restart_delay: 5,
        keepalive_max_restarts: 3,
        keepalive_services: [],
      },
      environment: {
        valuescan_db_path: 'data/valuescan.db',
        valuescan_performance_db_path: 'data/performance.db',
        binance_default_socks5: '',
        valuescan_socks5_proxy: '',
        valuescan_proxy: '',
        valuescan_vps_password: '',
        valuescan_email: '',
        valuescan_password: '',
      },
    };
  }

  private extractBackendError(data: SaveConfigResponse): string | null {
    if (Array.isArray(data.errors) && data.errors.length > 0) {
      return data.errors.join('; ');
    }
    if (data.validation_errors && typeof data.validation_errors === 'object') {
      const messages = Object.values(data.validation_errors)
        .flat()
        .filter(Boolean);
      if (messages.length > 0) {
        return messages.join('; ');
      }
    }
    if (typeof data.error === 'string' && data.error.trim()) {
      return data.error.trim();
    }
    return null;
  }

  private formatSaveError(error: unknown): string {
    if (error && typeof error === 'object') {
      const maybeError = error as { response?: { data?: SaveConfigResponse }; message?: string };
      const data = maybeError.response?.data;
      if (data) {
        const detail = this.extractBackendError(data);
        if (detail) {
          return detail;
        }
      }
      if (maybeError.message) {
        return maybeError.message;
      }
    }
    return 'Backend save failed';
  }

  // Transform backend format to frontend format
  private transformBackendToFrontend(data: BackendConfig): CompleteConfig {
    const signal = data.signal || {};
    const trader = data.trader || {};

    // AI Service Configuration
    const ai_service: AIServiceConfig = {
      ai_position_api_key: trader.ai_position_api_key || '',
      ai_position_api_url: trader.ai_position_api_url || '',
      ai_position_model: trader.ai_position_model || '',
      enable_ai_position_agent: trader.enable_ai_position_agent || false,
      ai_position_check_interval: trader.ai_position_check_interval || 300,
      ai_evolution_api_key: trader.ai_evolution_api_key || '',
      ai_evolution_api_url: trader.ai_evolution_api_url || '',
      ai_evolution_model: trader.ai_evolution_model || '',
      enable_ai_evolution: trader.enable_ai_evolution || false,
      ai_evolution_profile: trader.ai_evolution_profile || 'balanced_day',
      ai_evolution_min_trades: trader.ai_evolution_min_trades || 50,
      ai_evolution_learning_period_days: trader.ai_evolution_learning_period_days || 30,
      ai_evolution_interval_hours: trader.ai_evolution_interval_hours || 24,
      enable_ai_ab_testing: trader.enable_ai_ab_testing !== false,
      ai_ab_test_ratio: trader.ai_ab_test_ratio || 0.2,
      ai_signal_analysis_api_key: signal.ai_signal_analysis_api_key || '',
      ai_signal_analysis_api_url: signal.ai_signal_analysis_api_url || '',
      ai_signal_analysis_model: signal.ai_signal_analysis_model || '',
      enable_ai_signal_analysis_service: signal.enable_ai_signal_analysis_service || false,
      ai_signal_analysis_interval: signal.ai_signal_analysis_interval || 3600,
      ai_signal_analysis_lookback_hours: signal.ai_signal_analysis_lookback_hours || 24,
      ai_key_levels_api_key: signal.ai_key_levels_api_key || '',
      ai_key_levels_api_url: signal.ai_key_levels_api_url || '',
      ai_key_levels_model: signal.ai_key_levels_model || '',
      enable_ai_key_levels_service: signal.enable_ai_key_levels_service || false,
      ai_overlays_api_key: signal.ai_overlays_api_key || '',
      ai_overlays_api_url: signal.ai_overlays_api_url || '',
      ai_overlays_model: signal.ai_overlays_model || '',
      enable_ai_overlays_service: signal.enable_ai_overlays_service || false,
      ai_market_analysis_api_key: signal.ai_market_analysis_api_key || '',
      ai_market_analysis_api_url: signal.ai_market_analysis_api_url || '',
      ai_market_analysis_model: signal.ai_market_analysis_model || '',
      enable_ai_market_analysis: signal.enable_ai_market_analysis || false,
      ai_market_analysis_interval: signal.ai_market_analysis_interval || 3600,
      ai_market_analysis_lookback_hours: signal.ai_market_analysis_lookback_hours || 24,
      ai_summary_proxy: signal.ai_summary_proxy || 'http://127.0.0.1:7890',
    };

    // Signal Monitor Configuration
    const signal_monitor: SignalMonitorConfig = {
      telegram_bot_token: signal.telegram_bot_token || '',
      telegram_chat_id: signal.telegram_chat_id || '',
      enable_telegram: signal.enable_telegram !== false,
      send_tg_in_mode_1: signal.send_tg_in_mode_1 !== false,
      chrome_debug_port: signal.chrome_debug_port || 9222,
      headless_mode: signal.headless_mode || false,
      api_path: signal.api_path || 'api/account/message/getWarnMessage',
      ai_api_path: signal.ai_api_path || 'api/account/message/aiMessagePage',
      language: signal.language || 'zh',
      coinmarketcap_api_key: signal.coinmarketcap_api_key || '',
      cryptocompare_api_key: signal.cryptocompare_api_key || '',
      coingecko_api_key: signal.coingecko_api_key || '',
      etherscan_api_key: signal.etherscan_api_key || '',
      crypto_news_api_key: signal.crypto_news_api_key || '',
      poll_interval: signal.poll_interval || 10,
      request_timeout: signal.request_timeout || 15,
      max_consecutive_failures: signal.max_consecutive_failures || 5,
      failure_cooldown: signal.failure_cooldown || 60,
      startup_signal_max_age_seconds: signal.startup_signal_max_age_seconds || 600,
      signal_max_age_seconds: signal.signal_max_age_seconds || 600,
      enable_ipc_forwarding: signal.enable_ipc_forwarding !== false,
      ipc_host: signal.ipc_host || '127.0.0.1',
      ipc_port: signal.ipc_port || 8765,
      ipc_connect_timeout: signal.ipc_connect_timeout || 1.5,
      ipc_retry_delay: signal.ipc_retry_delay || 2.0,
      ipc_max_retries: signal.ipc_max_retries || 3,
      socks5_proxy: signal.socks5_proxy || '',
      http_proxy: signal.http_proxy || '',
      enable_pro_chart: signal.enable_pro_chart !== false,
      enable_ai_key_levels: signal.enable_ai_key_levels || false,
      enable_ai_overlays: signal.enable_ai_overlays || false,
      enable_ai_signal_analysis: signal.enable_ai_signal_analysis !== false,
      ai_brief_wait_timeout_seconds: signal.ai_brief_wait_timeout_seconds || 90,
      bull_bear_signal_ttl_seconds: signal.bull_bear_signal_ttl_seconds || 86400,
      enable_tradingview_chart: signal.enable_tradingview_chart !== false,
      chart_img_api_key: signal.chart_img_api_key || '',
      chart_img_layout_id: signal.chart_img_layout_id || 'oeTZqtUR',
      chart_img_width: signal.chart_img_width || 800,
      chart_img_height: signal.chart_img_height || 600,
      chart_img_timeout: signal.chart_img_timeout || 90,
      auto_delete_charts: signal.auto_delete_charts !== false,
      enable_valuescan_key_levels: signal.enable_valuescan_key_levels !== false,
      valuescan_key_levels_as_primary: signal.valuescan_key_levels_as_primary !== false,  // 默认开启
      valuescan_key_levels_days: signal.valuescan_key_levels_days || 7,  // chart key levels days (default 7)
      valuescan_ai_analysis_days: signal.valuescan_ai_analysis_days || 15,  // AI analysis key levels days
    };

    // Trading Bot Configuration
    const trading_bot: TradingBotConfig = {
      binance_api_key: trader.binance_api_key || '',
      binance_api_secret: trader.binance_api_secret || '',
      use_testnet: trader.use_testnet !== false,
      socks5_proxy: trader.socks5_proxy || '',
      auto_proxy_binance: trader.auto_proxy_binance !== false,
      enable_proxy_fallback: trader.enable_proxy_fallback !== false,
      symbol_suffix: trader.symbol_suffix || 'USDT',
      leverage: trader.leverage || 10,
      margin_type: trader.margin_type || 'ISOLATED',
      position_side: trader.position_side || 'LONG',
      coin_blacklist: trader.coin_blacklist || [],
      enable_ai_mode: trader.enable_ai_mode || false,
      long_trading_enabled: trader.long_trading_enabled !== false,
      short_trading_enabled: trader.short_trading_enabled || false,
      short_stop_loss_percent: trader.short_stop_loss_percent || 2.0,
      short_take_profit_percent: trader.short_take_profit_percent || 3.0,
      short_enable_pyramiding_exit: trader.short_enable_pyramiding_exit !== false,
      short_pyramiding_exit_levels: trader.short_pyramiding_exit_levels || [[2.0, 0.5], [3.0, 0.5], [5.0, 1.0]],
      signal_time_window: trader.signal_time_window || 300,
      min_signal_score: trader.min_signal_score || 0.6,
      enable_signal_state_cache: trader.enable_signal_state_cache !== false,
      signal_state_file: trader.signal_state_file || 'data/signal_state.json',
      max_processed_signal_ids: trader.max_processed_signal_ids || 5000,
      enable_fomo_intensify: trader.enable_fomo_intensify !== false,
      max_position_percent: trader.max_position_percent || 5.0,
      max_total_position_percent: trader.max_total_position_percent || 30.0,
      major_total_position_percent: trader.major_total_position_percent || 30.0,
      alt_total_position_percent: trader.alt_total_position_percent || 30.0,
      max_daily_trades: trader.max_daily_trades || 15,
      max_daily_loss_percent: trader.max_daily_loss_percent || 5.0,
      stop_loss_percent: trader.stop_loss_percent || 2.0,
      take_profit_1_percent: trader.take_profit_1_percent || 3.0,
      take_profit_2_percent: trader.take_profit_2_percent || 6.0,
      enable_trailing_stop: trader.enable_trailing_stop !== false,
      trailing_stop_activation: trader.trailing_stop_activation || 2.0,
      trailing_stop_callback: trader.trailing_stop_callback || 1.5,
      trailing_stop_update_interval: trader.trailing_stop_update_interval || 10,
      trailing_stop_type: trader.trailing_stop_type || 'PERCENTAGE',
      enable_pyramiding_exit: trader.enable_pyramiding_exit !== false,
      pyramiding_exit_execution: trader.pyramiding_exit_execution || 'orders',
      pyramiding_exit_levels: trader.pyramiding_exit_levels || [[3.0, 0.5], [5.0, 0.5], [8.0, 1.0]],
      major_coins: trader.major_coins || ['BTC', 'ETH', 'BNB', 'SOL', 'XRP'],
      enable_major_coin_strategy: trader.enable_major_coin_strategy !== false,
      major_coin_leverage: trader.major_coin_leverage || null,
      major_coin_max_position_percent: trader.major_coin_max_position_percent || null,
      major_coin_stop_loss_percent: trader.major_coin_stop_loss_percent || 1.5,
      major_coin_pyramiding_exit_levels: trader.major_coin_pyramiding_exit_levels || [[1.5, 0.3], [2.5, 0.4], [4.0, 1.0]],
      major_coin_enable_trailing_stop: trader.major_coin_enable_trailing_stop !== false,
      major_coin_trailing_stop_activation: trader.major_coin_trailing_stop_activation || 1.0,
      major_coin_trailing_stop_callback: trader.major_coin_trailing_stop_callback || 0.8,
      auto_trading_enabled: trader.auto_trading_enabled || false,
      order_type: trader.order_type || 'MARKET',
      cancel_exit_orders_before_entry: trader.cancel_exit_orders_before_entry !== false,
      exit_order_types_to_cancel: trader.exit_order_types_to_cancel || ['STOP_MARKET', 'TAKE_PROFIT_MARKET', 'LIMIT', 'STOP', 'TAKE_PROFIT'],
      position_precision: trader.position_precision || 3,
      position_monitor_interval: trader.position_monitor_interval || 10,
      balance_update_interval: trader.balance_update_interval || 60,
      liquidation_warning_margin_ratio: trader.liquidation_warning_margin_ratio || 30.0,
      enable_telegram_alerts: trader.enable_telegram_alerts !== false,
      enable_trade_notifications: trader.enable_trade_notifications !== false,
      notify_open_position: trader.notify_open_position !== false,
      notify_close_position: trader.notify_close_position !== false,
      notify_stop_loss: trader.notify_stop_loss !== false,
      notify_take_profit: trader.notify_take_profit !== false,
      notify_partial_close: trader.notify_partial_close !== false,
      notify_errors: trader.notify_errors !== false,
      slippage_tolerance: trader.slippage_tolerance || 0.5,
      api_retry_count: trader.api_retry_count || 3,
      api_timeout: trader.api_timeout || 30,
      binance_recv_window_ms: trader.binance_recv_window_ms || 10000,
      binance_time_sync_interval: trader.binance_time_sync_interval || 300,
      binance_time_sync_safety_ms: trader.binance_time_sync_safety_ms || 1500,
      use_hedge_mode: trader.use_hedge_mode || false,
      max_single_trade_value: trader.max_single_trade_value || 1000.0,
      force_close_margin_ratio: trader.force_close_margin_ratio || 20.0,
      enable_emergency_stop: trader.enable_emergency_stop !== false,
      emergency_stop_file: trader.emergency_stop_file || 'STOP_TRADING',
      enable_websocket: trader.enable_websocket !== false,
      websocket_reconnect_interval: trader.websocket_reconnect_interval || 5,
      enable_backtest: trader.enable_backtest || false,
      backtest_start_date: trader.backtest_start_date || '2024-01-01',
      backtest_end_date: trader.backtest_end_date || '2024-12-31',
    };

    // System Configuration (placeholder - these are typically environment variables)
    const system: SystemConfig = {
      nofx_backend_port: 8080,
      nofx_frontend_port: 3000,
      nofx_timezone: 'Asia/Shanghai',
      jwt_secret: '',
      data_encryption_key: '',
      rsa_private_key: '',
      transport_encryption: false,
      binance_socks5_proxy: trader.socks5_proxy || '',
      binance_http_proxy: '',
      telegram_bot_token: signal.telegram_bot_token || '',
      telegram_chat_id: signal.telegram_chat_id || '',
    };

    // Logging Configuration
    const logging: LoggingConfig = {
      log_level: signal.log_level || 'INFO',
      log_to_file: signal.log_to_file !== false,
      log_file: signal.log_file || 'valuescan.log',
      log_max_size: signal.log_max_size || 10485760,
      log_backup_count: signal.log_backup_count || 5,
      log_format: signal.log_format || '%(asctime)s [%(levelname)s] %(message)s',
      log_date_format: signal.log_date_format || '%Y-%m-%d %H:%M:%S',
    };

    // Copy Trade Configuration (with defaults)
    const copytrade: CopyTradeConfig = {
      telegram_api_id: 0,
      telegram_api_hash: '',
      monitor_group_ids: [],
      signal_user_ids: [],
      copytrade_enabled: false,
      follow_close_signal: false,
      copytrade_mode: 'OPEN_ONLY',
      position_mode: 'FIXED',
      position_ratio: 1.0,
      fixed_position_size: 100,
      take_profit_3_percent: 3.0,
      min_leverage: 1,
      max_leverage: 20,
      direction_filter: 'BOTH',
      symbol_whitelist: [],
      symbol_blacklist: [],
      max_signal_delay: 300,
      notify_bot_token: '',
      notify_chat_id: '',
      notify_new_signal: false,
    };

    // Keepalive Configuration (with defaults)
    const keepalive: KeepaliveConfig = {
      keepalive_config_path: 'config/keepalive.json',
      keepalive_check_interval: 60,
      keepalive_restart_delay: 5,
      keepalive_max_restarts: 3,
      keepalive_services: [],
    };

    // Environment Configuration (with defaults)
    const environment: EnvironmentConfig = {
      valuescan_db_path: 'data/valuescan.db',
      valuescan_performance_db_path: 'data/performance.db',
      binance_default_socks5: '',
      valuescan_socks5_proxy: '',
      valuescan_proxy: '',
      valuescan_vps_password: '',
      valuescan_email: '',
      valuescan_password: '',
    };

    return {
      ai_service,
      signal_monitor,
      trading_bot,
      copytrade,
      keepalive,
      system,
      logging,
      environment,
    };
  }

  // Transform frontend format to backend format
  private transformFrontendToBackend(config: CompleteConfig): BackendConfig {
    const { ai_service, signal_monitor, trading_bot, logging } = config;

    // Merge AI service config into trader
    const trader: Record<string, any> = {
      ...this.tradingBotToBackend(trading_bot),
      // AI service fields
      ai_position_api_key: ai_service.ai_position_api_key,
      ai_position_api_url: ai_service.ai_position_api_url,
      ai_position_model: ai_service.ai_position_model,
      enable_ai_position_agent: ai_service.enable_ai_position_agent,
      ai_position_check_interval: ai_service.ai_position_check_interval,
      ai_evolution_api_key: ai_service.ai_evolution_api_key,
      ai_evolution_api_url: ai_service.ai_evolution_api_url,
      ai_evolution_model: ai_service.ai_evolution_model,
      enable_ai_evolution: ai_service.enable_ai_evolution,
      ai_evolution_profile: ai_service.ai_evolution_profile,
      ai_evolution_min_trades: ai_service.ai_evolution_min_trades,
      ai_evolution_learning_period_days: ai_service.ai_evolution_learning_period_days,
      ai_evolution_interval_hours: ai_service.ai_evolution_interval_hours,
      enable_ai_ab_testing: ai_service.enable_ai_ab_testing,
      ai_ab_test_ratio: ai_service.ai_ab_test_ratio,
    };

    // Merge logging config into signal
    const signal: Record<string, any> = {
      ...this.signalMonitorToBackend(signal_monitor),
      ai_summary_proxy: ai_service.ai_summary_proxy,
      // AI Signal Analysis fields
      ai_signal_analysis_api_key: ai_service.ai_signal_analysis_api_key,
      ai_signal_analysis_api_url: ai_service.ai_signal_analysis_api_url,
      ai_signal_analysis_model: ai_service.ai_signal_analysis_model,
      enable_ai_signal_analysis_service: ai_service.enable_ai_signal_analysis_service,
      ai_signal_analysis_interval: ai_service.ai_signal_analysis_interval,
      ai_signal_analysis_lookback_hours: ai_service.ai_signal_analysis_lookback_hours,
      // AI Key Levels fields
      ai_key_levels_api_key: ai_service.ai_key_levels_api_key,
      ai_key_levels_api_url: ai_service.ai_key_levels_api_url,
      ai_key_levels_model: ai_service.ai_key_levels_model,
      enable_ai_key_levels_service: ai_service.enable_ai_key_levels_service,
      // AI Overlays fields
      ai_overlays_api_key: ai_service.ai_overlays_api_key,
      ai_overlays_api_url: ai_service.ai_overlays_api_url,
      ai_overlays_model: ai_service.ai_overlays_model,
      enable_ai_overlays_service: ai_service.enable_ai_overlays_service,
      // AI Market Analysis fields
      ai_market_analysis_api_key: ai_service.ai_market_analysis_api_key,
      ai_market_analysis_api_url: ai_service.ai_market_analysis_api_url,
      ai_market_analysis_model: ai_service.ai_market_analysis_model,
      enable_ai_market_analysis: ai_service.enable_ai_market_analysis,
      ai_market_analysis_interval: ai_service.ai_market_analysis_interval,
      ai_market_analysis_lookback_hours: ai_service.ai_market_analysis_lookback_hours,
      // Logging fields
      log_level: logging.log_level,
      log_to_file: logging.log_to_file,
      log_file: logging.log_file,
      log_max_size: logging.log_max_size,
      log_backup_count: logging.log_backup_count,
      log_format: logging.log_format,
      log_date_format: logging.log_date_format,
    };

    return {
      signal,
      trader,
    };
  }

  private signalMonitorToBackend(config: SignalMonitorConfig): Record<string, any> {
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
      crypto_news_api_key: config.crypto_news_api_key,
      poll_interval: config.poll_interval,
      request_timeout: config.request_timeout,
      max_consecutive_failures: config.max_consecutive_failures,
      failure_cooldown: config.failure_cooldown,
      startup_signal_max_age_seconds: config.startup_signal_max_age_seconds,
      signal_max_age_seconds: config.signal_max_age_seconds,
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
        valuescan_key_levels_days: config.valuescan_key_levels_days,
        valuescan_ai_analysis_days: config.valuescan_ai_analysis_days,
      };
  }

  private tradingBotToBackend(config: TradingBotConfig): Record<string, any> {
    return {
      binance_api_key: config.binance_api_key,
      binance_api_secret: config.binance_api_secret,
      use_testnet: config.use_testnet,
      socks5_proxy: config.socks5_proxy,
      auto_proxy_binance: config.auto_proxy_binance,
      enable_proxy_fallback: config.enable_proxy_fallback,
      symbol_suffix: config.symbol_suffix,
      leverage: config.leverage,
      margin_type: config.margin_type,
      position_side: config.position_side,
      coin_blacklist: config.coin_blacklist,
      enable_ai_mode: config.enable_ai_mode,
      long_trading_enabled: config.long_trading_enabled,
      short_trading_enabled: config.short_trading_enabled,
      short_stop_loss_percent: config.short_stop_loss_percent,
      short_take_profit_percent: config.short_take_profit_percent,
      short_enable_pyramiding_exit: config.short_enable_pyramiding_exit,
      short_pyramiding_exit_levels: config.short_pyramiding_exit_levels,
      signal_time_window: config.signal_time_window,
      min_signal_score: config.min_signal_score,
      enable_signal_state_cache: config.enable_signal_state_cache,
      signal_state_file: config.signal_state_file,
      max_processed_signal_ids: config.max_processed_signal_ids,
      enable_fomo_intensify: config.enable_fomo_intensify,
      max_position_percent: config.max_position_percent,
      max_total_position_percent: config.max_total_position_percent,
      major_total_position_percent: config.major_total_position_percent,
      alt_total_position_percent: config.alt_total_position_percent,
      max_daily_trades: config.max_daily_trades,
      max_daily_loss_percent: config.max_daily_loss_percent,
      stop_loss_percent: config.stop_loss_percent,
      take_profit_1_percent: config.take_profit_1_percent,
      take_profit_2_percent: config.take_profit_2_percent,
      enable_trailing_stop: config.enable_trailing_stop,
      trailing_stop_activation: config.trailing_stop_activation,
      trailing_stop_callback: config.trailing_stop_callback,
      trailing_stop_update_interval: config.trailing_stop_update_interval,
      trailing_stop_type: config.trailing_stop_type,
      enable_pyramiding_exit: config.enable_pyramiding_exit,
      pyramiding_exit_execution: config.pyramiding_exit_execution,
      pyramiding_exit_levels: config.pyramiding_exit_levels,
      major_coins: config.major_coins,
      enable_major_coin_strategy: config.enable_major_coin_strategy,
      major_coin_leverage: config.major_coin_leverage,
      major_coin_max_position_percent: config.major_coin_max_position_percent,
      major_coin_stop_loss_percent: config.major_coin_stop_loss_percent,
      major_coin_pyramiding_exit_levels: config.major_coin_pyramiding_exit_levels,
      major_coin_enable_trailing_stop: config.major_coin_enable_trailing_stop,
      major_coin_trailing_stop_activation: config.major_coin_trailing_stop_activation,
      major_coin_trailing_stop_callback: config.major_coin_trailing_stop_callback,
      auto_trading_enabled: config.auto_trading_enabled,
      order_type: config.order_type,
      cancel_exit_orders_before_entry: config.cancel_exit_orders_before_entry,
      exit_order_types_to_cancel: config.exit_order_types_to_cancel,
      position_precision: config.position_precision,
      position_monitor_interval: config.position_monitor_interval,
      balance_update_interval: config.balance_update_interval,
      liquidation_warning_margin_ratio: config.liquidation_warning_margin_ratio,
      enable_telegram_alerts: config.enable_telegram_alerts,
      enable_trade_notifications: config.enable_trade_notifications,
      notify_open_position: config.notify_open_position,
      notify_close_position: config.notify_close_position,
      notify_stop_loss: config.notify_stop_loss,
      notify_take_profit: config.notify_take_profit,
      notify_partial_close: config.notify_partial_close,
      notify_errors: config.notify_errors,
      slippage_tolerance: config.slippage_tolerance,
      api_retry_count: config.api_retry_count,
      api_timeout: config.api_timeout,
      binance_recv_window_ms: config.binance_recv_window_ms,
      binance_time_sync_interval: config.binance_time_sync_interval,
      binance_time_sync_safety_ms: config.binance_time_sync_safety_ms,
      use_hedge_mode: config.use_hedge_mode,
      max_single_trade_value: config.max_single_trade_value,
      force_close_margin_ratio: config.force_close_margin_ratio,
      enable_emergency_stop: config.enable_emergency_stop,
      emergency_stop_file: config.emergency_stop_file,
      enable_websocket: config.enable_websocket,
      websocket_reconnect_interval: config.websocket_reconnect_interval,
      enable_backtest: config.enable_backtest,
      backtest_start_date: config.backtest_start_date,
      backtest_end_date: config.backtest_end_date,
    };
  }

  // Export configuration as JSON file
  exportConfiguration(config: CompleteConfig): void {
    const dataStr = JSON.stringify(config, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `valuescan-config-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  // Import configuration from JSON file
  async importConfiguration(file: File): Promise<CompleteConfig> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const config = JSON.parse(e.target?.result as string);
          resolve(config);
        } catch (error) {
          reject(new Error('Invalid configuration file'));
        }
      };
      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsText(file);
    });
  }
}

// Export singleton instance
export const configService = new ConfigService();

import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Settings as SettingsIcon, Save, RefreshCw, Brain, Activity, Bot, Shield, Bell, Server, Download, Upload, Key } from 'lucide-react';
import { GlassCard } from '../components/Common/GlassCard';
import { Button } from '../components/Common/Button';
import { AIServiceConfigComponent } from '../components/Config/AIServiceConfig';
import { SignalMonitorConfigComponent } from '../components/Config/SignalMonitorConfig';
import { TradingBotConfigComponent } from '../components/Config/TradingBotConfig';
import { RiskManagementConfig } from '../components/Config/RiskManagementConfig';
import { NotificationConfig } from '../components/Config/NotificationConfig';
import { SystemConfigComponent } from '../components/Config/SystemConfig';
import { LoginCredentialsConfig } from '../components/Config/LoginCredentialsConfig';
import {
  AIServiceConfig,
  SignalMonitorConfig,
  TradingBotConfig,
  SystemConfig,
  LoggingConfig,
  CopyTradeConfig,
  KeepaliveConfig,
  EnvironmentConfig,
} from '../types/config';
import { configService } from '../services/configService';
import { configValidator } from '../utils/configValidation';
import { logger } from '../services/loggerService';

type ConfigTab = 'ai' | 'signal' | 'trading' | 'risk' | 'notification' | 'login' | 'system';

const ConfigurationPage: React.FC = () => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<ConfigTab>('ai');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Configuration states
  const [aiConfig, setAiConfig] = useState<AIServiceConfig>({
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
  });

  const [signalConfig, setSignalConfig] = useState<SignalMonitorConfig>({
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
    enable_valuescan_key_levels: true,
    valuescan_key_levels_as_primary: true,
    valuescan_key_levels_days: 7,
    valuescan_ai_analysis_days: 15,
  });

  const [tradingConfig, setTradingConfig] = useState<TradingBotConfig>({
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
  });

  const [systemConfig, setSystemConfig] = useState<SystemConfig>({
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
  });

  const [loggingConfig, setLoggingConfig] = useState<LoggingConfig>({
    log_level: 'INFO',
    log_to_file: true,
    log_file: 'valuescan.log',
    log_max_size: 10485760,
    log_backup_count: 5,
    log_format: '%(asctime)s [%(levelname)s] %(message)s',
    log_date_format: '%Y-%m-%d %H:%M:%S',
  });

  const [environmentConfig, setEnvironmentConfig] = useState<EnvironmentConfig>({
    valuescan_db_path: 'data/valuescan.db',
    valuescan_performance_db_path: 'data/performance.db',
    binance_default_socks5: '',
    valuescan_socks5_proxy: '',
    valuescan_proxy: '',
    valuescan_vps_password: '',
    valuescan_email: '',
    valuescan_password: '',
  });

  useEffect(() => {
    loadConfiguration();
  }, []);

  const loadConfiguration = async () => {
    setLoading(true);
    logger.info('ConfigurationPage', '开始加载配置');
    try {
      const config = await configService.loadConfiguration();

      setAiConfig(config.ai_service);
      setSignalConfig(config.signal_monitor);
      setTradingConfig(config.trading_bot);
      setSystemConfig(config.system);
      setLoggingConfig(config.logging);
      setEnvironmentConfig(config.environment);

      logger.info('ConfigurationPage', '配置加载成功');
      showMessage('success', '配置加载成功（后端未连接时使用本地存储）');
    } catch (error) {
      logger.error('ConfigurationPage', '配置加载失败', error as Error);
      console.error('Failed to load configuration:', error);
      showMessage('error', '配置加载失败');
    } finally {
      setLoading(false);
    }
  };

  const saveConfiguration = async () => {
    setSaving(true);
    try {
      // Validate configuration before saving
      const validationErrors = configValidator.validateAll(
        aiConfig,
        signalConfig,
        tradingConfig,
        systemConfig,
        loggingConfig
      );

      if (validationErrors.length > 0) {
        const errorMessages = validationErrors
          .filter(e => e.severity === 'error')
          .map(e => e.message);

        if (errorMessages.length > 0) {
          showMessage('error', `配置验证失败: ${errorMessages.join(', ')}`);
          return;
        }

        // Show warnings but allow saving
        const warningMessages = validationErrors
          .filter(e => e.severity === 'warning')
          .map(e => e.message);

        if (warningMessages.length > 0) {
          console.warn('Configuration warnings:', warningMessages);
        }
      }

      const config = {
        ai_service: aiConfig,
        signal_monitor: signalConfig,
        trading_bot: tradingConfig,
        system: systemConfig,
        logging: loggingConfig,
        copytrade: {
          telegram_api_id: 0,
          telegram_api_hash: '',
          monitor_group_ids: [],
          signal_user_ids: [],
          copytrade_enabled: false,
          follow_close_signal: false,
          copytrade_mode: 'OPEN_ONLY' as const,
          position_mode: 'FIXED' as const,
          position_ratio: 1.0,
          fixed_position_size: 100,
          take_profit_3_percent: 3.0,
          min_leverage: 1,
          max_leverage: 20,
          direction_filter: 'BOTH' as const,
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
        environment: environmentConfig,
      };

      await configService.saveConfiguration(config);
      logger.info('ConfigurationPage', '配置保存成功');
      showMessage('success', '配置保存成功');
    } catch (error) {
      logger.error('ConfigurationPage', '配置保存失败', error as Error);
      console.error('Failed to save configuration:', error);
      const errorMessage = error instanceof Error ? error.message : '后端保存失败';
      showMessage('error', `配置保存失败（已保存到本地存储）: ${errorMessage}`);
    } finally {
      setSaving(false);
    }
  };

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 3000);
  };

  const handleExportConfig = () => {
    const config = {
      ai_service: aiConfig,
      signal_monitor: signalConfig,
      trading_bot: tradingConfig,
      system: systemConfig,
      logging: loggingConfig,
      copytrade: {
        telegram_api_id: 0,
        telegram_api_hash: '',
        monitor_group_ids: [],
        signal_user_ids: [],
        copytrade_enabled: false,
        follow_close_signal: false,
        copytrade_mode: 'OPEN_ONLY' as const,
        position_mode: 'FIXED' as const,
        position_ratio: 1.0,
        fixed_position_size: 100,
        take_profit_3_percent: 3.0,
        min_leverage: 1,
        max_leverage: 20,
        direction_filter: 'BOTH' as const,
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
      environment: environmentConfig,
    };
    configService.exportConfiguration(config);
    showMessage('success', '配置已导出');
  };

  const handleImportConfig = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const config = await configService.importConfiguration(file);
      setAiConfig(config.ai_service);
      setSignalConfig(config.signal_monitor);
      setTradingConfig(config.trading_bot);
      setSystemConfig(config.system);
      setLoggingConfig(config.logging);
      setEnvironmentConfig(config.environment);
      showMessage('success', '配置已导入');
    } catch (error) {
      console.error('Failed to import configuration:', error);
      showMessage('error', '配置导入失败');
    }

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const tabs = [
    { id: 'ai' as ConfigTab, label: 'AI 服务', icon: Brain, color: 'text-purple-500' },
    { id: 'signal' as ConfigTab, label: '信号监控', icon: Activity, color: 'text-green-500' },
    { id: 'trading' as ConfigTab, label: '交易机器人', icon: Bot, color: 'text-yellow-500' },
    { id: 'risk' as ConfigTab, label: '风险管理', icon: Shield, color: 'text-red-500' },
    { id: 'notification' as ConfigTab, label: '通知设置', icon: Bell, color: 'text-blue-500' },
    { id: 'login' as ConfigTab, label: '登录凭证', icon: Key, color: 'text-indigo-500' },
    { id: 'system' as ConfigTab, label: '系统配置', icon: Server, color: 'text-cyan-500' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <SettingsIcon className="text-green-500" size={32} />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">系统配置</h2>
        </div>

        <div className="flex gap-3">
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            onChange={handleImportConfig}
            className="hidden"
          />
          <Button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-2 bg-blue-500 hover:bg-blue-600"
          >
            <Upload size={18} />
            导入配置
          </Button>
          <Button
            onClick={handleExportConfig}
            className="flex items-center gap-2 bg-purple-500 hover:bg-purple-600"
          >
            <Download size={18} />
            导出配置
          </Button>
          <Button
            onClick={loadConfiguration}
            disabled={loading}
            className="flex items-center gap-2 bg-gray-500 hover:bg-gray-600"
          >
            <RefreshCw className={loading ? 'animate-spin' : ''} size={18} />
            重新加载
          </Button>
          <Button
            onClick={saveConfiguration}
            disabled={saving}
            className="flex items-center gap-2 bg-green-500 hover:bg-green-600"
          >
            <Save size={18} />
            {saving ? '保存中...' : '保存配置'}
          </Button>
        </div>
      </div>

      {/* Message */}
      {message && (
        <div
          className={`p-4 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200'
              : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Tabs */}
      <GlassCard className="p-2">
        <div className="flex flex-wrap gap-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                  activeTab === tab.id
                    ? 'bg-white dark:bg-gray-800 shadow-md'
                    : 'hover:bg-white/50 dark:hover:bg-gray-800/50'
                }`}
              >
                <Icon className={tab.color} size={20} />
                <span className="font-medium text-gray-900 dark:text-white">{tab.label}</span>
              </button>
            );
          })}
        </div>
      </GlassCard>

      {/* Content */}
      <div className="min-h-[600px]">
        {activeTab === 'ai' && (
          <AIServiceConfigComponent config={aiConfig} onChange={setAiConfig} />
        )}
        {activeTab === 'signal' && (
          <SignalMonitorConfigComponent config={signalConfig} onChange={setSignalConfig} />
        )}
        {activeTab === 'trading' && (
          <TradingBotConfigComponent config={tradingConfig} onChange={setTradingConfig} />
        )}
        {activeTab === 'risk' && (
          <RiskManagementConfig config={tradingConfig} onChange={setTradingConfig} />
        )}
        {activeTab === 'notification' && (
          <NotificationConfig
            signalConfig={signalConfig}
            tradingConfig={tradingConfig}
            onSignalChange={setSignalConfig}
            onTradingChange={setTradingConfig}
          />
        )}
        {activeTab === 'login' && (
          <LoginCredentialsConfig
            config={environmentConfig}
            onChange={setEnvironmentConfig}
          />
        )}
        {activeTab === 'system' && (
          <SystemConfigComponent
            systemConfig={systemConfig}
            loggingConfig={loggingConfig}
            tradingConfig={tradingConfig}
            onSystemChange={setSystemConfig}
            onLoggingChange={setLoggingConfig}
            onTradingChange={setTradingConfig}
          />
        )}
      </div>
    </div>
  );
};

export default ConfigurationPage;

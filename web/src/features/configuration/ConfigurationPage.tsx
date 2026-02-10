import { useCallback, useEffect, useRef, useState } from 'react';
import { Settings, Save, RefreshCw, Brain, Activity, Bell, Server, Download, Upload, Zap, TrendingUp } from 'lucide-react';
import { PageContainer } from '../../components/layout';
import { Button } from '../../components/ui';
import { GlassCard } from '../../components/shared';
import { AIServiceConfigComponent } from '../../components/Config/AIServiceConfig';
import { SignalMonitorConfigComponent } from '../../components/Config/SignalMonitorConfig';
import { NotificationConfig } from '../../components/Config/NotificationConfig';
import { SystemConfigComponent } from '../../components/Config/SystemConfig';
import { AnomalyDetectorConfigComponent } from '../../components/Config/AnomalyDetectorConfig';
import { USMarketConfigComponent } from '../../components/Config/USMarketConfig';
import { AIServiceConfig, SignalMonitorConfig, SystemConfig, LoggingConfig, EnvironmentConfig, AnomalyDetectorConfig, USMarketConfig, DEFAULT_ANOMALY_CONFIG, DEFAULT_US_MARKET_CONFIG } from '../../types/config';
import { configService } from '../../services/configService';
import { aiConfigApi } from '../../services/aiConfigApi';
import { configValidator } from '../../utils/configValidation';
import { useToast } from '../../hooks';

type ConfigTab = 'ai' | 'signal' | 'notification' | 'system' | 'anomaly' | 'usmarket';

const defaultAiConfig: AIServiceConfig = {
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
  ai_summary_proxy: '',
};

const defaultSignalConfig: SignalMonitorConfig = {
  telegram_bot_token: '',
  telegram_chat_id: '',
  enable_telegram: true,
  send_tg_in_mode_1: true,
  chrome_debug_port: 9222,
  headless_mode: false,
  api_path: '',
  ai_api_path: '',
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
  chart_img_layout_id: '',
  chart_img_width: 800,
  chart_img_height: 600,
  chart_img_timeout: 90,
  auto_delete_charts: true,
};

const defaultSystemConfig: SystemConfig = {
  nofx_backend_port: 8080,
  nofx_frontend_port: 3000,
  nofx_timezone: 'Asia/Shanghai',
  jwt_secret: '',
  data_encryption_key: '',
  rsa_private_key: '',
  transport_encryption: false,
};

const defaultLoggingConfig: LoggingConfig = {
  log_level: 'INFO',
  log_to_file: true,
  log_file: 'signal_monitor.log',
  log_max_size: 10485760,
  log_backup_count: 5,
  log_format: '%(asctime)s [%(levelname)s] %(message)s',
  log_date_format: '%Y-%m-%d %H:%M:%S',
};

const defaultEnvConfig: EnvironmentConfig = {
  valuescan_email: '',
  valuescan_password: '',
  valuescan_vps_password: '',
};

export const ConfigurationPage = () => {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<ConfigTab>('ai');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [aiConfig, setAiConfig] = useState<AIServiceConfig>(defaultAiConfig);
  const [signalConfig, setSignalConfig] = useState<SignalMonitorConfig>(defaultSignalConfig);
  const [systemConfig, setSystemConfig] = useState<SystemConfig>(defaultSystemConfig);
  const [loggingConfig, setLoggingConfig] = useState<LoggingConfig>(defaultLoggingConfig);
  const [environmentConfig, setEnvironmentConfig] = useState<EnvironmentConfig>(defaultEnvConfig);
  const [anomalyConfig, setAnomalyConfig] = useState<AnomalyDetectorConfig>(DEFAULT_ANOMALY_CONFIG);
  const [usMarketConfig, setUsMarketConfig] = useState<USMarketConfig>(DEFAULT_US_MARKET_CONFIG);

  const loadConfiguration = useCallback(async () => {
    setLoading(true);
    try {
      const config = await configService.loadConfiguration();
      setAiConfig(config.ai_service);
      setSignalConfig(config.signal_monitor);
      setSystemConfig(config.system);
      setLoggingConfig(config.logging);
      setEnvironmentConfig(config.environment);
      setAnomalyConfig(config.anomaly);
      setUsMarketConfig(config.us_market);

      try {
        const [signalResp, levelsResp, overlaysResp, marketResp] = await Promise.all([
          aiConfigApi.getSignalConfig(),
          aiConfigApi.getLevelsConfig(),
          aiConfigApi.getOverlaysConfig(),
          aiConfigApi.getMarketConfig(),
        ]);
        const normalize = (p: any) => p?.config || p?.data?.config || p || {};
        const s = normalize(signalResp), l = normalize(levelsResp), o = normalize(overlaysResp), m = normalize(marketResp);
        setAiConfig((prev) => ({
          ...prev,
          enable_ai_signal_analysis_service: s.enabled ?? prev.enable_ai_signal_analysis_service,
          ai_signal_analysis_api_key: s.api_key ?? prev.ai_signal_analysis_api_key,
          ai_signal_analysis_api_url: s.api_url ?? prev.ai_signal_analysis_api_url,
          ai_signal_analysis_api_protocol: s.api_protocol ?? prev.ai_signal_analysis_api_protocol,
          ai_signal_analysis_model: s.model ?? prev.ai_signal_analysis_model,
          enable_ai_key_levels_service: l.enabled ?? prev.enable_ai_key_levels_service,
          ai_key_levels_api_key: l.api_key ?? prev.ai_key_levels_api_key,
          ai_key_levels_api_url: l.api_url ?? prev.ai_key_levels_api_url,
          ai_key_levels_api_protocol: l.api_protocol ?? prev.ai_key_levels_api_protocol,
          ai_key_levels_model: l.model ?? prev.ai_key_levels_model,
          enable_ai_overlays_service: o.enabled ?? prev.enable_ai_overlays_service,
          ai_overlays_api_key: o.api_key ?? prev.ai_overlays_api_key,
          ai_overlays_api_url: o.api_url ?? prev.ai_overlays_api_url,
          ai_overlays_api_protocol: o.api_protocol ?? prev.ai_overlays_api_protocol,
          ai_overlays_model: o.model ?? prev.ai_overlays_model,
          enable_ai_market_analysis: m.enabled ?? prev.enable_ai_market_analysis,
          ai_market_analysis_api_key: m.api_key ?? prev.ai_market_analysis_api_key,
          ai_market_analysis_api_url: m.api_url ?? prev.ai_market_analysis_api_url,
          ai_market_analysis_api_protocol: m.api_protocol ?? prev.ai_market_analysis_api_protocol,
          ai_market_analysis_model: m.model ?? prev.ai_market_analysis_model,
        }));
      } catch {}
      toast.success('配置加载成功');
    } catch {
      toast.error('配置加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadConfiguration(); }, [loadConfiguration]);

  const saveConfiguration = async () => {
    setSaving(true);
    try {
      const errors = configValidator.validateAll(aiConfig, signalConfig, systemConfig, loggingConfig);
      const critical = errors.filter((e) => e.severity === 'error');
      if (critical.length > 0) {
        toast.error(`配置校验失败: ${critical.map((e) => e.message).join(', ')}`);
        return;
      }
      const config = {
        ai_service: aiConfig,
        signal_monitor: signalConfig,
        system: systemConfig,
        logging: loggingConfig,
        environment: environmentConfig,
        anomaly: anomalyConfig,
        us_market: usMarketConfig,
      };
      await configService.saveConfiguration(config);
      try {
        await Promise.all([
          aiConfigApi.saveSignalConfig({
            api_url: aiConfig.ai_signal_analysis_api_url,
            api_key: aiConfig.ai_signal_analysis_api_key,
            api_protocol: aiConfig.ai_signal_analysis_api_protocol,
            model: aiConfig.ai_signal_analysis_model,
            enabled: aiConfig.enable_ai_signal_analysis_service,
            interval_hours: aiConfig.ai_signal_analysis_interval_hours,
            lookback_hours: aiConfig.ai_signal_analysis_lookback_hours,
          }),
          aiConfigApi.saveLevelsConfig({
            api_url: aiConfig.ai_key_levels_api_url,
            api_key: aiConfig.ai_key_levels_api_key,
            api_protocol: aiConfig.ai_key_levels_api_protocol,
            model: aiConfig.ai_key_levels_model,
            enabled: aiConfig.enable_ai_key_levels_service,
          }),
          aiConfigApi.saveOverlaysConfig({
            api_url: aiConfig.ai_overlays_api_url,
            api_key: aiConfig.ai_overlays_api_key,
            api_protocol: aiConfig.ai_overlays_api_protocol,
            model: aiConfig.ai_overlays_model,
            enabled: aiConfig.enable_ai_overlays_service,
          }),
          aiConfigApi.saveMarketConfig({
            api_url: aiConfig.ai_market_analysis_api_url,
            api_key: aiConfig.ai_market_analysis_api_key,
            api_protocol: aiConfig.ai_market_analysis_api_protocol,
            model: aiConfig.ai_market_analysis_model,
            enabled: aiConfig.enable_ai_market_analysis,
            interval_hours: aiConfig.ai_market_analysis_interval_hours,
            lookback_hours: aiConfig.ai_market_analysis_lookback_hours,
          }),
        ]);
      } catch {}
      toast.success('配置保存成功');
    } catch {
      toast.error('配置保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleExport = () => {
    configService.exportConfiguration({
      ai_service: aiConfig,
      signal_monitor: signalConfig,
      system: systemConfig,
      logging: loggingConfig,
      environment: environmentConfig,
      anomaly: anomalyConfig,
      us_market: usMarketConfig,
    });
    toast.success('配置已导出');
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const config = await configService.importConfiguration(file);
      setAiConfig(config.ai_service);
      setSignalConfig(config.signal_monitor);
      setSystemConfig(config.system);
      setLoggingConfig(config.logging);
      setEnvironmentConfig(config.environment);
      setAnomalyConfig(config.anomaly);
      setUsMarketConfig(config.us_market);
      toast.success('配置已导入');
    } catch {
      toast.error('配置导入失败');
    }
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const tabs = [
    { id: 'ai' as ConfigTab, label: 'AI 配置', icon: Brain },
    { id: 'signal' as ConfigTab, label: '信号配置', icon: Activity },
    { id: 'anomaly' as ConfigTab, label: '异动检测', icon: Zap },
    { id: 'usmarket' as ConfigTab, label: '美股监控', icon: TrendingUp },
    { id: 'notification' as ConfigTab, label: '通知配置', icon: Bell },
    { id: 'system' as ConfigTab, label: '系统配置', icon: Server },
  ];

  return (
    <PageContainer>
      <div className="space-y-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <Settings className="text-green-500" size={32} />
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">配置中心</h2>
          </div>
          <div className="flex gap-3 flex-wrap">
            <input ref={fileInputRef} type="file" accept=".json" onChange={handleImport} className="hidden" />
            <Button variant="secondary" onClick={() => fileInputRef.current?.click()}><Upload className="w-4 h-4 mr-2" />导入</Button>
            <Button variant="secondary" onClick={handleExport}><Download className="w-4 h-4 mr-2" />导出</Button>
            <Button variant="secondary" onClick={loadConfiguration} disabled={loading}><RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />重新加载</Button>
            <Button onClick={saveConfiguration} disabled={saving}><Save className="w-4 h-4 mr-2" />{saving ? '保存中...' : '保存配置'}</Button>
          </div>
        </div>

        <GlassCard className="p-2">
          <div className="flex flex-wrap gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${activeTab === tab.id ? 'bg-white dark:bg-gray-800 shadow-md' : 'hover:bg-white/50 dark:hover:bg-gray-800/50'}`}
              >
                <tab.icon className="w-5 h-5 text-primary-500" />
                <span className="font-medium text-gray-900 dark:text-white">{tab.label}</span>
              </button>
            ))}
          </div>
        </GlassCard>

        <div className="min-h-[600px]">
          {activeTab === 'ai' && <AIServiceConfigComponent config={aiConfig} onChange={setAiConfig} />}
          {activeTab === 'signal' && <SignalMonitorConfigComponent config={signalConfig} onChange={setSignalConfig} />}
          {activeTab === 'notification' && <NotificationConfig signalConfig={signalConfig} onSignalChange={setSignalConfig} />}
          {activeTab === 'system' && <SystemConfigComponent systemConfig={systemConfig} loggingConfig={loggingConfig} onSystemChange={setSystemConfig} onLoggingChange={setLoggingConfig} />}
          {activeTab === 'anomaly' && <AnomalyDetectorConfigComponent config={anomalyConfig} onChange={setAnomalyConfig} />}
          {activeTab === 'usmarket' && <USMarketConfigComponent config={usMarketConfig} onChange={setUsMarketConfig} />}
        </div>
      </div>
    </PageContainer>
  );
};

export default ConfigurationPage;

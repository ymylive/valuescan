import { type ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
import {
  AIProtocol,
  AIServiceConfig,
  SignalMonitorConfig,
  SystemConfig,
  LoggingConfig,
  AnomalyDetectorConfig,
  USMarketConfig,
  DEFAULT_ANOMALY_CONFIG,
  DEFAULT_US_MARKET_CONFIG,
} from '../../types/config';
import {
  createDefaultAiServiceConfig,
  createDefaultLoggingConfig,
  createDefaultSignalMonitorConfig,
  createDefaultSystemConfig,
} from '../../services/configDefaults';
import { configService } from '../../services/configService';
import { aiConfigApi } from '../../services/aiConfigApi';
import { configValidator } from '../../utils/configValidation';
import { useToastStore } from '../../stores';

type ConfigTab = 'ai' | 'signal' | 'notification' | 'system' | 'anomaly' | 'usmarket';

type ConfigState = {
  ai_service: AIServiceConfig;
  signal_monitor: SignalMonitorConfig;
  system: SystemConfig;
  logging: LoggingConfig;
  anomaly: AnomalyDetectorConfig;
  us_market: USMarketConfig;
};

type AiApiConfigPayload = {
  enabled?: boolean;
  api_key?: string;
  api_url?: string;
  api_protocol?: string;
  model?: string;
  fallbacks?: Array<{
    api_key?: string;
    api_url?: string;
    api_protocol?: string;
    model?: string;
  }>;
  mcp_search?: {
    enabled?: boolean;
    query_template?: string;
    max_results?: number;
    timeout_sec?: number;
    cache_ttl_sec?: number;
    max_prompt_chars?: number;
    max_parallel_sources?: number;
    sources?: Array<{
      enabled?: boolean;
      name?: string;
      command?: string;
      args?: string | string[];
      tool_name?: string;
      env?: Record<string, string>;
    }>;
  };
  interval_hours?: number;
  lookback_hours?: number;
};

const isRecord = (value: unknown): value is Record<string, unknown> => {
  return typeof value === 'object' && value !== null;
};

const normalizeAiApiPayload = (payload: unknown): AiApiConfigPayload => {
  if (!isRecord(payload)) {
    return {};
  }

  if (isRecord(payload.config)) {
    return payload.config as AiApiConfigPayload;
  }

  if (isRecord(payload.data) && isRecord(payload.data.config)) {
    return payload.data.config as AiApiConfigPayload;
  }

  return payload as AiApiConfigPayload;
};

const AI_PROTOCOLS = new Set<AIProtocol>(['auto', 'compatible', 'responses']);

const toAiProtocol = (value: string | undefined, fallback: AIProtocol): AIProtocol => {
  if (value && AI_PROTOCOLS.has(value as AIProtocol)) {
    return value as AIProtocol;
  }
  return fallback;
};

const normalizeArgsToString = (value: unknown): string => {
  if (Array.isArray(value)) {
    return value.map((item) => String(item)).join(' ').trim();
  }
  return typeof value === 'string' ? value : '';
};

const parseEnvJson = (raw: string): Record<string, string> => {
  const text = (raw || '').trim();
  if (!text) {
    return {};
  }
  try {
    const parsed = JSON.parse(text);
    if (!isRecord(parsed)) {
      return {};
    }
    const env: Record<string, string> = {};
    Object.entries(parsed).forEach(([key, value]) => {
      const envKey = key.trim();
      if (!envKey) {
        return;
      }
      env[envKey] = value == null ? '' : String(value);
    });
    return env;
  } catch {
    return {};
  }
};

const stringifyEnvJson = (value: unknown): string => {
  if (!isRecord(value)) {
    return '{}';
  }
  const env: Record<string, string> = {};
  Object.entries(value).forEach(([key, val]) => {
    const envKey = key.trim();
    if (!envKey) {
      return;
    }
    env[envKey] = val == null ? '' : String(val);
  });
  return JSON.stringify(env);
};

const createConfigSnapshot = (config: ConfigState): string => {
  return JSON.stringify(config);
};

const formatSyncTime = (timestamp: number | null): string => {
  if (timestamp === null) {
    return '尚未同步';
  }
  return new Date(timestamp).toLocaleString();
};

export const ConfigurationPage = () => {
  const addToast = useToastStore((state) => state.addToast);
  const toastSuccess = useCallback((message: string) => addToast('success', message), [addToast]);
  const toastError = useCallback((message: string) => addToast('error', message), [addToast]);
  const toastWarning = useCallback((message: string) => addToast('warning', message), [addToast]);
  const [activeTab, setActiveTab] = useState<ConfigTab>('ai');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [lastSyncedAt, setLastSyncedAt] = useState<number | null>(null);
  const [savedSnapshot, setSavedSnapshot] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [aiConfig, setAiConfig] = useState<AIServiceConfig>(() => createDefaultAiServiceConfig());
  const [signalConfig, setSignalConfig] = useState<SignalMonitorConfig>(() => createDefaultSignalMonitorConfig());
  const [systemConfig, setSystemConfig] = useState<SystemConfig>(() => createDefaultSystemConfig());
  const [loggingConfig, setLoggingConfig] = useState<LoggingConfig>(() => createDefaultLoggingConfig());
  const [anomalyConfig, setAnomalyConfig] = useState<AnomalyDetectorConfig>(DEFAULT_ANOMALY_CONFIG);
  const [usMarketConfig, setUsMarketConfig] = useState<USMarketConfig>(DEFAULT_US_MARKET_CONFIG);

  const currentConfig = useMemo<ConfigState>(() => {
    return {
      ai_service: aiConfig,
      signal_monitor: signalConfig,
      system: systemConfig,
      logging: loggingConfig,
      anomaly: anomalyConfig,
      us_market: usMarketConfig,
    };
  }, [aiConfig, signalConfig, systemConfig, loggingConfig, anomalyConfig, usMarketConfig]);

  const currentSnapshot = useMemo(() => {
    return createConfigSnapshot(currentConfig);
  }, [currentConfig]);

  const isDirty = savedSnapshot !== null && currentSnapshot !== savedSnapshot;

  const loadConfiguration = useCallback(async () => {
    setLoading(true);
    try {
      const config = await configService.loadConfiguration();
      let mergedAiConfig = config.ai_service;

      try {
        const [signalResp, levelsResp, overlaysResp, marketResp] = await Promise.all([
          aiConfigApi.getSignalConfig(),
          aiConfigApi.getLevelsConfig(),
          aiConfigApi.getOverlaysConfig(),
          aiConfigApi.getMarketConfig(),
        ]);

        const signalPayload = normalizeAiApiPayload(signalResp);
        const signalFallbacks = Array.isArray(signalPayload.fallbacks) ? signalPayload.fallbacks : [];
        const signalSecondary = signalFallbacks[0] ?? {};
        const signalTertiary = signalFallbacks[1] ?? {};
        const mcpSearch = isRecord(signalPayload.mcp_search) ? signalPayload.mcp_search : {};
        const mcpSources = Array.isArray(mcpSearch.sources) ? mcpSearch.sources : [];
        const mcpPrimary = isRecord(mcpSources[0]) ? mcpSources[0] : {};
        const mcpSecondary = isRecord(mcpSources[1]) ? mcpSources[1] : {};
        const levelsPayload = normalizeAiApiPayload(levelsResp);
        const overlaysPayload = normalizeAiApiPayload(overlaysResp);
        const marketPayload = normalizeAiApiPayload(marketResp);

        mergedAiConfig = {
          ...mergedAiConfig,
          enable_ai_signal_analysis_service:
            signalPayload.enabled ?? mergedAiConfig.enable_ai_signal_analysis_service,
          ai_signal_analysis_api_key: signalPayload.api_key ?? mergedAiConfig.ai_signal_analysis_api_key,
          ai_signal_analysis_api_url: signalPayload.api_url ?? mergedAiConfig.ai_signal_analysis_api_url,
          ai_signal_analysis_api_protocol:
            toAiProtocol(signalPayload.api_protocol, mergedAiConfig.ai_signal_analysis_api_protocol),
          ai_signal_analysis_model: signalPayload.model ?? mergedAiConfig.ai_signal_analysis_model,
          ai_signal_analysis_secondary_api_key:
            signalSecondary.api_key ?? mergedAiConfig.ai_signal_analysis_secondary_api_key,
          ai_signal_analysis_secondary_api_url:
            signalSecondary.api_url ?? mergedAiConfig.ai_signal_analysis_secondary_api_url,
          ai_signal_analysis_secondary_api_protocol:
            toAiProtocol(signalSecondary.api_protocol, mergedAiConfig.ai_signal_analysis_secondary_api_protocol),
          ai_signal_analysis_secondary_model:
            signalSecondary.model ?? mergedAiConfig.ai_signal_analysis_secondary_model,
          ai_signal_analysis_tertiary_api_key:
            signalTertiary.api_key ?? mergedAiConfig.ai_signal_analysis_tertiary_api_key,
          ai_signal_analysis_tertiary_api_url:
            signalTertiary.api_url ?? mergedAiConfig.ai_signal_analysis_tertiary_api_url,
          ai_signal_analysis_tertiary_api_protocol:
            toAiProtocol(signalTertiary.api_protocol, mergedAiConfig.ai_signal_analysis_tertiary_api_protocol),
          ai_signal_analysis_tertiary_model:
            signalTertiary.model ?? mergedAiConfig.ai_signal_analysis_tertiary_model,
          ai_signal_analysis_mcp_enabled:
            Boolean(mcpSearch.enabled ?? mergedAiConfig.ai_signal_analysis_mcp_enabled),
          ai_signal_analysis_mcp_query_template:
            (mcpSearch.query_template as string | undefined) ?? mergedAiConfig.ai_signal_analysis_mcp_query_template,
          ai_signal_analysis_mcp_max_results:
            (mcpSearch.max_results as number | undefined) ?? mergedAiConfig.ai_signal_analysis_mcp_max_results,
          ai_signal_analysis_mcp_timeout_sec:
            (mcpSearch.timeout_sec as number | undefined) ?? mergedAiConfig.ai_signal_analysis_mcp_timeout_sec,
          ai_signal_analysis_mcp_cache_ttl_sec:
            (mcpSearch.cache_ttl_sec as number | undefined) ?? mergedAiConfig.ai_signal_analysis_mcp_cache_ttl_sec,
          ai_signal_analysis_mcp_max_prompt_chars:
            (mcpSearch.max_prompt_chars as number | undefined) ?? mergedAiConfig.ai_signal_analysis_mcp_max_prompt_chars,
          ai_signal_analysis_mcp_source_primary_enabled:
            Boolean(mcpPrimary.enabled ?? mergedAiConfig.ai_signal_analysis_mcp_source_primary_enabled),
          ai_signal_analysis_mcp_source_primary_name:
            (mcpPrimary.name as string | undefined) ?? mergedAiConfig.ai_signal_analysis_mcp_source_primary_name,
          ai_signal_analysis_mcp_source_primary_command:
            (mcpPrimary.command as string | undefined) ?? mergedAiConfig.ai_signal_analysis_mcp_source_primary_command,
          ai_signal_analysis_mcp_source_primary_args:
            normalizeArgsToString(mcpPrimary.args) || mergedAiConfig.ai_signal_analysis_mcp_source_primary_args,
          ai_signal_analysis_mcp_source_primary_tool_name:
            (mcpPrimary.tool_name as string | undefined) ?? mergedAiConfig.ai_signal_analysis_mcp_source_primary_tool_name,
          ai_signal_analysis_mcp_source_primary_env_json:
            stringifyEnvJson(mcpPrimary.env) || mergedAiConfig.ai_signal_analysis_mcp_source_primary_env_json,
          ai_signal_analysis_mcp_source_secondary_enabled:
            Boolean(mcpSecondary.enabled ?? mergedAiConfig.ai_signal_analysis_mcp_source_secondary_enabled),
          ai_signal_analysis_mcp_source_secondary_name:
            (mcpSecondary.name as string | undefined) ?? mergedAiConfig.ai_signal_analysis_mcp_source_secondary_name,
          ai_signal_analysis_mcp_source_secondary_command:
            (mcpSecondary.command as string | undefined) ?? mergedAiConfig.ai_signal_analysis_mcp_source_secondary_command,
          ai_signal_analysis_mcp_source_secondary_args:
            normalizeArgsToString(mcpSecondary.args) || mergedAiConfig.ai_signal_analysis_mcp_source_secondary_args,
          ai_signal_analysis_mcp_source_secondary_tool_name:
            (mcpSecondary.tool_name as string | undefined) ?? mergedAiConfig.ai_signal_analysis_mcp_source_secondary_tool_name,
          ai_signal_analysis_mcp_source_secondary_env_json:
            stringifyEnvJson(mcpSecondary.env) || mergedAiConfig.ai_signal_analysis_mcp_source_secondary_env_json,
          enable_ai_key_levels_service: levelsPayload.enabled ?? mergedAiConfig.enable_ai_key_levels_service,
          ai_key_levels_api_key: levelsPayload.api_key ?? mergedAiConfig.ai_key_levels_api_key,
          ai_key_levels_api_url: levelsPayload.api_url ?? mergedAiConfig.ai_key_levels_api_url,
          ai_key_levels_api_protocol: toAiProtocol(levelsPayload.api_protocol, mergedAiConfig.ai_key_levels_api_protocol),
          ai_key_levels_model: levelsPayload.model ?? mergedAiConfig.ai_key_levels_model,
          enable_ai_overlays_service: overlaysPayload.enabled ?? mergedAiConfig.enable_ai_overlays_service,
          ai_overlays_api_key: overlaysPayload.api_key ?? mergedAiConfig.ai_overlays_api_key,
          ai_overlays_api_url: overlaysPayload.api_url ?? mergedAiConfig.ai_overlays_api_url,
          ai_overlays_api_protocol: toAiProtocol(overlaysPayload.api_protocol, mergedAiConfig.ai_overlays_api_protocol),
          ai_overlays_model: overlaysPayload.model ?? mergedAiConfig.ai_overlays_model,
          enable_ai_market_analysis: marketPayload.enabled ?? mergedAiConfig.enable_ai_market_analysis,
          ai_market_analysis_api_key: marketPayload.api_key ?? mergedAiConfig.ai_market_analysis_api_key,
          ai_market_analysis_api_url: marketPayload.api_url ?? mergedAiConfig.ai_market_analysis_api_url,
          ai_market_analysis_api_protocol:
            toAiProtocol(marketPayload.api_protocol, mergedAiConfig.ai_market_analysis_api_protocol),
          ai_market_analysis_model: marketPayload.model ?? mergedAiConfig.ai_market_analysis_model,
          ai_market_analysis_interval_hours:
            marketPayload.interval_hours ?? mergedAiConfig.ai_market_analysis_interval_hours,
          ai_market_analysis_lookback_hours:
            marketPayload.lookback_hours ?? mergedAiConfig.ai_market_analysis_lookback_hours,
        };
      } catch (error) {
        console.warn('Failed to load AI detail configuration:', error);
      }

      const loadedConfig: ConfigState = {
        ai_service: mergedAiConfig,
        signal_monitor: config.signal_monitor,
        system: config.system,
        logging: config.logging,
        anomaly: config.anomaly,
        us_market: config.us_market,
      };

      setAiConfig(loadedConfig.ai_service);
      setSignalConfig(config.signal_monitor);
      setSystemConfig(config.system);
      setLoggingConfig(config.logging);
      setAnomalyConfig(config.anomaly);
      setUsMarketConfig(config.us_market);

      setSavedSnapshot(createConfigSnapshot(loadedConfig));
      setLastSyncedAt(Date.now());
      toastSuccess('配置加载成功');
    } catch {
      toastError('配置加载失败');
    } finally {
      setLoading(false);
    }
  }, [toastError, toastSuccess]);

  useEffect(() => { loadConfiguration(); }, [loadConfiguration]);

  const saveConfiguration = async () => {
    setSaving(true);
    try {
      const errors = configValidator.validateAll(aiConfig, signalConfig, systemConfig, loggingConfig);
      const critical = errors.filter((e) => e.severity === 'error');
      if (critical.length > 0) {
        toastError(`配置校验失败: ${critical.map((e) => e.message).join(', ')}`);
        return;
      }
      const config = currentConfig;
      const baseSaveResult = await configService.saveConfiguration(config);

      let aiDetailSaved = true;
      try {
        await Promise.all([
          aiConfigApi.saveSignalConfig({
            api_url: aiConfig.ai_signal_analysis_api_url,
            api_key: aiConfig.ai_signal_analysis_api_key,
            api_protocol: aiConfig.ai_signal_analysis_api_protocol,
            model: aiConfig.ai_signal_analysis_model,
            fallbacks: [
              {
                api_url: aiConfig.ai_signal_analysis_secondary_api_url,
                api_key: aiConfig.ai_signal_analysis_secondary_api_key,
                api_protocol: aiConfig.ai_signal_analysis_secondary_api_protocol,
                model: aiConfig.ai_signal_analysis_secondary_model,
              },
              {
                api_url: aiConfig.ai_signal_analysis_tertiary_api_url,
                api_key: aiConfig.ai_signal_analysis_tertiary_api_key,
                api_protocol: aiConfig.ai_signal_analysis_tertiary_api_protocol,
                model: aiConfig.ai_signal_analysis_tertiary_model,
              },
            ],
            mcp_search: {
              enabled: aiConfig.ai_signal_analysis_mcp_enabled,
              query_template: aiConfig.ai_signal_analysis_mcp_query_template,
              max_results: aiConfig.ai_signal_analysis_mcp_max_results,
              timeout_sec: aiConfig.ai_signal_analysis_mcp_timeout_sec,
              cache_ttl_sec: aiConfig.ai_signal_analysis_mcp_cache_ttl_sec,
              max_prompt_chars: aiConfig.ai_signal_analysis_mcp_max_prompt_chars,
              max_parallel_sources: aiConfig.ai_signal_analysis_mcp_source_secondary_enabled ? 2 : 1,
              sources: [
                {
                  enabled: aiConfig.ai_signal_analysis_mcp_source_primary_enabled,
                  name: aiConfig.ai_signal_analysis_mcp_source_primary_name,
                  command: aiConfig.ai_signal_analysis_mcp_source_primary_command,
                  args: aiConfig.ai_signal_analysis_mcp_source_primary_args,
                  tool_name: aiConfig.ai_signal_analysis_mcp_source_primary_tool_name,
                  env: parseEnvJson(aiConfig.ai_signal_analysis_mcp_source_primary_env_json),
                },
                {
                  enabled: aiConfig.ai_signal_analysis_mcp_source_secondary_enabled,
                  name: aiConfig.ai_signal_analysis_mcp_source_secondary_name,
                  command: aiConfig.ai_signal_analysis_mcp_source_secondary_command,
                  args: aiConfig.ai_signal_analysis_mcp_source_secondary_args,
                  tool_name: aiConfig.ai_signal_analysis_mcp_source_secondary_tool_name,
                  env: parseEnvJson(aiConfig.ai_signal_analysis_mcp_source_secondary_env_json),
                },
              ],
            },
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
      } catch (error) {
        aiDetailSaved = false;
        console.warn('Failed to save AI detail configuration:', error);
      }

      if (baseSaveResult.backendSaved && aiDetailSaved) {
        setSavedSnapshot(createConfigSnapshot(config));
        setLastSyncedAt(Date.now());
        toastSuccess('配置保存成功');
      } else {
        const warnings: string[] = [];
        if (!baseSaveResult.backendSaved) {
          warnings.push('主配置后端同步失败（已保存到本地）');
        }
        if (!aiDetailSaved) {
          warnings.push('AI 详细配置同步失败');
        }
        toastWarning(warnings.join('；'));
      }
    } catch {
      toastError('配置保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleExport = () => {
    configService.exportConfiguration(currentConfig);
    toastSuccess('配置已导出');
  };

  const handleImport = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const config = await configService.importConfiguration(file);
      setAiConfig(config.ai_service);
      setSignalConfig(config.signal_monitor);
      setSystemConfig(config.system);
      setLoggingConfig(config.logging);
      setAnomalyConfig(config.anomaly);
      setUsMarketConfig(config.us_market);
      toastSuccess('配置已导入');
    } catch {
      toastError('配置导入失败');
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

  const activeTabMeta = tabs.find((tab) => tab.id === activeTab) ?? tabs[0];
  const ActiveTabIcon = activeTabMeta.icon;

  return (
    <PageContainer>
      <div className="space-y-6">
        <GlassCard className="p-5 sm:p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <Settings className="text-green-500" size={32} />
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">配置中心</h2>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span
                  className={`inline-flex items-center rounded-full px-3 py-1 font-medium ${
                    loading
                      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                      : saving
                        ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                        : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                  }`}
                >
                  {loading ? '加载中' : saving ? '保存中' : '状态正常'}
                </span>
                <span
                  className={`inline-flex items-center rounded-full px-3 py-1 font-medium ${
                    isDirty
                      ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'
                      : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200'
                  }`}
                >
                  {isDirty ? '未保存更改' : '已同步'}
                </span>
                <span className="text-gray-600 dark:text-gray-300">最后同步: {formatSyncTime(lastSyncedAt)}</span>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <input ref={fileInputRef} type="file" accept=".json" onChange={handleImport} className="hidden" />
              <Button
                variant="secondary"
                onClick={() => fileInputRef.current?.click()}
                disabled={loading || saving}
              >
                <Upload className="w-4 h-4 mr-2" />导入
              </Button>
              <Button variant="secondary" onClick={handleExport} disabled={loading || saving}>
                <Download className="w-4 h-4 mr-2" />导出
              </Button>
              <Button variant="secondary" onClick={loadConfiguration} disabled={loading || saving}>
                <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />重新加载
              </Button>
              <Button onClick={saveConfiguration} disabled={loading || saving}>
                <Save className={`w-4 h-4 mr-2 ${saving ? 'animate-pulse' : ''}`} />
                {saving ? '保存中...' : isDirty ? '保存变更' : '保存配置'}
              </Button>
            </div>
          </div>
        </GlassCard>

        <GlassCard className="p-3">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2 px-2">
            <div className="text-sm text-gray-600 dark:text-gray-300">当前选项卡</div>
            <div className="inline-flex items-center gap-2 rounded-full bg-primary-50 px-3 py-1 text-sm font-medium text-primary-700 dark:bg-primary-900/25 dark:text-primary-300">
              <ActiveTabIcon className="h-4 w-4" />
              <span>{activeTabMeta.label}</span>
            </div>
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {tabs.map((tab) => {
              const TabIcon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`inline-flex shrink-0 items-center gap-2 rounded-lg px-4 py-2 transition-all ${
                    activeTab === tab.id
                      ? 'bg-white text-primary-600 shadow-md dark:bg-gray-800 dark:text-primary-300'
                      : 'text-gray-700 hover:bg-white/60 dark:text-gray-200 dark:hover:bg-gray-800/50'
                  }`}
                >
                  <TabIcon className="w-5 h-5" />
                  <span className="font-medium">{tab.label}</span>
                </button>
              );
            })}
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

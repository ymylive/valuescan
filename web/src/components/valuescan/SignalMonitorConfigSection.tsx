import {
  Send,
  Globe,
  Server,
  Shield,
  BarChart3,
  FileText,
  Brain,
  Activity,
  Filter,
  Key,
  Database,
} from 'lucide-react'
import type {
  SignalMonitorConfig,
  AISignalConfig,
  AILevelsConfig,
  AIOverlaysConfig,
  AIMarketConfig,
} from '../../types/config'
import { ConfigFieldGroup } from './ConfigFieldGroup'
import { SensitiveFieldInput } from './SensitiveFieldInput'
import { AIModuleConfigGroup } from './AIModuleConfigGroup'
import { api } from '../../lib/api'
import { useLanguage } from '../../contexts/LanguageContext'

interface SignalMonitorConfigSectionProps {
  config: Partial<SignalMonitorConfig>
  onChange: (config: Partial<SignalMonitorConfig>) => void
  errors?: Record<string, string>
}

const defaultAiSignalConfig: AISignalConfig = {
  enabled: true,
  api_key: 'sk-chat2api',
  api_url: 'https://chat.cornna.xyz/chatgpt/v1/chat/completions',
  model: 'gpt-5.2',
  interval_hours: 1,
  lookback_hours: 1,
}

const defaultAiLevelsConfig: AILevelsConfig = {
  enabled: true,
  api_key: 'Qq159741',
  api_url: 'https://chat.cornna.xyz/gemini/v1/chat/completions',
  model: 'gemini-3-flash-preview-search',
}

const defaultAiOverlaysConfig: AIOverlaysConfig = {
  enabled: true,
  api_key: 'Qq159741',
  api_url: 'https://chat.cornna.xyz/gemini/v1/chat/completions',
  model: 'gemini-3-flash-preview-search',
}

const defaultAiMarketConfig: AIMarketConfig = {
  enabled: true,
  api_key: 'Qq159741',
  api_url: 'https://chat.cornna.xyz/gemini/v1/chat/completions',
  model: 'gemini-3-pro-preview-search',
  interval_hours: 1,
  lookback_hours: 48,
}

function Toggle({
  checked,
  onChange,
}: {
  checked: boolean
  onChange: () => void
}) {
  return (
    <button
      type="button"
      onClick={onChange}
      className={`relative w-11 h-6 rounded-full transition-colors ${
        checked ? 'bg-white' : 'bg-neutral-700'
      }`}
    >
      <span
        className={`absolute top-1 w-4 h-4 rounded-full transition-transform ${
          checked ? 'left-6 bg-black' : 'left-1 bg-neutral-400'
        }`}
      />
    </button>
  )
}

export function SignalMonitorConfigSection({
  config,
  onChange,
  errors = {},
}: SignalMonitorConfigSectionProps) {
  const { language: uiLanguage, setLanguage, t } = useLanguage()

  const updateField = <K extends keyof SignalMonitorConfig>(
    key: K,
    value: SignalMonitorConfig[K]
  ) => {
    onChange({ ...config, [key]: value })
  }
  const updateFields = (updates: Partial<SignalMonitorConfig>) => {
    onChange({ ...config, ...updates })
  }

  const aiSignalConfig = {
    ...defaultAiSignalConfig,
    ...(config.ai_signal_config || {}),
  }
  const aiLevelsConfig = {
    ...defaultAiLevelsConfig,
    ...(config.ai_levels_config || {}),
  }
  const aiOverlaysConfig = {
    ...defaultAiOverlaysConfig,
    ...(config.ai_overlays_config || {}),
  }
  const aiMarketConfig = {
    ...defaultAiMarketConfig,
    ...(config.ai_market_config || {}),
  }

  const aiSignalEnabled =
    config.ai_signal_config?.enabled ??
    config.enable_ai_signal_analysis ??
    defaultAiSignalConfig.enabled
  const aiLevelsEnabled =
    config.ai_levels_config?.enabled ??
    config.enable_ai_key_levels ??
    defaultAiLevelsConfig.enabled
  const aiOverlaysEnabled =
    config.ai_overlays_config?.enabled ??
    config.enable_ai_overlays ??
    defaultAiOverlaysConfig.enabled

  const inputClass =
    'w-full px-3 py-2 bg-neutral-900 border border-neutral-800 rounded-lg text-sm text-white placeholder:text-neutral-600 focus:outline-none focus:border-neutral-600 transition-colors'
  const selectClass =
    'w-full px-3 py-2 bg-neutral-900 border border-neutral-800 rounded-lg text-sm text-white focus:outline-none focus:border-neutral-600 transition-colors'
  const labelClass = 'block text-sm text-neutral-400 mb-1.5'

  return (
    <div className="space-y-4">
      <ConfigFieldGroup
        title={t('language')}
        description={uiLanguage === 'zh' ? 'UI语言和AI输出语言' : 'UI language and AI output language'}
        icon={<Globe className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div>
          <label className={labelClass}>{t('language')}</label>
          <select
            value={config.language || uiLanguage || 'zh'}
            onChange={(e) => {
              const next = (e.target.value as 'zh' | 'en') || 'zh'
              updateField('language', next)
              setLanguage(next)
            }}
            className={selectClass}
          >
            <option value="zh">中文 (Chinese)</option>
            <option value="en">English</option>
          </select>
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title={t('telegramConfig')}
        description={t('telegramConfigDesc')}
        icon={<Send className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">
              {t('enableTelegram')}
            </label>
            <Toggle
              checked={!!config.enable_telegram}
              onChange={() =>
                updateField('enable_telegram', !config.enable_telegram)
              }
            />
          </div>
          <SensitiveFieldInput
            fieldKey="telegram_bot_token"
            value={config.telegram_bot_token || ''}
            onChange={(v) => updateField('telegram_bot_token', v)}
            label={t('botToken')}
            placeholder={uiLanguage === 'zh' ? '输入 Telegram Bot Token' : 'Enter Telegram Bot Token'}
          />
          {errors.telegram_bot_token && (
            <p className="text-xs text-red-400">{errors.telegram_bot_token}</p>
          )}
          <SensitiveFieldInput
            fieldKey="telegram_chat_id"
            value={config.telegram_chat_id || ''}
            onChange={(v) => updateField('telegram_chat_id', v)}
            label={t('chatId')}
            placeholder={uiLanguage === 'zh' ? '输入 Telegram Chat ID' : 'Enter Telegram Chat ID'}
          />
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">
              {uiLanguage === 'zh' ? '使用模式1发送Telegram' : 'Send Telegram in mode 1'}
            </label>
            <Toggle
              checked={!!config.send_tg_in_mode_1}
              onChange={() =>
                updateField('send_tg_in_mode_1', !config.send_tg_in_mode_1)
              }
            />
          </div>
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title={t('browserConfig')}
        description={t('browserConfigDesc')}
        icon={<Globe className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>{t('chromePort')}</label>
            <input
              type="number"
              value={config.chrome_debug_port || 9222}
              onChange={(e) =>
                updateField(
                  'chrome_debug_port',
                  parseInt(e.target.value, 10) || 9222
                )
              }
              className={inputClass}
            />
          </div>
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">{t('headlessMode')}</label>
            <Toggle
              checked={!!config.headless_mode}
              onChange={() =>
                updateField('headless_mode', !config.headless_mode)
              }
            />
          </div>
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title={t('apiConfig')}
        description={t('apiConfigDesc')}
        icon={<Server className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>{uiLanguage === 'zh' ? '信号 API 路径' : 'Signal API path'}</label>
            <input
              type="text"
              value={config.api_path || 'api/account/message/getWarnMessage'}
              onChange={(e) => updateField('api_path', e.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>AI message API path</label>
            <input
              type="text"
              value={config.ai_api_path || 'api/account/message/aiMessagePage'}
              onChange={(e) => updateField('ai_api_path', e.target.value)}
              className={inputClass}
            />
          </div>
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title={t('pollingConfig')}
        description={t('pollingConfigDesc')}
        icon={<Activity className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>{t('pollingInterval')}</label>
            <input
              type="number"
              min="1"
              max="300"
              value={config.poll_interval || 10}
              onChange={(e) =>
                updateField('poll_interval', parseInt(e.target.value, 10) || 10)
              }
              className={inputClass}
            />
          </div>

          <div>
            <label className={labelClass}>{t('requestTimeout')}</label>
            <input
              type="number"
              min="5"
              max="120"
              value={config.request_timeout || 15}
              onChange={(e) =>
                updateField(
                  'request_timeout',
                  parseInt(e.target.value, 10) || 15
                )
              }
              className={inputClass}
            />
          </div>

          <div>
            <label className={labelClass}>{t('maxConsecutiveFailures')}</label>
            <input
              type="number"
              min="1"
              max="20"
              value={config.max_consecutive_failures || 5}
              onChange={(e) =>
                updateField(
                  'max_consecutive_failures',
                  parseInt(e.target.value, 10) || 5
                )
              }
              className={inputClass}
            />
          </div>

          <div>
            <label className={labelClass}>{t('failureCooldown')}</label>
            <input
              type="number"
              min="10"
              max="600"
              value={config.failure_cooldown || 60}
              onChange={(e) =>
                updateField(
                  'failure_cooldown',
                  parseInt(e.target.value, 10) || 60
                )
              }
              className={inputClass}
            />
          </div>

          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">{t('autoRelogin')}</label>
            <Toggle
              checked={!!config.auto_relogin}
              onChange={() => updateField('auto_relogin', !config.auto_relogin)}
            />
          </div>

          {config.auto_relogin && (
            <div>
              <label className={labelClass}>{t('reloginCooldown')}</label>
              <input
                type="number"
                min="60"
                max="7200"
                value={config.auto_relogin_cooldown || 1800}
                onChange={(e) =>
                  updateField(
                    'auto_relogin_cooldown',
                    parseInt(e.target.value, 10) || 1800
                  )
                }
                className={inputClass}
              />
            </div>
          )}
        </div>
      </ConfigFieldGroup>
      <ConfigFieldGroup
        title={t('signalFilter')}
        description={t('signalFilterDesc')}
        icon={<Filter className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>{t('startupSignalMaxAge')}</label>
            <input
              type="number"
              min="60"
              max="3600"
              value={config.startup_signal_max_age_seconds || 600}
              onChange={(e) =>
                updateField(
                  'startup_signal_max_age_seconds',
                  parseInt(e.target.value, 10) || 600
                )
              }
              className={inputClass}
            />
          </div>

          <div>
            <label className={labelClass}>{t('runtimeSignalMaxAge')}</label>
            <input
              type="number"
              min="60"
              max="3600"
              value={config.signal_max_age_seconds || 600}
              onChange={(e) =>
                updateField(
                  'signal_max_age_seconds',
                  parseInt(e.target.value, 10) || 600
                )
              }
              className={inputClass}
            />
          </div>
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title={t('tokenRefresher')}
        description={t('tokenRefresherDesc')}
        icon={<Key className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>{t('tokenRefreshInterval')}</label>
            <input
              type="number"
              step="0.1"
              min="0.1"
              max="24"
              value={config.token_refresh_interval_hours || 0.8}
              onChange={(e) =>
                updateField(
                  'token_refresh_interval_hours',
                  parseFloat(e.target.value) || 0.8
                )
              }
              className={inputClass}
            />
          </div>

          <div>
            <label className={labelClass}>{t('tokenSafetyMargin')}</label>
            <input
              type="number"
              min="60"
              max="1800"
              value={config.token_refresh_safety_seconds || 300}
              onChange={(e) =>
                updateField(
                  'token_refresh_safety_seconds',
                  parseInt(e.target.value, 10) || 300
                )
              }
              className={inputClass}
            />
          </div>

          <div>
            <label className={labelClass}>{t('loginMethod')}</label>
            <select
              value={config.login_method || 'auto'}
              onChange={(e) =>
                updateField(
                  'login_method',
                  e.target.value as 'auto' | 'http' | 'cdp' | 'browser'
                )
              }
              className={selectClass}
            >
              <option value="auto">Auto</option>
              <option value="http">HTTP</option>
              <option value="cdp">CDP</option>
              <option value="browser">Browser</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>{t('refreshWindowStart')}</label>
              <input
                type="number"
                min="0"
                max="23"
                value={config.refresh_window_start || 0}
                onChange={(e) =>
                  updateField(
                    'refresh_window_start',
                    parseInt(e.target.value, 10) || 0
                  )
                }
                className={inputClass}
              />
            </div>

            <div>
              <label className={labelClass}>{t('refreshWindowEnd')}</label>
              <input
                type="number"
                min="0"
                max="23"
                value={config.refresh_window_end || 6}
                onChange={(e) =>
                  updateField(
                    'refresh_window_end',
                    parseInt(e.target.value, 10) || 6
                  )
                }
                className={inputClass}
              />
            </div>
          </div>
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title={t('ipcForwarding')}
        description={t('ipcForwardingDesc')}
        icon={<Server className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">
              {t('enableIpc')}
            </label>
            <Toggle
              checked={!!config.enable_ipc_forwarding}
              onChange={() =>
                updateField(
                  'enable_ipc_forwarding',
                  !config.enable_ipc_forwarding
                )
              }
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>{t('ipcHost')}</label>
              <input
                type="text"
                value={config.ipc_host || 'localhost'}
                onChange={(e) => updateField('ipc_host', e.target.value)}
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>{t('ipcPort')}</label>
              <input
                type="number"
                value={config.ipc_port || 9999}
                onChange={(e) =>
                  updateField('ipc_port', parseInt(e.target.value, 10) || 9999)
                }
                className={inputClass}
              />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className={labelClass}>{t('connectTimeout')}</label>
              <input
                type="number"
                step="0.1"
                value={config.ipc_connect_timeout || 1.5}
                onChange={(e) =>
                  updateField(
                    'ipc_connect_timeout',
                    parseFloat(e.target.value) || 1.5
                  )
                }
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>{t('retryDelay')}</label>
              <input
                type="number"
                step="0.1"
                value={config.ipc_retry_delay || 2}
                onChange={(e) =>
                  updateField(
                    'ipc_retry_delay',
                    parseFloat(e.target.value) || 2
                  )
                }
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>{t('maxRetries')}</label>
              <input
                type="number"
                min="0"
                value={config.ipc_max_retries || 3}
                onChange={(e) =>
                  updateField(
                    'ipc_max_retries',
                    parseInt(e.target.value, 10) || 3
                  )
                }
                className={inputClass}
              />
            </div>
          </div>
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title={t('proxyConfig')}
        description={t('proxyConfigDesc')}
        icon={<Shield className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>{t('socks5Proxy')}</label>
            <input
              type="text"
              value={config.socks5_proxy || ''}
              onChange={(e) => updateField('socks5_proxy', e.target.value)}
              placeholder="socks5://127.0.0.1:1080"
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>{t('httpProxy')}</label>
            <input
              type="text"
              value={config.http_proxy || ''}
              onChange={(e) => updateField('http_proxy', e.target.value)}
              placeholder="http://127.0.0.1:8080"
              className={inputClass}
            />
          </div>
        </div>
      </ConfigFieldGroup>
      <ConfigFieldGroup
        title={t('externalApiKeys')}
        description={t('externalApiKeysDesc')}
        icon={<Database className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
          <SensitiveFieldInput
            fieldKey="coinmarketcap_api_key"
            value={config.coinmarketcap_api_key || ''}
            onChange={(v) => updateField('coinmarketcap_api_key', v)}
            label="CoinMarketCap API Key"
            placeholder="Optional"
          />
          <SensitiveFieldInput
            fieldKey="cryptocompare_api_key"
            value={config.cryptocompare_api_key || ''}
            onChange={(v) => updateField('cryptocompare_api_key', v)}
            label="CryptoCompare API Key"
            placeholder="Optional"
          />
          <SensitiveFieldInput
            fieldKey="coingecko_api_key"
            value={config.coingecko_api_key || ''}
            onChange={(v) => updateField('coingecko_api_key', v)}
            label="CoinGecko API Key"
            placeholder="Optional"
          />
          <SensitiveFieldInput
            fieldKey="etherscan_api_key"
            value={config.etherscan_api_key || ''}
            onChange={(v) => updateField('etherscan_api_key', v)}
            label="Etherscan API Key"
            placeholder="Optional"
          />
          <SensitiveFieldInput
            fieldKey="crypto_news_api_key"
            value={config.crypto_news_api_key || ''}
            onChange={(v) => updateField('crypto_news_api_key', v)}
            label="Crypto News API Key"
            placeholder="Optional"
          />
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title={t('chartConfig')}
        description={t('chartConfigDesc')}
        icon={<BarChart3 className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">
              {t('enableProCharts')}
            </label>
            <Toggle
              checked={!!config.enable_pro_chart}
              onChange={() =>
                updateField('enable_pro_chart', !config.enable_pro_chart)
              }
            />
          </div>
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">
              {t('enableAiKeyLevels')}
            </label>
            <Toggle
              checked={aiLevelsEnabled}
              onChange={() => {
                const nextEnabled = !aiLevelsEnabled
                updateFields({
                  enable_ai_key_levels: nextEnabled,
                  ai_levels_config: {
                    ...aiLevelsConfig,
                    enabled: nextEnabled,
                  } as AILevelsConfig,
                })
              }}
            />
          </div>
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">
              {t('enableAiOverlays')}
            </label>
            <Toggle
              checked={aiOverlaysEnabled}
              onChange={() => {
                const nextEnabled = !aiOverlaysEnabled
                updateFields({
                  enable_ai_overlays: nextEnabled,
                  ai_overlays_config: {
                    ...aiOverlaysConfig,
                    enabled: nextEnabled,
                  } as AIOverlaysConfig,
                })
              }}
            />
          </div>
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">
              Enable AI signal analysis
            </label>
            <Toggle
              checked={aiSignalEnabled}
              onChange={() => {
                const nextEnabled = !aiSignalEnabled
                updateFields({
                  enable_ai_signal_analysis: nextEnabled,
                  ai_signal_config: {
                    ...aiSignalConfig,
                    enabled: nextEnabled,
                  } as AISignalConfig,
                })
              }}
            />
          </div>
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">
              Enable TradingView chart
            </label>
            <Toggle
              checked={!!config.enable_tradingview_chart}
              onChange={() =>
                updateField(
                  'enable_tradingview_chart',
                  !config.enable_tradingview_chart
                )
              }
            />
          </div>
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">
              {t('autoDeleteCharts')}
            </label>
            <Toggle
              checked={!!config.auto_delete_charts}
              onChange={() =>
                updateField('auto_delete_charts', !config.auto_delete_charts)
              }
            />
          </div>
          <SensitiveFieldInput
            fieldKey="chart_img_api_key"
            value={config.chart_img_api_key || ''}
            onChange={(v) => updateField('chart_img_api_key', v)}
            label="Chart-img API Key"
          />
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>{t('layoutId')}</label>
              <input
                type="text"
                value={config.chart_img_layout_id || ''}
                onChange={(e) =>
                  updateField('chart_img_layout_id', e.target.value)
                }
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>{t('timeout')}</label>
              <input
                type="number"
                min="30"
                max="180"
                value={config.chart_img_timeout || 90}
                onChange={(e) =>
                  updateField(
                    'chart_img_timeout',
                    parseInt(e.target.value, 10) || 90
                  )
                }
                className={inputClass}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>{t('width')}</label>
              <input
                type="number"
                value={config.chart_img_width || 800}
                onChange={(e) =>
                  updateField(
                    'chart_img_width',
                    parseInt(e.target.value, 10) || 800
                  )
                }
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>{t('height')}</label>
              <input
                type="number"
                value={config.chart_img_height || 600}
                onChange={(e) =>
                  updateField(
                    'chart_img_height',
                    parseInt(e.target.value, 10) || 600
                  )
                }
                className={inputClass}
              />
            </div>
          </div>
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title={t('loggingConfig')}
        description={t('loggingConfigDesc')}
        icon={<FileText className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>{t('logLevel')}</label>
            <select
              value={config.log_level || 'INFO'}
              onChange={(e) => updateField('log_level', e.target.value)}
              className={selectClass}
            >
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">{t('logToFile')}</label>
            <Toggle
              checked={!!config.log_to_file}
              onChange={() => updateField('log_to_file', !config.log_to_file)}
            />
          </div>
          {config.log_to_file && (
            <div>
              <label className={labelClass}>{t('logFilePath')}</label>
              <input
                type="text"
                value={config.log_file || ''}
                onChange={(e) => updateField('log_file', e.target.value)}
                className={inputClass}
              />
            </div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>{t('logMaxSize')}</label>
              <input
                type="number"
                min="1"
                value={
                  config.log_max_size
                    ? Math.round(config.log_max_size / 1024 / 1024)
                    : 10
                }
                onChange={(e) =>
                  updateField(
                    'log_max_size',
                    (parseInt(e.target.value, 10) || 10) * 1024 * 1024
                  )
                }
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>{t('logBackupCount')}</label>
              <input
                type="number"
                min="0"
                value={config.log_backup_count || 5}
                onChange={(e) =>
                  updateField(
                    'log_backup_count',
                    parseInt(e.target.value, 10) || 5
                  )
                }
                className={inputClass}
              />
            </div>
          </div>
          <div>
            <label className={labelClass}>{t('logFormat')}</label>
            <input
              type="text"
              value={
                config.log_format || '%(asctime)s [%(levelname)s] %(message)s'
              }
              onChange={(e) => updateField('log_format', e.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>{t('logDateFormat')}</label>
            <input
              type="text"
              value={config.log_date_format || '%Y-%m-%d %H:%M:%S'}
              onChange={(e) => updateField('log_date_format', e.target.value)}
              className={inputClass}
            />
          </div>
        </div>
      </ConfigFieldGroup>
      <ConfigFieldGroup
        title={t('aiSignalAnalysis')}
        description={t('aiSignalAnalysisDesc')}
        icon={<Brain className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <AIModuleConfigGroup
          title={t('aiSignalAnalysis')}
          description={t('aiSignalAnalysisDesc')}
          enabled={aiSignalEnabled}
          config={aiSignalConfig}
          onEnabledChange={(enabled) =>
            updateFields({
              ai_signal_config: {
                ...aiSignalConfig,
                enabled,
              } as AISignalConfig,
              enable_ai_signal_analysis: enabled,
            })
          }
          onConfigChange={(newConfig) => {
            const nextConfig = newConfig as AISignalConfig
            updateFields({
              ai_signal_config: nextConfig,
              enable_ai_signal_analysis: nextConfig.enabled,
            })
          }}
          onTestConnection={async (cfg) => {
            try {
              const result = await api.testAISignalConnection(cfg)
              return result
            } catch (error) {
              return {
                success: false,
                error: error instanceof Error ? error.message : 'Test failed',
              }
            }
          }}
          showIntervalHours
          intervalHours={aiSignalConfig.interval_hours}
          onIntervalHoursChange={(hours) =>
            updateFields({
              ai_signal_config: {
                ...aiSignalConfig,
                interval_hours: hours,
              } as AISignalConfig,
            })
          }
          showLookbackHours
          lookbackHours={aiSignalConfig.lookback_hours}
          onLookbackHoursChange={(hours) =>
            updateFields({
              ai_signal_config: {
                ...aiSignalConfig,
                lookback_hours: hours,
              } as AISignalConfig,
            })
          }
        />
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title={t('aiKeyLevels')}
        description={t('aiKeyLevelsDesc')}
        icon={<Brain className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <AIModuleConfigGroup
          title={t('aiKeyLevels')}
          description={t('aiKeyLevelsDesc')}
          enabled={aiLevelsEnabled}
          config={aiLevelsConfig}
          onEnabledChange={(enabled) =>
            updateFields({
              ai_levels_config: {
                ...aiLevelsConfig,
                enabled,
              } as AILevelsConfig,
              enable_ai_key_levels: enabled,
            })
          }
          onConfigChange={(newConfig) => {
            const nextConfig = newConfig as AILevelsConfig
            updateFields({
              ai_levels_config: nextConfig,
              enable_ai_key_levels: nextConfig.enabled,
            })
          }}
          onTestConnection={async (cfg) => {
            try {
              const result = await api.testAILevelsConnection(cfg)
              return result
            } catch (error) {
              return {
                success: false,
                error: error instanceof Error ? error.message : 'Test failed',
              }
            }
          }}
        />
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title={t('aiOverlays')}
        description={t('aiOverlaysDesc')}
        icon={<Brain className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <AIModuleConfigGroup
          title={t('aiOverlays')}
          description={t('aiOverlaysDesc')}
          enabled={aiOverlaysEnabled}
          config={aiOverlaysConfig}
          onEnabledChange={(enabled) =>
            updateFields({
              ai_overlays_config: {
                ...aiOverlaysConfig,
                enabled,
              } as AIOverlaysConfig,
              enable_ai_overlays: enabled,
            })
          }
          onConfigChange={(newConfig) => {
            const nextConfig = newConfig as AIOverlaysConfig
            updateFields({
              ai_overlays_config: nextConfig,
              enable_ai_overlays: nextConfig.enabled,
            })
          }}
          onTestConnection={async (cfg) => {
            try {
              const result = await api.testAIOverlaysConnection(cfg)
              return result
            } catch (error) {
              return {
                success: false,
                error: error instanceof Error ? error.message : 'Test failed',
              }
            }
          }}
        />
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title={t('aiMarketAnalysis')}
        description={t('aiMarketAnalysisDesc')}
        icon={<Brain className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <AIModuleConfigGroup
          title={t('aiMarketAnalysis')}
          description={t('aiMarketAnalysisDesc')}
          enabled={aiMarketConfig.enabled}
          config={aiMarketConfig}
          onEnabledChange={(enabled) =>
            updateField('ai_market_config', {
              ...aiMarketConfig,
              enabled,
            } as AIMarketConfig)
          }
          onConfigChange={(newConfig) =>
            updateField('ai_market_config', newConfig as AIMarketConfig)
          }
          onTestConnection={async (cfg) => {
            try {
              const result = await api.testAIMarketConnection(cfg)
              return result
            } catch (error) {
              return {
                success: false,
                error: error instanceof Error ? error.message : 'Test failed',
              }
            }
          }}
          showIntervalHours
          intervalHours={aiMarketConfig.interval_hours}
          onIntervalHoursChange={(hours) =>
            updateField('ai_market_config', {
              ...aiMarketConfig,
              interval_hours: hours,
            } as AIMarketConfig)
          }
          showLookbackHours
          lookbackHours={aiMarketConfig.lookback_hours}
          onLookbackHoursChange={(hours) =>
            updateField('ai_market_config', {
              ...aiMarketConfig,
              lookback_hours: hours,
            } as AIMarketConfig)
          }
        />
      </ConfigFieldGroup>
    </div>
  )
}

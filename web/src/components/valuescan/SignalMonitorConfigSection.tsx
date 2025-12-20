import { Send, Globe, Server, Shield, BarChart3, FileText } from 'lucide-react'
import type { SignalMonitorConfig } from '../../types/config'
import { ConfigFieldGroup } from './ConfigFieldGroup'
import { SensitiveFieldInput } from './SensitiveFieldInput'

interface SignalMonitorConfigSectionProps {
  config: Partial<SignalMonitorConfig>
  onChange: (config: Partial<SignalMonitorConfig>) => void
  errors?: Record<string, string>
}

// Toggle switch component for consistent styling
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
  const updateField = <K extends keyof SignalMonitorConfig>(
    key: K,
    value: SignalMonitorConfig[K]
  ) => {
    onChange({ ...config, [key]: value })
  }

  const inputClass =
    'w-full px-3 py-2 bg-neutral-900 border border-neutral-800 rounded-lg text-sm text-white placeholder:text-neutral-600 focus:outline-none focus:border-neutral-600 transition-colors'
  const selectClass =
    'w-full px-3 py-2 bg-neutral-900 border border-neutral-800 rounded-lg text-sm text-white focus:outline-none focus:border-neutral-600 transition-colors'
  const labelClass = 'block text-sm text-neutral-400 mb-1.5'

  return (
    <div className="space-y-4">
      {/* Telegram Group */}
      <ConfigFieldGroup
        title="Telegram 通知"
        description="配置 Telegram Bot 发送信号通知"
        icon={<Send className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">
              启用 Telegram 通知
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
            label="Bot Token"
            placeholder="输入 Telegram Bot Token"
          />
          {errors.telegram_bot_token && (
            <p className="text-xs text-red-400">{errors.telegram_bot_token}</p>
          )}
          <SensitiveFieldInput
            fieldKey="telegram_chat_id"
            value={config.telegram_chat_id || ''}
            onChange={(v) => updateField('telegram_chat_id', v)}
            label="Chat ID"
            placeholder="输入 Telegram Chat ID"
          />
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">
              Mode 1 时发送通知
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

      {/* Browser Group */}
      <ConfigFieldGroup
        title="浏览器设置"
        description="Chrome 调试端口和无头模式"
        icon={<Globe className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>Chrome 调试端口</label>
            <input
              type="number"
              value={config.chrome_debug_port || 9222}
              onChange={(e) =>
                updateField(
                  'chrome_debug_port',
                  parseInt(e.target.value) || 9222
                )
              }
              className={inputClass}
            />
          </div>
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">无头模式</label>
            <Toggle
              checked={!!config.headless_mode}
              onChange={() =>
                updateField('headless_mode', !config.headless_mode)
              }
            />
          </div>
        </div>
      </ConfigFieldGroup>

      {/* IPC Group */}
      <ConfigFieldGroup
        title="IPC 转发"
        description="进程间通信配置，用于转发信号到交易模块"
        icon={<Server className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">启用 IPC 转发</label>
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
              <label className={labelClass}>IPC 主机</label>
              <input
                type="text"
                value={config.ipc_host || 'localhost'}
                onChange={(e) => updateField('ipc_host', e.target.value)}
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>IPC 端口</label>
              <input
                type="number"
                value={config.ipc_port || 9999}
                onChange={(e) =>
                  updateField('ipc_port', parseInt(e.target.value) || 9999)
                }
                className={inputClass}
              />
            </div>
          </div>
        </div>
      </ConfigFieldGroup>

      {/* Proxy Group */}
      <ConfigFieldGroup
        title="代理设置"
        description="SOCKS5 和 HTTP 代理配置"
        icon={<Shield className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>SOCKS5 代理</label>
            <input
              type="text"
              value={config.socks5_proxy || ''}
              onChange={(e) => updateField('socks5_proxy', e.target.value)}
              placeholder="socks5://127.0.0.1:1080"
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>HTTP 代理</label>
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

      {/* Chart Group */}
      <ConfigFieldGroup
        title="图表设置"
        description="TradingView 图表截图配置"
        icon={<BarChart3 className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">
              启用 TradingView 图表
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
          <SensitiveFieldInput
            fieldKey="chart_img_api_key"
            value={config.chart_img_api_key || ''}
            onChange={(v) => updateField('chart_img_api_key', v)}
            label="Chart-img API Key"
          />
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className={labelClass}>Layout ID</label>
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
              <label className={labelClass}>宽度</label>
              <input
                type="number"
                value={config.chart_img_width || 800}
                onChange={(e) =>
                  updateField(
                    'chart_img_width',
                    parseInt(e.target.value) || 800
                  )
                }
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>高度</label>
              <input
                type="number"
                value={config.chart_img_height || 600}
                onChange={(e) =>
                  updateField(
                    'chart_img_height',
                    parseInt(e.target.value) || 600
                  )
                }
                className={inputClass}
              />
            </div>
          </div>
        </div>
      </ConfigFieldGroup>

      {/* Logging Group */}
      <ConfigFieldGroup
        title="日志设置"
        description="日志级别和文件配置"
        icon={<FileText className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>日志级别</label>
            <select
              value={config.log_level || 'INFO'}
              onChange={(e) => updateField('log_level', e.target.value)}
              className={selectClass}
            >
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
            </select>
          </div>
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">写入日志文件</label>
            <Toggle
              checked={!!config.log_to_file}
              onChange={() => updateField('log_to_file', !config.log_to_file)}
            />
          </div>
          {config.log_to_file && (
            <div>
              <label className={labelClass}>日志文件路径</label>
              <input
                type="text"
                value={config.log_file || ''}
                onChange={(e) => updateField('log_file', e.target.value)}
                className={inputClass}
              />
            </div>
          )}
        </div>
      </ConfigFieldGroup>
    </div>
  )
}

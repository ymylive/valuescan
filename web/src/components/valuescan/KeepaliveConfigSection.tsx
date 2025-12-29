import { Settings, Bell, Server } from 'lucide-react'
import type {
  KeepaliveConfig,
  KeepaliveServiceConfig,
} from '../../types/config'
import { ConfigFieldGroup } from './ConfigFieldGroup'
import { SensitiveFieldInput } from './SensitiveFieldInput'
import { ServiceListEditor } from './ServiceListEditor'
import {
  validateKeepaliveCheckInterval,
  validateTelegramAlertConfig,
} from '../../utils/configValidation'

interface KeepaliveConfigSectionProps {
  config: KeepaliveConfig | null
  onChange: (config: KeepaliveConfig) => void
  errors?: Record<string, string>
}

const DEFAULT_CONFIG: KeepaliveConfig = {
  global: {
    check_interval: 60,
    restart_cooldown: 300,
    log_file: 'keepalive.log',
  },
  telegram: {
    enabled: false,
    bot_token: '',
    chat_id: '',
  },
  services: [],
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

export function KeepaliveConfigSection({
  config,
  onChange,
  errors: _errors = {},
}: KeepaliveConfigSectionProps) {
  // Note: _errors is available for future field-level error display
  void _errors
  const currentConfig = config || DEFAULT_CONFIG

  const updateGlobal = (
    key: keyof KeepaliveConfig['global'],
    value: unknown
  ) => {
    onChange({
      ...currentConfig,
      global: { ...currentConfig.global, [key]: value },
    })
  }

  const updateTelegram = (
    key: keyof KeepaliveConfig['telegram'],
    value: unknown
  ) => {
    onChange({
      ...currentConfig,
      telegram: { ...currentConfig.telegram, [key]: value },
    })
  }

  const updateServices = (services: KeepaliveServiceConfig[]) => {
    onChange({
      ...currentConfig,
      services,
    })
  }

  // Validate check interval
  const checkIntervalValidation = validateKeepaliveCheckInterval(
    currentConfig.global.check_interval
  )

  // Validate telegram config
  const telegramValidation = validateTelegramAlertConfig(currentConfig.telegram)

  const inputClass =
    'w-full px-3 py-2 bg-neutral-900 border border-neutral-800 rounded-lg text-sm text-white placeholder:text-neutral-600 focus:outline-none focus:border-neutral-600 transition-colors'
  const labelClass = 'block text-sm text-neutral-400 mb-1.5'

  return (
    <div className="space-y-4">
      {/* Global Settings */}
      <ConfigFieldGroup
        title="全局设置"
        description="服务健康检查的默认参数"
        icon={<Settings className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>
                默认检查间隔 (秒)
                <span className="text-xs text-neutral-500 ml-1">10-300</span>
              </label>
              <input
                type="number"
                min={10}
                max={300}
                value={currentConfig.global.check_interval}
                onChange={(e) => {
                  const value = parseInt(e.target.value) || 60
                  const { clamped } = validateKeepaliveCheckInterval(value)
                  updateGlobal('check_interval', clamped)
                }}
                className={`${inputClass} ${
                  !checkIntervalValidation.valid
                    ? 'border-amber-500/50 focus:border-amber-500'
                    : ''
                }`}
              />
              {!checkIntervalValidation.valid && (
                <p className="text-xs text-amber-500 mt-1">
                  {checkIntervalValidation.message}
                </p>
              )}
            </div>
            <div>
              <label className={labelClass}>默认重启冷却 (秒)</label>
              <input
                type="number"
                min={60}
                value={currentConfig.global.restart_cooldown}
                onChange={(e) =>
                  updateGlobal(
                    'restart_cooldown',
                    parseInt(e.target.value) || 300
                  )
                }
                className={inputClass}
              />
            </div>
          </div>
          <div>
            <label className={labelClass}>日志文件</label>
            <input
              type="text"
              value={currentConfig.global.log_file}
              onChange={(e) => updateGlobal('log_file', e.target.value)}
              className={inputClass}
            />
          </div>
        </div>
      </ConfigFieldGroup>

      {/* Telegram Alert Settings */}
      <ConfigFieldGroup
        title="Telegram 告警"
        description="服务异常时发送 Telegram 通知"
        icon={<Bell className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">
              启用 Telegram 告警
            </label>
            <Toggle
              checked={currentConfig.telegram.enabled}
              onChange={() =>
                updateTelegram('enabled', !currentConfig.telegram.enabled)
              }
            />
          </div>

          {currentConfig.telegram.enabled && (
            <>
              <SensitiveFieldInput
                fieldKey="telegram_bot_token"
                value={currentConfig.telegram.bot_token}
                onChange={(v) => updateTelegram('bot_token', v)}
                label="Bot Token"
                placeholder="输入 Telegram Bot Token"
              />
              {telegramValidation.errors.find(
                (e) => e.field === 'telegram.bot_token'
              ) && (
                <p className="text-xs text-red-400">
                  {
                    telegramValidation.errors.find(
                      (e) => e.field === 'telegram.bot_token'
                    )?.message
                  }
                </p>
              )}

              <SensitiveFieldInput
                fieldKey="telegram_chat_id"
                value={currentConfig.telegram.chat_id}
                onChange={(v) => updateTelegram('chat_id', v)}
                label="Chat ID"
                placeholder="输入 Telegram Chat ID"
              />
              {telegramValidation.errors.find(
                (e) => e.field === 'telegram.chat_id'
              ) && (
                <p className="text-xs text-red-400">
                  {
                    telegramValidation.errors.find(
                      (e) => e.field === 'telegram.chat_id'
                    )?.message
                  }
                </p>
              )}
            </>
          )}
        </div>
      </ConfigFieldGroup>

      {/* Services List */}
      <ConfigFieldGroup
        title="监控服务"
        description="配置需要监控的 systemd 服务"
        icon={<Server className="w-5 h-5" />}
        collapsible={false}
      >
        <ServiceListEditor
          services={currentConfig.services}
          onChange={updateServices}
        />
      </ConfigFieldGroup>
    </div>
  )
}

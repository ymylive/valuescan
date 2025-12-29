import { MessageSquare, Wallet, TrendingUp, Shield, Filter, Bell, FileText, Target } from 'lucide-react'
import type { CopyTradeConfig } from '../../types/config'
import { ConfigFieldGroup } from './ConfigFieldGroup'
import { SensitiveFieldInput } from './SensitiveFieldInput'
import { TagInput } from './TagInput'

interface CopyTradeConfigSectionProps {
  config: Partial<CopyTradeConfig>
  onChange: (config: Partial<CopyTradeConfig>) => void
  errors?: Record<string, string>
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
      className={`relative w-10 h-5 rounded-full transition-all duration-300 border border-white/5 ${
        checked ? 'bg-white' : 'bg-white/10'
      } shadow-inner`}
    >
      <span
        className={`absolute top-0.5 w-3.5 h-3.5 rounded-full transition-all duration-300 shadow-sm ${
          checked ? 'left-5.5 bg-black scale-110' : 'left-1 bg-neutral-500'
        }`}
      />
    </button>
  )
}

export function CopyTradeConfigSection({
  config,
  onChange,
  errors = {},
}: CopyTradeConfigSectionProps) {
  const updateField = <K extends keyof CopyTradeConfig>(
    key: K,
    value: CopyTradeConfig[K]
  ) => {
    onChange({ ...config, [key]: value })
  }

  const isFixedMode = config.position_mode === 'FIXED'
  const followLeverage = config.leverage === 'FOLLOW'
  const inputClass = 'input-modern'
  const selectClass = 'input-modern'
  const labelClass = 'block text-sm font-medium text-neutral-400 mb-1.5'

  return (
    <div className="space-y-4">
      <ConfigFieldGroup
        title="Telegram API"
        description="Telegram client API"
        icon={<MessageSquare className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>API ID</label>
            <input
              type="number"
              value={config.telegram_api_id || ''}
              onChange={(e) =>
                updateField('telegram_api_id', parseInt(e.target.value, 10) || 0)
              }
              placeholder="Telegram API ID"
              className={inputClass}
            />
            {errors.telegram_api_id && (
              <p className="text-xs text-red-400 mt-1">
                {errors.telegram_api_id}
              </p>
            )}
          </div>
          <SensitiveFieldInput
            fieldKey="telegram_api_hash"
            value={config.telegram_api_hash || ''}
            onChange={(v) => updateField('telegram_api_hash', v)}
            label="API Hash"
          />
          <div>
            <label className={labelClass}>Monitor group IDs</label>
            <input
              type="text"
              value={config.monitor_group_ids?.join(', ') || ''}
              onChange={(e) => {
                const ids = e.target.value
                  .split(',')
                  .map((s) => parseInt(s.trim(), 10))
                  .filter((n) => !isNaN(n))
                updateField('monitor_group_ids', ids)
              }}
              placeholder="-1001234567890, -1009876543210"
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>Signal user IDs</label>
            <input
              type="text"
              value={config.signal_user_ids?.join(', ') || ''}
              onChange={(e) => {
                const ids = e.target.value
                  .split(',')
                  .map((s) => parseInt(s.trim(), 10))
                  .filter((n) => !isNaN(n))
                updateField('signal_user_ids', ids)
              }}
              placeholder="Optional"
              className={inputClass}
            />
          </div>
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title="Copytrade"
        description="Copytrade behavior"
        icon={<Wallet className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">Enable copytrade</label>
            <Toggle
              checked={!!config.copytrade_enabled}
              onChange={() =>
                updateField('copytrade_enabled', !config.copytrade_enabled)
              }
            />
          </div>
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">Follow close signal</label>
            <Toggle
              checked={!!config.follow_close_signal}
              onChange={() =>
                updateField('follow_close_signal', !config.follow_close_signal)
              }
            />
          </div>
          <div>
            <label className={labelClass}>Copytrade mode</label>
            <select
              value={config.copytrade_mode || 'OPEN_ONLY'}
              onChange={(e) =>
                updateField(
                  'copytrade_mode',
                  e.target.value as 'OPEN_ONLY' | 'FULL'
                )
              }
              className={selectClass}
            >
              <option value="OPEN_ONLY">Open only</option>
              <option value="FULL">Full</option>
            </select>
          </div>
          <div>
            <label className={labelClass}>Position mode</label>
            <select
              value={config.position_mode || 'RATIO'}
              onChange={(e) =>
                updateField('position_mode', e.target.value as 'FIXED' | 'RATIO')
              }
              className={selectClass}
            >
              <option value="RATIO">Ratio</option>
              <option value="FIXED">Fixed</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>Position ratio</label>
              <input
                type="number"
                min={0}
                max={1}
                step={0.01}
                value={config.position_ratio || 0.1}
                onChange={(e) =>
                  updateField('position_ratio', parseFloat(e.target.value) || 0.1)
                }
                disabled={isFixedMode}
                className={`${inputClass} ${isFixedMode ? 'opacity-50 cursor-not-allowed' : ''}`}
              />
            </div>
            <div>
              <label className={labelClass}>Fixed position (USDT)</label>
              <input
                type="number"
                min={0}
                value={config.fixed_position_size || 100}
                onChange={(e) =>
                  updateField(
                    'fixed_position_size',
                    parseFloat(e.target.value) || 100
                  )
                }
                disabled={!isFixedMode}
                className={`${inputClass} ${!isFixedMode ? 'opacity-50 cursor-not-allowed' : ''}`}
              />
            </div>
          </div>
        </div>
      </ConfigFieldGroup>
      <ConfigFieldGroup
        title="Leverage"
        description="Leverage settings"
        icon={<TrendingUp className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">Follow signal leverage</label>
            <Toggle
              checked={followLeverage}
              onChange={() =>
                updateField('leverage', followLeverage ? 10 : 'FOLLOW')
              }
            />
          </div>
          <div>
            <label className={labelClass}>Leverage</label>
            <input
              type="number"
              min={1}
              max={125}
              value={typeof config.leverage === 'number' ? config.leverage : 10}
              onChange={(e) =>
                updateField('leverage', parseInt(e.target.value, 10) || 10)
              }
              disabled={followLeverage}
              className={`${inputClass} ${followLeverage ? 'opacity-50 cursor-not-allowed' : ''}`}
            />
          </div>
          <div>
            <label className={labelClass}>Margin type</label>
            <select
              value={config.margin_type || 'ISOLATED'}
              onChange={(e) =>
                updateField('margin_type', e.target.value as 'ISOLATED' | 'CROSSED')
              }
              className={selectClass}
            >
              <option value="ISOLATED">Isolated</option>
              <option value="CROSSED">Crossed</option>
            </select>
          </div>
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title="Stop Loss / Take Profit"
        description="Exit controls"
        icon={<Target className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>Stop loss (%)</label>
            <input
              type="number"
              min={0}
              step={0.1}
              value={config.stop_loss_percent || 3}
              onChange={(e) =>
                updateField('stop_loss_percent', parseFloat(e.target.value) || 3)
              }
              className={inputClass}
            />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className={labelClass}>TP1 (%)</label>
              <input
                type="number"
                min={0}
                step={0.1}
                value={config.take_profit_1_percent || 5}
                onChange={(e) =>
                  updateField(
                    'take_profit_1_percent',
                    parseFloat(e.target.value) || 5
                  )
                }
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>TP2 (%)</label>
              <input
                type="number"
                min={0}
                step={0.1}
                value={config.take_profit_2_percent || 10}
                onChange={(e) =>
                  updateField(
                    'take_profit_2_percent',
                    parseFloat(e.target.value) || 10
                  )
                }
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>TP3 (%)</label>
              <input
                type="number"
                min={0}
                step={0.1}
                value={config.take_profit_3_percent || 15}
                onChange={(e) =>
                  updateField(
                    'take_profit_3_percent',
                    parseFloat(e.target.value) || 15
                  )
                }
                className={inputClass}
              />
            </div>
          </div>
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">Enable trailing stop</label>
            <Toggle
              checked={!!config.enable_trailing_stop}
              onChange={() =>
                updateField('enable_trailing_stop', !config.enable_trailing_stop)
              }
            />
          </div>
          {config.enable_trailing_stop && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelClass}>Activation (%)</label>
                <input
                  type="number"
                  min={0}
                  step={0.1}
                  value={config.trailing_stop_activation || 3}
                  onChange={(e) =>
                    updateField(
                      'trailing_stop_activation',
                      parseFloat(e.target.value) || 3
                    )
                  }
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Callback (%)</label>
                <input
                  type="number"
                  min={0}
                  step={0.1}
                  value={config.trailing_stop_callback || 2}
                  onChange={(e) =>
                    updateField(
                      'trailing_stop_callback',
                      parseFloat(e.target.value) || 2
                    )
                  }
                  className={inputClass}
                />
              </div>
            </div>
          )}
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title="Risk Control"
        description="Position and daily limits"
        icon={<Shield className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>Max position (%)</label>
              <input
                type="number"
                min={0}
                max={100}
                step={0.1}
                value={config.max_position_percent || 10}
                onChange={(e) =>
                  updateField(
                    'max_position_percent',
                    parseFloat(e.target.value) || 10
                  )
                }
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>Max total position (%)</label>
              <input
                type="number"
                min={0}
                max={100}
                step={0.1}
                value={config.max_total_position_percent || 50}
                onChange={(e) =>
                  updateField(
                    'max_total_position_percent',
                    parseFloat(e.target.value) || 50
                  )
                }
                className={inputClass}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>Max daily trades</label>
              <input
                type="number"
                min={0}
                value={config.max_daily_trades || 20}
                onChange={(e) =>
                  updateField('max_daily_trades', parseInt(e.target.value, 10) || 20)
                }
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>Max daily loss (%)</label>
              <input
                type="number"
                min={0}
                max={100}
                step={0.1}
                value={config.max_daily_loss_percent || 10}
                onChange={(e) =>
                  updateField(
                    'max_daily_loss_percent',
                    parseFloat(e.target.value) || 10
                  )
                }
                className={inputClass}
              />
            </div>
          </div>
          <div>
            <label className={labelClass}>Max single trade (USDT)</label>
            <input
              type="number"
              min={0}
              value={config.max_single_trade_value || 500}
              onChange={(e) =>
                updateField(
                  'max_single_trade_value',
                  parseFloat(e.target.value) || 500
                )
              }
              className={inputClass}
            />
          </div>
        </div>
      </ConfigFieldGroup>
      <ConfigFieldGroup
        title="Signal Filter"
        description="Filter incoming signals"
        icon={<Filter className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>Min leverage</label>
              <input
                type="number"
                min={1}
                value={config.min_leverage || 1}
                onChange={(e) =>
                  updateField('min_leverage', parseInt(e.target.value, 10) || 1)
                }
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>Max leverage</label>
              <input
                type="number"
                min={1}
                max={125}
                value={config.max_leverage || 50}
                onChange={(e) =>
                  updateField('max_leverage', parseInt(e.target.value, 10) || 50)
                }
                className={inputClass}
              />
            </div>
          </div>
          <div>
            <label className={labelClass}>Direction filter</label>
            <select
              value={config.direction_filter || 'BOTH'}
              onChange={(e) =>
                updateField(
                  'direction_filter',
                  e.target.value as 'BOTH' | 'LONG' | 'SHORT'
                )
              }
              className={selectClass}
            >
              <option value="BOTH">Both</option>
              <option value="LONG">Long</option>
              <option value="SHORT">Short</option>
            </select>
          </div>
          <TagInput
            tags={config.symbol_whitelist || []}
            onChange={(tags) => updateField('symbol_whitelist', tags)}
            label="Symbol whitelist"
            description="Only copy these symbols"
          />
          <TagInput
            tags={config.symbol_blacklist || []}
            onChange={(tags) => updateField('symbol_blacklist', tags)}
            label="Symbol blacklist"
            description="Ignore these symbols"
          />
          <div>
            <label className={labelClass}>Max signal delay (s)</label>
            <input
              type="number"
              min={0}
              value={config.max_signal_delay || 60}
              onChange={(e) =>
                updateField('max_signal_delay', parseInt(e.target.value, 10) || 60)
              }
              className={inputClass}
            />
          </div>
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title="Binance API"
        description="Binance trading account"
        icon={<TrendingUp className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
          <SensitiveFieldInput
            fieldKey="binance_api_key"
            value={config.binance_api_key || ''}
            onChange={(v) => updateField('binance_api_key', v)}
            label="API Key"
          />
          <SensitiveFieldInput
            fieldKey="binance_api_secret"
            value={config.binance_api_secret || ''}
            onChange={(v) => updateField('binance_api_secret', v)}
            label="API Secret"
          />
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">Use testnet</label>
            <Toggle
              checked={!!config.use_testnet}
              onChange={() => updateField('use_testnet', !config.use_testnet)}
            />
          </div>
          <div>
            <label className={labelClass}>SOCKS5 proxy</label>
            <input
              type="text"
              value={config.socks5_proxy || ''}
              onChange={(e) => updateField('socks5_proxy', e.target.value)}
              placeholder="socks5://127.0.0.1:1080"
              className={inputClass}
            />
          </div>
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title="Notifications"
        description="Telegram notifications"
        icon={<Bell className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
          <SensitiveFieldInput
            fieldKey="notify_bot_token"
            value={config.notify_bot_token || ''}
            onChange={(v) => updateField('notify_bot_token', v)}
            label="Notify Bot Token"
          />
          <SensitiveFieldInput
            fieldKey="notify_chat_id"
            value={config.notify_chat_id || ''}
            onChange={(v) => updateField('notify_chat_id', v)}
            label="Notify Chat ID"
          />
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center justify-between">
              <label className="text-sm text-neutral-400">New signal</label>
              <Toggle
                checked={!!config.notify_new_signal}
                onChange={() =>
                  updateField('notify_new_signal', !config.notify_new_signal)
                }
              />
            </div>
            <div className="flex items-center justify-between">
              <label className="text-sm text-neutral-400">Open position</label>
              <Toggle
                checked={!!config.notify_open_position}
                onChange={() =>
                  updateField('notify_open_position', !config.notify_open_position)
                }
              />
            </div>
            <div className="flex items-center justify-between">
              <label className="text-sm text-neutral-400">Close position</label>
              <Toggle
                checked={!!config.notify_close_position}
                onChange={() =>
                  updateField('notify_close_position', !config.notify_close_position)
                }
              />
            </div>
            <div className="flex items-center justify-between">
              <label className="text-sm text-neutral-400">Errors</label>
              <Toggle
                checked={!!config.notify_errors}
                onChange={() => updateField('notify_errors', !config.notify_errors)}
              />
            </div>
          </div>
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title="Logging"
        description="Log settings"
        icon={<FileText className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>Log level</label>
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
          <div>
            <label className={labelClass}>Log file</label>
            <input
              type="text"
              value={config.log_file || 'logs/telegram_copytrade.log'}
              onChange={(e) => updateField('log_file', e.target.value)}
              className={inputClass}
            />
          </div>
        </div>
      </ConfigFieldGroup>
    </div>
  )
}

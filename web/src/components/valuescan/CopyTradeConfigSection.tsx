import { MessageSquare, Wallet, TrendingUp, Shield, Filter } from 'lucide-react'
import type { CopyTradeConfig } from '../../types/config'
import { ConfigFieldGroup } from './ConfigFieldGroup'
import { SensitiveFieldInput } from './SensitiveFieldInput'
import { TagInput } from './TagInput'

interface CopyTradeConfigSectionProps {
  config: Partial<CopyTradeConfig>
  onChange: (config: Partial<CopyTradeConfig>) => void
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
  const inputClass = 'input-modern'
  const selectClass = 'input-modern'
  const labelClass = 'block text-sm font-medium text-neutral-400 mb-1.5'

  return (
    <div className="space-y-4">
      {/* Telegram API Group */}
      <ConfigFieldGroup
        title="Telegram API"
        description="配置 Telegram 客户端 API"
        icon={<MessageSquare className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>API ID</label>
            <input
              type="number"
              value={config.telegram_api_id || ''}
              onChange={(e) =>
                updateField('telegram_api_id', parseInt(e.target.value) || 0)
              }
              placeholder="输入 Telegram API ID"
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
            <label className={labelClass}>监控群组 ID</label>
            <input
              type="text"
              value={config.monitor_group_ids?.join(', ') || ''}
              onChange={(e) => {
                const ids = e.target.value
                  .split(',')
                  .map((s) => parseInt(s.trim()))
                  .filter((n) => !isNaN(n))
                updateField('monitor_group_ids', ids)
              }}
              placeholder="逗号分隔，如: -1001234567890, -1009876543210"
              className={inputClass}
            />
            <p className="text-xs text-neutral-500 mt-1">多个群组用逗号分隔</p>
          </div>
        </div>
      </ConfigFieldGroup>

      {/* Position Group */}
      <ConfigFieldGroup
        title="仓位设置"
        description="跟单仓位计算方式"
        icon={<Wallet className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">启用跟单</label>
            <Toggle
              checked={!!config.copytrade_enabled}
              onChange={() =>
                updateField('copytrade_enabled', !config.copytrade_enabled)
              }
            />
          </div>
          <div>
            <label className={labelClass}>仓位模式</label>
            <select
              value={config.position_mode || 'RATIO'}
              onChange={(e) =>
                updateField(
                  'position_mode',
                  e.target.value as 'FIXED' | 'RATIO'
                )
              }
              className={selectClass}
            >
              <option value="RATIO">比例模式</option>
              <option value="FIXED">固定金额</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>
                仓位比例
                {isFixedMode && (
                  <span className="text-neutral-600 ml-1">(已禁用)</span>
                )}
              </label>
              <input
                type="number"
                min={0}
                max={1}
                step={0.01}
                value={config.position_ratio || 0.1}
                onChange={(e) =>
                  updateField(
                    'position_ratio',
                    parseFloat(e.target.value) || 0.1
                  )
                }
                disabled={isFixedMode}
                className={`${inputClass} ${isFixedMode ? 'opacity-50 cursor-not-allowed' : ''}`}
              />
            </div>
            <div>
              <label className={labelClass}>
                固定金额 (USDT)
                {!isFixedMode && (
                  <span className="text-neutral-600 ml-1">(已禁用)</span>
                )}
              </label>
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

      {/* Leverage Group */}
      <ConfigFieldGroup
        title="杠杆设置"
        description="跟单杠杆配置"
        icon={<TrendingUp className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>杠杆倍数</label>
            <input
              type="number"
              min={1}
              max={125}
              value={typeof config.leverage === 'number' ? config.leverage : 10}
              onChange={(e) =>
                updateField('leverage', parseInt(e.target.value) || 10)
              }
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>保证金类型</label>
            <select
              value={config.margin_type || 'ISOLATED'}
              onChange={(e) =>
                updateField(
                  'margin_type',
                  e.target.value as 'ISOLATED' | 'CROSSED'
                )
              }
              className={selectClass}
            >
              <option value="ISOLATED">逐仓</option>
              <option value="CROSSED">全仓</option>
            </select>
          </div>
        </div>
      </ConfigFieldGroup>

      {/* Risk Control Group */}
      <ConfigFieldGroup
        title="风险控制"
        description="仓位和交易限制"
        icon={<Shield className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>单笔最大仓位 (%)</label>
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
              <label className={labelClass}>总仓位上限 (%)</label>
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
              <label className={labelClass}>每日最大交易次数</label>
              <input
                type="number"
                min={0}
                value={config.max_daily_trades || 10}
                onChange={(e) =>
                  updateField(
                    'max_daily_trades',
                    parseInt(e.target.value) || 10
                  )
                }
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>每日最大亏损 (%)</label>
              <input
                type="number"
                min={0}
                max={100}
                step={0.1}
                value={config.max_daily_loss_percent || 5}
                onChange={(e) =>
                  updateField(
                    'max_daily_loss_percent',
                    parseFloat(e.target.value) || 5
                  )
                }
                className={inputClass}
              />
            </div>
          </div>
        </div>
      </ConfigFieldGroup>

      {/* Signal Filter Group */}
      <ConfigFieldGroup
        title="信号过滤"
        description="过滤不符合条件的交易信号"
        icon={<Filter className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>最小杠杆</label>
              <input
                type="number"
                min={1}
                value={config.min_leverage || 1}
                onChange={(e) =>
                  updateField('min_leverage', parseInt(e.target.value) || 1)
                }
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>最大杠杆</label>
              <input
                type="number"
                min={1}
                max={125}
                value={config.max_leverage || 50}
                onChange={(e) =>
                  updateField('max_leverage', parseInt(e.target.value) || 50)
                }
                className={inputClass}
              />
            </div>
          </div>
          <div>
            <label className={labelClass}>方向过滤</label>
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
              <option value="BOTH">双向</option>
              <option value="LONG">仅做多</option>
              <option value="SHORT">仅做空</option>
            </select>
          </div>
          <TagInput
            tags={config.symbol_whitelist || []}
            onChange={(tags) => updateField('symbol_whitelist', tags)}
            label="币种白名单"
            description="只跟单这些币种，留空表示不限制"
          />
          <TagInput
            tags={config.symbol_blacklist || []}
            onChange={(tags) => updateField('symbol_blacklist', tags)}
            label="币种黑名单"
            description="不跟单这些币种"
          />
        </div>
      </ConfigFieldGroup>
    </div>
  )
}

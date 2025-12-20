import {
  Key,
  TrendingUp,
  TrendingDown,
  Shield,
  Target,
  Activity,
  Zap,
  AlertTriangle,
  Star,
} from 'lucide-react'
import type { TraderConfig } from '../../types/config'
import { ConfigFieldGroup } from './ConfigFieldGroup'
import { SensitiveFieldInput } from './SensitiveFieldInput'
import { TakeProfitEditor } from './TakeProfitEditor'
import { TagInput } from './TagInput'

interface TraderConfigSectionProps {
  config: Partial<TraderConfig>
  onChange: (config: Partial<TraderConfig>) => void
  errors?: Record<string, string>
}

// Toggle switch component for consistent styling
function Toggle({
  checked,
  onChange,
  variant = 'default',
}: {
  checked: boolean
  onChange: () => void
  variant?: 'default' | 'green' | 'red'
}) {
  const bgColor = checked
    ? variant === 'green'
      ? 'bg-green-500'
      : variant === 'red'
        ? 'bg-red-500'
        : 'bg-white'
    : 'bg-white/10'
  const dotColor = checked
    ? variant === 'default'
      ? 'bg-black'
      : 'bg-white'
    : 'bg-neutral-500'

  return (
    <button
      type="button"
      onClick={onChange}
      className={`relative w-10 h-5 rounded-full transition-all duration-300 border border-white/5 ${bgColor} shadow-inner`}
    >
      <span
        className={`absolute top-0.5 w-3.5 h-3.5 rounded-full transition-all duration-300 shadow-sm ${dotColor} ${
          checked ? 'left-5.5 scale-110' : 'left-1'
        }`}
      />
    </button>
  )
}

// 做空金字塔止盈编辑器
function ShortTakeProfitEditor({
  levels,
  onChange,
}: {
  levels: { percent: number; ratio: number }[]
  onChange: (levels: { percent: number; ratio: number }[]) => void
}) {
  const normalizedLevels = [
    levels[0] || { percent: 2, ratio: 0.5 },
    levels[1] || { percent: 3, ratio: 0.5 },
    levels[2] || { percent: 5, ratio: 1.0 },
  ]

  const handlePercentChange = (index: number, value: string) => {
    const num = parseFloat(value)
    if (isNaN(num)) return
    const newLevels = [...normalizedLevels]
    newLevels[index] = { ...newLevels[index], percent: num }
    onChange(newLevels)
  }

  const handleRatioChange = (index: number, value: string) => {
    const num = parseFloat(value)
    if (isNaN(num) || num < 0 || num > 1) return
    const newLevels = [...normalizedLevels]
    newLevels[index] = { ...newLevels[index], ratio: num }
    onChange(newLevels)
  }

  const levelLabels = ['第一目标', '第二目标', '第三目标']
  const levelColors = ['text-yellow-500', 'text-orange-500', 'text-red-500']

  return (
    <div className="glass-panel rounded-lg p-4 bg-red-500/5 border-red-500/10">
      <div className="flex items-center gap-2 mb-4">
        <Target className="w-4 h-4 text-red-400" />
        <span className="text-sm font-medium text-white">做空分批止盈</span>
      </div>
      <div className="space-y-3">
        {normalizedLevels.map((level, index) => (
          <div key={index} className="flex items-center gap-3 flex-wrap p-2 rounded-lg bg-black/20 border border-white/5">
            <div className="flex items-center gap-2 w-24">
              <div
                className={`status-dot ${levelColors[index].replace('text-', 'bg-')} ${levelColors[index]}`}
              />
              <span className={`text-sm ${levelColors[index]}`}>
                {levelLabels[index]}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-neutral-500">下跌</label>
              <div className="relative w-20">
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="100"
                  value={level.percent}
                  onChange={(e) => handlePercentChange(index, e.target.value)}
                  className="input-modern px-2 py-1 h-7 text-xs pr-6"
                />
                <span className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-500 text-[10px]">
                  %
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-neutral-500">平仓</label>
              <div className="relative w-20">
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  value={level.ratio}
                  onChange={(e) => handleRatioChange(index, e.target.value)}
                  className="input-modern px-2 py-1 h-7 text-xs pr-6"
                />
                <span className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-500 text-[10px]">
                  ×
                </span>
              </div>
            </div>
            <span className="text-[10px] text-neutral-500 font-mono">
              ({Math.round(level.ratio * 100)}% POS)
            </span>
          </div>
        ))}
      </div>
      <div className="mt-4 pt-3 border-t border-white/5">
        <p className="text-[10px] text-neutral-500 italic">
          * 提示：价格下跌达到目标时分批平仓。例如下跌2%时平50%，下跌3%时再平50%，下跌5%时全平。
        </p>
      </div>
    </div>
  )
}

// 主流币金字塔止盈编辑器
function MajorCoinTakeProfitEditor({
  levels,
  onChange,
  stopLossPercent,
  onStopLossChange,
}: {
  levels: { percent: number; ratio: number }[]
  onChange: (levels: { percent: number; ratio: number }[]) => void
  stopLossPercent?: number
  onStopLossChange?: (value: number) => void
}) {
  const normalizedLevels = [
    levels[0] || { percent: 1.5, ratio: 0.3 },
    levels[1] || { percent: 2.5, ratio: 0.4 },
    levels[2] || { percent: 4.0, ratio: 1.0 },
  ]

  const handlePercentChange = (index: number, value: string) => {
    const num = parseFloat(value)
    if (isNaN(num)) return
    const newLevels = [...normalizedLevels]
    newLevels[index] = { ...newLevels[index], percent: num }
    onChange(newLevels)
  }

  const handleRatioChange = (index: number, value: string) => {
    const num = parseFloat(value)
    if (isNaN(num) || num < 0 || num > 1) return
    const newLevels = [...normalizedLevels]
    newLevels[index] = { ...newLevels[index], ratio: num }
    onChange(newLevels)
  }

  const levelLabels = ['第一目标', '第二目标', '第三目标']
  const levelColors = ['text-blue-400', 'text-cyan-400', 'text-teal-400']

  return (
    <div className="glass-panel rounded-lg p-4 bg-blue-500/5 border-blue-500/10">
      <div className="flex items-center gap-2 mb-4">
        <Target className="w-4 h-4 text-blue-400" />
        <span className="text-sm font-medium text-white">主流币分批止盈</span>
      </div>

      {/* Stop Loss */}
      {onStopLossChange && (
        <div className="mb-4 pb-4 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 w-24">
              <div className="status-dot text-red-500 bg-red-500" />
              <span className="text-sm text-red-400">止损</span>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-neutral-500">亏损</label>
              <div className="relative w-24">
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="100"
                  value={stopLossPercent || 1.5}
                  onChange={(e) =>
                    onStopLossChange(parseFloat(e.target.value) || 1.5)
                  }
                  className="input-modern px-2 py-1 h-7 text-xs pr-6"
                />
                <span className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-500 text-[10px]">
                  %
                </span>
              </div>
            </div>
            <span className="text-[10px] text-neutral-500 italic">触发止损</span>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {normalizedLevels.map((level, index) => (
          <div key={index} className="flex items-center gap-3 flex-wrap p-2 rounded-lg bg-black/20 border border-white/5">
            <div className="flex items-center gap-2 w-24">
              <div
                className={`status-dot ${levelColors[index].replace('text-', 'bg-')} ${levelColors[index]}`}
              />
              <span className={`text-sm ${levelColors[index]}`}>
                {levelLabels[index]}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-neutral-500">盈利</label>
              <div className="relative w-20">
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="100"
                  value={level.percent}
                  onChange={(e) => handlePercentChange(index, e.target.value)}
                  className="input-modern px-2 py-1 h-7 text-xs pr-6"
                />
                <span className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-500 text-[10px]">
                  %
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-neutral-500">平仓</label>
              <div className="relative w-20">
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  value={level.ratio}
                  onChange={(e) => handleRatioChange(index, e.target.value)}
                  className="input-modern px-2 py-1 h-7 text-xs pr-6"
                />
                <span className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-500 text-[10px]">
                  ×
                </span>
              </div>
            </div>
            <span className="text-[10px] text-neutral-500 font-mono">
              ({Math.round(level.ratio * 100)}% POS)
            </span>
          </div>
        ))}
      </div>
      <div className="mt-4 pt-3 border-t border-white/5">
        <p className="text-[10px] text-neutral-500 italic leading-relaxed">
          * 提示：主流币波动较小，止盈点设置更保守。例如盈利1.5%时平30%，盈利2.5%时平40%，盈利4%时全平。
        </p>
      </div>
    </div>
  )
}

export function TraderConfigSection({
  config,
  onChange,
  errors = {},
}: TraderConfigSectionProps) {
  const updateField = <K extends keyof TraderConfig>(
    key: K,
    value: TraderConfig[K]
  ) => {
    onChange({ ...config, [key]: value })
  }

  const leverage = config.leverage || 1
  const isHighLeverage = leverage > 20

  const inputClass = "input-modern"
  const selectClass = "input-modern"
  const labelClass = 'block text-sm font-medium text-neutral-400 mb-1.5'

  // Convert pyramiding_exit_levels to TakeProfitEditor format (做多)
  const takeProfitLevels = config.pyramiding_exit_levels?.map(
    ([percent, ratio]) => ({
      percent,
      ratio,
    })
  ) || [
    { percent: config.take_profit_1_percent || 3, ratio: 0.5 },
    { percent: config.take_profit_2_percent || 5, ratio: 0.5 },
    { percent: config.take_profit_3_percent || 8, ratio: 1.0 },
  ]

  const handleTakeProfitChange = (
    levels: { percent: number; ratio: number }[]
  ) => {
    onChange({
      ...config,
      take_profit_1_percent: levels[0]?.percent,
      take_profit_2_percent: levels[1]?.percent,
      take_profit_3_percent: levels[2]?.percent,
      pyramiding_exit_levels: levels.map(
        (l) => [l.percent, l.ratio] as [number, number]
      ),
    })
  }

  // Convert short_pyramiding_exit_levels to TakeProfitEditor format (做空)
  const shortTakeProfitLevels = config.short_pyramiding_exit_levels?.map(
    ([percent, ratio]) => ({
      percent,
      ratio,
    })
  ) || [
    { percent: 2, ratio: 0.5 },
    { percent: 3, ratio: 0.5 },
    { percent: 5, ratio: 1.0 },
  ]

  const handleShortTakeProfitChange = (
    levels: { percent: number; ratio: number }[]
  ) => {
    onChange({
      ...config,
      short_pyramiding_exit_levels: levels.map(
        (l) => [l.percent, l.ratio] as [number, number]
      ),
    })
  }

  return (
    <div className="space-y-4">
      {/* Auto Trading Warning */}
      {config.auto_trading_enabled && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-amber-500 font-medium">自动交易已启用</p>
            <p className="text-xs text-amber-500/70 mt-1">
              系统将根据信号自动执行交易，请确保风险参数配置正确。
            </p>
          </div>
        </div>
      )}

      {/* API Group */}
      <ConfigFieldGroup
        title="币安 API"
        description="配置币安 API 密钥"
        icon={<Key className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <SensitiveFieldInput
            fieldKey="binance_api_key"
            value={config.binance_api_key || ''}
            onChange={(v) => updateField('binance_api_key', v)}
            label="API Key"
          />
          {errors.binance_api_key && (
            <p className="text-xs text-red-400">{errors.binance_api_key}</p>
          )}
          <SensitiveFieldInput
            fieldKey="binance_api_secret"
            value={config.binance_api_secret || ''}
            onChange={(v) => updateField('binance_api_secret', v)}
            label="API Secret"
          />
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">使用测试网</label>
            <Toggle
              checked={!!config.use_testnet}
              onChange={() => updateField('use_testnet', !config.use_testnet)}
            />
          </div>
        </div>
      </ConfigFieldGroup>

      {/* Trading Group */}
      <ConfigFieldGroup
        title="交易设置"
        description="杠杆、保证金类型等基础设置"
        icon={<TrendingUp className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>
              山寨币杠杆倍数
              {isHighLeverage && (
                <span className="ml-2 text-xs text-amber-500">
                  ⚠️ 高杠杆风险
                </span>
              )}
            </label>
            <input
              type="number"
              min={1}
              max={125}
              value={leverage}
              onChange={(e) =>
                updateField('leverage', parseInt(e.target.value) || 1)
              }
              className={`${inputClass} ${isHighLeverage ? 'border-amber-500/50 focus:border-amber-500' : ''}`}
            />
            {isHighLeverage && (
              <p className="text-xs text-amber-500 mt-1">
                杠杆超过 20x 会显著增加爆仓风险，请谨慎操作
              </p>
            )}
          </div>
          <div className="grid grid-cols-2 gap-4">
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
            <div>
              <label className={labelClass}>持仓方向</label>
              <select
                value={config.position_side || 'BOTH'}
                onChange={(e) =>
                  updateField(
                    'position_side',
                    e.target.value as 'LONG' | 'SHORT' | 'BOTH'
                  )
                }
                className={selectClass}
              >
                <option value="BOTH">双向持仓</option>
                <option value="LONG">仅做多</option>
                <option value="SHORT">仅做空</option>
              </select>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm text-neutral-400">启用自动交易</label>
              <p className="text-xs text-neutral-500">
                开启后系统将自动执行交易
              </p>
            </div>
            <Toggle
              checked={!!config.auto_trading_enabled}
              onChange={() =>
                updateField(
                  'auto_trading_enabled',
                  !config.auto_trading_enabled
                )
              }
            />
          </div>
        </div>
      </ConfigFieldGroup>

      {/* Long Strategy Group */}
      <ConfigFieldGroup
        title="做多策略"
        description="Alpha或FOMO信号 + 在异动榜单上 → 开多仓"
        icon={<TrendingUp className="w-5 h-5 text-green-500" />}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm text-neutral-400">启用做多</label>
              <p className="text-xs text-neutral-500">
                检测到Alpha/FOMO信号且币种在异动榜单上时自动开多
              </p>
            </div>
            <Toggle
              checked={config.long_trading_enabled !== false}
              onChange={() =>
                updateField(
                  'long_trading_enabled',
                  !config.long_trading_enabled
                )
              }
              variant="green"
            />
          </div>
          {config.long_trading_enabled !== false && (
            <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3">
              <p className="text-xs text-green-400">
                ✅ 做多策略已启用。当检测到 Alpha(110) 或 FOMO(113)
                信号，且币种在异动榜单上时，系统将自动开多仓。
              </p>
            </div>
          )}
        </div>
      </ConfigFieldGroup>

      {/* Short Strategy Group */}
      <ConfigFieldGroup
        title="做空策略"
        description="看跌信号 + 不在异动榜单上 → 开空仓"
        icon={<TrendingDown className="w-5 h-5 text-red-500" />}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm text-neutral-400">启用做空</label>
              <p className="text-xs text-neutral-500">
                检测到看跌信号且币种不在异动榜单上时自动开空
              </p>
            </div>
            <Toggle
              checked={!!config.short_trading_enabled}
              onChange={() =>
                updateField(
                  'short_trading_enabled',
                  !config.short_trading_enabled
                )
              }
              variant="red"
            />
          </div>
          {config.short_trading_enabled && (
            <>
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                <p className="text-xs text-red-400">
                  ⚠️ 做空策略已启用。当检测到
                  FOMO加剧(112)、资金出逃(111)、风险增加(100-7) 或
                  价格高点(100-24)
                  信号，且币种不在异动榜单上时，系统将自动开空仓。
                </p>
              </div>
              <div>
                <label className={labelClass}>做空止损 (%)</label>
                <input
                  type="number"
                  min={0}
                  max={100}
                  step={0.1}
                  value={config.short_stop_loss_percent || 2}
                  onChange={(e) =>
                    updateField(
                      'short_stop_loss_percent',
                      parseFloat(e.target.value) || 2
                    )
                  }
                  className={inputClass}
                />
                <p className="text-xs text-neutral-500 mt-1">
                  价格上涨此比例时止损
                </p>
              </div>
              <ShortTakeProfitEditor
                levels={shortTakeProfitLevels}
                onChange={handleShortTakeProfitChange}
              />
            </>
          )}
        </div>
      </ConfigFieldGroup>

      {/* Risk Management Group */}
      <ConfigFieldGroup
        title="风险管理"
        description="仓位限制和每日交易限制"
        icon={<Shield className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>山寨币单笔最大仓位 (%)</label>
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

      {/* Stop Loss / Take Profit Group */}
      <ConfigFieldGroup
        title="止损止盈"
        description="配置止损和分批止盈策略"
        icon={<Target className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm text-neutral-400">启用金字塔止盈</label>
              <p className="text-xs text-neutral-500">分批平仓锁定利润</p>
            </div>
            <Toggle
              checked={!!config.enable_pyramiding_exit}
              onChange={() =>
                updateField(
                  'enable_pyramiding_exit',
                  !config.enable_pyramiding_exit
                )
              }
            />
          </div>
          <TakeProfitEditor
            levels={takeProfitLevels}
            onChange={handleTakeProfitChange}
            stopLossPercent={config.stop_loss_percent}
            onStopLossChange={(v) => updateField('stop_loss_percent', v)}
          />
        </div>
      </ConfigFieldGroup>

      {/* Trailing Stop Group */}
      <ConfigFieldGroup
        title="移动止损"
        description="动态调整止损位置"
        icon={<Activity className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">启用移动止损</label>
            <Toggle
              checked={!!config.enable_trailing_stop}
              onChange={() =>
                updateField(
                  'enable_trailing_stop',
                  !config.enable_trailing_stop
                )
              }
            />
          </div>
          {config.enable_trailing_stop && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelClass}>激活阈值 (%)</label>
                <input
                  type="number"
                  min={0}
                  step={0.1}
                  value={config.trailing_stop_activation || 2}
                  onChange={(e) =>
                    updateField(
                      'trailing_stop_activation',
                      parseFloat(e.target.value) || 2
                    )
                  }
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>回调比例 (%)</label>
                <input
                  type="number"
                  min={0}
                  step={0.1}
                  value={config.trailing_stop_callback || 1}
                  onChange={(e) =>
                    updateField(
                      'trailing_stop_callback',
                      parseFloat(e.target.value) || 1
                    )
                  }
                  className={inputClass}
                />
              </div>
            </div>
          )}
        </div>
      </ConfigFieldGroup>

      {/* Major Coin Strategy Group */}
      <ConfigFieldGroup
        title="主流币策略"
        description="BTC、ETH等主流币使用独立的止盈止损策略"
        icon={<Star className="w-5 h-5 text-yellow-500" />}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm text-neutral-400">
                启用主流币独立策略
              </label>
              <p className="text-xs text-neutral-500">
                主流币波动较小，使用更保守的止盈止损
              </p>
            </div>
            <Toggle
              checked={!!config.enable_major_coin_strategy}
              onChange={() =>
                updateField(
                  'enable_major_coin_strategy',
                  !config.enable_major_coin_strategy
                )
              }
            />
          </div>

          {config.enable_major_coin_strategy && (
            <>
              {/* Major Coins List */}
              <TagInput
                tags={config.major_coins || ['BTC', 'ETH', 'BNB', 'SOL', 'XRP']}
                onChange={(tags) =>
                  updateField(
                    'major_coins',
                    tags.map((t) => t.toUpperCase())
                  )
                }
                label="主流币列表"
                description="这些币种将使用独立的止盈止损策略"
                placeholder="输入币种符号，如 BTC"
              />

              {/* Major Coin Leverage & Position Size */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={labelClass}>主流币杠杆倍数</label>
                  <input
                    type="number"
                    min={1}
                    max={125}
                    value={config.major_coin_leverage || 5}
                    onChange={(e) =>
                      updateField('major_coin_leverage', parseInt(e.target.value) || 5)
                    }
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>主流币单笔最大仓位 (%)</label>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    step={0.1}
                    value={config.major_coin_max_position_percent || 20}
                    onChange={(e) =>
                      updateField('major_coin_max_position_percent', parseFloat(e.target.value) || 20)
                    }
                    className={inputClass}
                  />
                </div>
              </div>

              {/* Strategy Comparison */}
              <div className="bg-neutral-900/50 border border-neutral-800 rounded-lg p-4">
                <h4 className="text-sm font-medium text-white mb-3">
                  策略对比
                </h4>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-neutral-400">
                        <th className="text-left py-2 pr-4">参数</th>
                        <th className="text-center py-2 px-4">主流币</th>
                        <th className="text-center py-2 pl-4">山寨币</th>
                      </tr>
                    </thead>
                    <tbody className="text-neutral-300">
                      <tr className="border-t border-neutral-800">
                        <td className="py-2 pr-4">杠杆</td>
                        <td className="text-center py-2 px-4 text-blue-400">
                          {config.major_coin_leverage || 5}x
                        </td>
                        <td className="text-center py-2 pl-4 text-green-400">
                          {config.leverage || 1}x
                        </td>
                      </tr>
                      <tr className="border-t border-neutral-800">
                        <td className="py-2 pr-4">单笔仓位</td>
                        <td className="text-center py-2 px-4 text-blue-400">
                          {config.major_coin_max_position_percent || 20}%
                        </td>
                        <td className="text-center py-2 pl-4 text-green-400">
                          {config.max_position_percent || 10}%
                        </td>
                      </tr>
                      <tr className="border-t border-neutral-800">
                        <td className="py-2 pr-4">止损</td>
                        <td className="text-center py-2 px-4 text-blue-400">
                          {config.major_coin_stop_loss_percent || 1.5}%
                        </td>
                        <td className="text-center py-2 pl-4 text-green-400">
                          {config.stop_loss_percent || 2}%
                        </td>
                      </tr>
                      <tr className="border-t border-neutral-800">
                        <td className="py-2 pr-4">止盈1</td>
                        <td className="text-center py-2 px-4 text-blue-400">
                          {config.major_coin_pyramiding_exit_levels?.[0]?.[0] ||
                            1.5}
                          % (平
                          {Math.round(
                            (config
                              .major_coin_pyramiding_exit_levels?.[0]?.[1] ||
                              0.3) * 100
                          )}
                          %)
                        </td>
                        <td className="text-center py-2 pl-4 text-green-400">
                          {config.pyramiding_exit_levels?.[0]?.[0] || 3}% (平
                          {Math.round(
                            (config.pyramiding_exit_levels?.[0]?.[1] || 0.5) *
                              100
                          )}
                          %)
                        </td>
                      </tr>
                      <tr className="border-t border-neutral-800">
                        <td className="py-2 pr-4">止盈2</td>
                        <td className="text-center py-2 px-4 text-blue-400">
                          {config.major_coin_pyramiding_exit_levels?.[1]?.[0] ||
                            2.5}
                          % (平
                          {Math.round(
                            (config
                              .major_coin_pyramiding_exit_levels?.[1]?.[1] ||
                              0.4) * 100
                          )}
                          %)
                        </td>
                        <td className="text-center py-2 pl-4 text-green-400">
                          {config.pyramiding_exit_levels?.[1]?.[0] || 5}% (平
                          {Math.round(
                            (config.pyramiding_exit_levels?.[1]?.[1] || 0.5) *
                              100
                          )}
                          %)
                        </td>
                      </tr>
                      <tr className="border-t border-neutral-800">
                        <td className="py-2 pr-4">止盈3</td>
                        <td className="text-center py-2 px-4 text-blue-400">
                          {config.major_coin_pyramiding_exit_levels?.[2]?.[0] ||
                            4}
                          % (全平)
                        </td>
                        <td className="text-center py-2 pl-4 text-green-400">
                          {config.pyramiding_exit_levels?.[2]?.[0] || 8}% (全平)
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Major Coin Take Profit Editor */}
              <MajorCoinTakeProfitEditor
                levels={
                  config.major_coin_pyramiding_exit_levels?.map(
                    ([percent, ratio]) => ({
                      percent,
                      ratio,
                    })
                  ) || [
                    { percent: 1.5, ratio: 0.3 },
                    { percent: 2.5, ratio: 0.4 },
                    { percent: 4.0, ratio: 1.0 },
                  ]
                }
                onChange={(levels) => {
                  onChange({
                    ...config,
                    major_coin_pyramiding_exit_levels: levels.map(
                      (l) => [l.percent, l.ratio] as [number, number]
                    ),
                  })
                }}
                stopLossPercent={config.major_coin_stop_loss_percent}
                onStopLossChange={(v) =>
                  updateField('major_coin_stop_loss_percent', v)
                }
              />

              {/* Major Coin Trailing Stop */}
              <div className="bg-neutral-900 border border-neutral-800 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-4">
                  <Activity className="w-4 h-4 text-blue-400" />
                  <span className="text-sm font-medium text-white">
                    主流币移动止损
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className={labelClass}>激活阈值 (%)</label>
                    <input
                      type="number"
                      min={0}
                      step={0.1}
                      value={config.major_coin_trailing_stop_activation || 1}
                      onChange={(e) =>
                        updateField(
                          'major_coin_trailing_stop_activation',
                          parseFloat(e.target.value) || 1
                        )
                      }
                      className={inputClass}
                    />
                    <p className="text-xs text-neutral-500 mt-1">
                      盈利达到此比例后启动移动止损
                    </p>
                  </div>
                  <div>
                    <label className={labelClass}>回调比例 (%)</label>
                    <input
                      type="number"
                      min={0}
                      step={0.1}
                      value={config.major_coin_trailing_stop_callback || 0.8}
                      onChange={(e) =>
                        updateField(
                          'major_coin_trailing_stop_callback',
                          parseFloat(e.target.value) || 0.8
                        )
                      }
                      className={inputClass}
                    />
                    <p className="text-xs text-neutral-500 mt-1">
                      从最高点回撤此比例触发止损
                    </p>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </ConfigFieldGroup>

      {/* Execution Group */}
      <ConfigFieldGroup
        title="执行设置"
        description="订单类型和执行参数"
        icon={<Zap className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>订单类型</label>
            <select
              value={config.order_type || 'MARKET'}
              onChange={(e) =>
                updateField('order_type', e.target.value as 'MARKET' | 'LIMIT')
              }
              className={selectClass}
            >
              <option value="MARKET">市价单</option>
              <option value="LIMIT">限价单</option>
            </select>
          </div>
          {config.enable_pyramiding_exit && (
            <div>
              <label className={labelClass}>止盈执行方式</label>
              <select
                value={config.pyramiding_exit_execution || 'market'}
                onChange={(e) =>
                  updateField(
                    'pyramiding_exit_execution',
                    e.target.value as 'orders' | 'market'
                  )
                }
                className={selectClass}
              >
                <option value="market">市价执行</option>
                <option value="orders">挂单执行</option>
              </select>
            </div>
          )}
        </div>
      </ConfigFieldGroup>
    </div>
  )
}

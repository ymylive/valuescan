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
  Bell,
  Clock,
  Brain,
  Ban,
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
    const next = [...normalizedLevels]
    next[index] = { ...next[index], percent: num }
    onChange(next)
  }

  const handleRatioChange = (index: number, value: string) => {
    const num = parseFloat(value)
    if (isNaN(num) || num < 0 || num > 1) return
    const next = [...normalizedLevels]
    next[index] = { ...next[index], ratio: num }
    onChange(next)
  }

  const labels = ['Level 1', 'Level 2', 'Level 3']

  return (
    <div className="glass-panel rounded-lg p-4 bg-red-500/5 border-red-500/10">
      <div className="flex items-center gap-2 mb-4">
        <Target className="w-4 h-4 text-red-400" />
        <span className="text-sm font-medium text-white">Short Take Profit</span>
      </div>
      <div className="space-y-3">
        {normalizedLevels.map((level, index) => (
          <div
            key={index}
            className="flex items-center gap-3 flex-wrap p-2 rounded-lg bg-black/20 border border-white/5"
          >
            <div className="flex items-center gap-2 w-24">
              <span className="text-sm text-red-400">{labels[index]}</span>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-neutral-500">Drop</label>
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
              <label className="text-xs text-neutral-500">Close</label>
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
                  x
                </span>
              </div>
            </div>
          </div>
        ))}
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

  const inputClass = 'input-modern'
  const selectClass = 'input-modern'
  const labelClass = 'block text-sm font-medium text-neutral-400 mb-1.5'

  const takeProfitLevels =
    config.pyramiding_exit_levels?.map(([percent, ratio]) => ({
      percent,
      ratio,
    })) || [
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
      pyramiding_exit_levels: levels.map((l) => [l.percent, l.ratio] as [number, number]),
    })
  }

  const shortTakeProfitLevels =
    config.short_pyramiding_exit_levels?.map(([percent, ratio]) => ({
      percent,
      ratio,
    })) || [
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
      <ConfigFieldGroup
        title="Binance API"
        description="API keys and proxy"
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
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">
              Auto proxy (local)
            </label>
            <Toggle
              checked={!!config.auto_proxy_binance}
              onChange={() =>
                updateField('auto_proxy_binance', !config.auto_proxy_binance)
              }
            />
          </div>
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">Proxy fallback</label>
            <Toggle
              checked={!!config.enable_proxy_fallback}
              onChange={() =>
                updateField('enable_proxy_fallback', !config.enable_proxy_fallback)
              }
            />
          </div>
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title="Trading Basics"
        description="Leverage and order basics"
        icon={<TrendingUp className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>Symbol suffix</label>
            <input
              type="text"
              value={config.symbol_suffix || 'USDT'}
              onChange={(e) => updateField('symbol_suffix', e.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>Leverage</label>
            <input
              type="number"
              min={1}
              max={125}
              value={config.leverage || 1}
              onChange={(e) =>
                updateField('leverage', parseInt(e.target.value, 10) || 1)
              }
              className={inputClass}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>Margin type</label>
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
                <option value="ISOLATED">Isolated</option>
                <option value="CROSSED">Crossed</option>
              </select>
            </div>
            <div>
              <label className={labelClass}>Position side</label>
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
                <option value="BOTH">Both</option>
                <option value="LONG">Long</option>
                <option value="SHORT">Short</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>Order type</label>
              <select
                value={config.order_type || 'MARKET'}
                onChange={(e) =>
                  updateField('order_type', e.target.value as 'MARKET' | 'LIMIT')
                }
                className={selectClass}
              >
                <option value="MARKET">Market</option>
                <option value="LIMIT">Limit</option>
              </select>
            </div>
            <div>
              <label className={labelClass}>Position precision</label>
              <input
                type="number"
                min={0}
                max={8}
                value={config.position_precision || 3}
                onChange={(e) =>
                  updateField(
                    'position_precision',
                    parseInt(e.target.value, 10) || 3
                  )
                }
                className={inputClass}
              />
            </div>
          </div>
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">Auto trading</label>
            <Toggle
              checked={!!config.auto_trading_enabled}
              onChange={() =>
                updateField('auto_trading_enabled', !config.auto_trading_enabled)
              }
              variant="green"
            />
          </div>
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">Hedge mode</label>
            <Toggle
              checked={!!config.use_hedge_mode}
              onChange={() => updateField('use_hedge_mode', !config.use_hedge_mode)}
            />
          </div>
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title="Coin Blacklist"
        description="Coins to exclude from trading"
        icon={<Ban className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <TagInput
            value={config.coin_blacklist || []}
            onChange={(tags) => updateField('coin_blacklist', tags)}
            placeholder="Add coin symbol (e.g., DOGE, SHIB)"
            label="Blacklisted Coins"
            description="These coins will be completely ignored by the trading system"
          />
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title="AI Trading Mode"
        description="AI-powered autonomous trading"
        icon={<Brain className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm text-neutral-400">Enable AI Mode</label>
              <p className="text-xs text-neutral-500 mt-1">
                AI takes full control, manual strategies disabled
              </p>
            </div>
            <Toggle
              checked={!!config.enable_ai_mode}
              onChange={() => updateField('enable_ai_mode', !config.enable_ai_mode)}
              variant="green"
            />
          </div>

          {config.enable_ai_mode && (
            <>
              <div className="glass-panel rounded-lg p-4 bg-purple-500/5 border-purple-500/10">
                <div className="flex items-center gap-2 mb-3">
                  <Brain className="w-4 h-4 text-purple-400" />
                  <span className="text-sm font-medium text-white">
                    AI Position Agent
                  </span>
                </div>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm text-neutral-400">
                        Enable Position Agent
                      </label>
                      <p className="text-xs text-neutral-500 mt-1">
                        AI decides when to add/reduce/close positions
                      </p>
                    </div>
                    <Toggle
                      checked={!!config.enable_ai_position_agent}
                      onChange={() =>
                        updateField(
                          'enable_ai_position_agent',
                          !config.enable_ai_position_agent
                        )
                      }
                    />
                  </div>

                  {config.enable_ai_position_agent && (
                    <>
                      <div>
                        <label className={labelClass}>Check Interval (seconds)</label>
                        <input
                          type="number"
                          min={60}
                          max={3600}
                          value={config.ai_position_check_interval || 300}
                          onChange={(e) =>
                            updateField(
                              'ai_position_check_interval',
                              parseInt(e.target.value, 10) || 300
                            )
                          }
                          className={inputClass}
                        />
                      </div>

                      <div>
                        <label className={labelClass}>AI API Key (optional)</label>
                        <input
                          type="password"
                          value={config.ai_position_api_key || ''}
                          onChange={(e) =>
                            updateField('ai_position_api_key', e.target.value)
                          }
                          placeholder="Leave empty to use AI Signal config"
                          className={inputClass}
                        />
                      </div>

                      <div>
                        <label className={labelClass}>AI API URL (optional)</label>
                        <input
                          type="text"
                          value={config.ai_position_api_url || ''}
                          onChange={(e) =>
                            updateField('ai_position_api_url', e.target.value)
                          }
                          placeholder="Leave empty to use AI Signal config"
                          className={inputClass}
                        />
                      </div>

                      <div>
                        <label className={labelClass}>AI Model (optional)</label>
                        <input
                          type="text"
                          value={config.ai_position_model || ''}
                          onChange={(e) =>
                            updateField('ai_position_model', e.target.value)
                          }
                          placeholder="Leave empty to use AI Signal config"
                          className={inputClass}
                        />
                      </div>
                    </>
                  )}
                </div>
              </div>

              <div className="glass-panel rounded-lg p-3 bg-yellow-500/5 border-yellow-500/10">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-yellow-400 mt-0.5 flex-shrink-0" />
                  <div className="text-xs text-neutral-400">
                    <p className="font-medium text-yellow-400 mb-1">
                      AI Mode Active
                    </p>
                    <p>
                      Traditional signal strategies (FOMO + Alpha) are disabled.
                      Trading decisions are made entirely by AI signal analysis.
                    </p>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title="AI Evolution System"
        description="AI self-learning and optimization"
        icon={<Zap className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm text-neutral-400">Enable AI Evolution</label>
              <p className="text-xs text-neutral-500 mt-1">
                AI learns from trading data and optimizes strategy
              </p>
            </div>
            <Toggle
              checked={!!config.enable_ai_evolution}
              onChange={() =>
                updateField('enable_ai_evolution', !config.enable_ai_evolution)
              }
              variant="green"
            />
          </div>

          {config.enable_ai_evolution && (
            <>
              <div className="glass-panel rounded-lg p-4 bg-gradient-to-br from-purple-500/10 to-blue-500/10 border-purple-500/20">
                <div className="flex items-center gap-2 mb-3">
                  <Star className="w-4 h-4 text-purple-400" />
                  <span className="text-sm font-medium text-white">
                    Evolution Strategy
                  </span>
                </div>
                <div>
                  <label className={labelClass}>Strategy Profile</label>
                  <select
                    value={config.ai_evolution_profile || 'balanced_day'}
                    onChange={(e) =>
                      updateField('ai_evolution_profile', e.target.value)
                    }
                    className={selectClass}
                  >
                    <optgroup label="Conservative (Low Risk)">
                      <option value="conservative_scalping">
                        稳健剥头皮 - Low risk ultra-short term
                      </option>
                      <option value="conservative_swing">
                        稳健波段 - Low risk swing trading
                      </option>
                    </optgroup>
                    <optgroup label="Balanced (Recommended)">
                      <option value="balanced_day">
                        平衡日内 - Balanced day trading (Recommended)
                      </option>
                      <option value="balanced_swing">
                        平衡波段 - Balanced swing trading
                      </option>
                    </optgroup>
                    <optgroup label="Aggressive (High Risk)">
                      <option value="aggressive_scalping">
                        激进剥头皮 - High frequency high risk
                      </option>
                      <option value="aggressive_day">
                        激进日内 - Aggressive day trading
                      </option>
                    </optgroup>
                  </select>
                  <p className="text-xs text-neutral-500 mt-2">
                    {config.ai_evolution_profile === 'conservative_scalping' &&
                      '⏱️ Ultra-short term (1-5 min) | 🎯 Win rate focused | 🛡️ Tight stop loss'}
                    {config.ai_evolution_profile === 'conservative_swing' &&
                      '📅 Medium term (2-10 days) | 🎯 Stable returns | 🛡️ Low risk'}
                    {config.ai_evolution_profile === 'balanced_day' &&
                      '⏰ Day trading (1-8 hours) | ⚖️ Balanced risk/reward | 👍 Most popular'}
                    {config.ai_evolution_profile === 'balanced_swing' &&
                      '📊 Swing trading (2-10 days) | ⚖️ Balanced approach | 💼 Good for busy traders'}
                    {config.ai_evolution_profile === 'aggressive_scalping' &&
                      '⚡ High frequency (1-5 min) | 💰 Profit focused | ⚠️ High risk'}
                    {config.ai_evolution_profile === 'aggressive_day' &&
                      '🔥 Aggressive day (1-8 hours) | 💰 Max profit | ⚠️ High risk'}
                  </p>
                </div>
              </div>

              <div className="glass-panel rounded-lg p-4 bg-blue-500/5 border-blue-500/10">
                <div className="flex items-center gap-2 mb-3">
                  <Zap className="w-4 h-4 text-blue-400" />
                  <span className="text-sm font-medium text-white">
                    Learning Parameters
                  </span>
                </div>
                <div className="space-y-4">
                  <div>
                    <label className={labelClass}>Min Trades for Learning</label>
                    <input
                      type="number"
                      min={10}
                      max={500}
                      value={config.ai_evolution_min_trades || 50}
                      onChange={(e) =>
                        updateField(
                          'ai_evolution_min_trades',
                          parseInt(e.target.value, 10) || 50
                        )
                      }
                      className={inputClass}
                    />
                    <p className="text-xs text-neutral-500 mt-1">
                      Minimum trades needed before AI starts learning
                    </p>
                  </div>

                  <div>
                    <label className={labelClass}>Learning Period (days)</label>
                    <input
                      type="number"
                      min={7}
                      max={90}
                      value={config.ai_evolution_learning_period_days || 30}
                      onChange={(e) =>
                        updateField(
                          'ai_evolution_learning_period_days',
                          parseInt(e.target.value, 10) || 30
                        )
                      }
                      className={inputClass}
                    />
                    <p className="text-xs text-neutral-500 mt-1">
                      How many days of data to analyze
                    </p>
                  </div>

                  <div>
                    <label className={labelClass}>Evolution Interval (hours)</label>
                    <input
                      type="number"
                      min={1}
                      max={168}
                      value={config.ai_evolution_interval_hours || 24}
                      onChange={(e) =>
                        updateField(
                          'ai_evolution_interval_hours',
                          parseInt(e.target.value, 10) || 24
                        )
                      }
                      className={inputClass}
                    />
                    <p className="text-xs text-neutral-500 mt-1">
                      How often AI should evolve
                    </p>
                  </div>
                </div>
              </div>

              <div className="glass-panel rounded-lg p-4 bg-purple-500/5 border-purple-500/10">
                <div className="flex items-center gap-2 mb-3">
                  <Activity className="w-4 h-4 text-purple-400" />
                  <span className="text-sm font-medium text-white">A/B Testing</span>
                </div>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm text-neutral-400">
                        Enable A/B Testing
                      </label>
                      <p className="text-xs text-neutral-500 mt-1">
                        Test new strategies before full deployment
                      </p>
                    </div>
                    <Toggle
                      checked={!!config.enable_ai_ab_testing}
                      onChange={() =>
                        updateField(
                          'enable_ai_ab_testing',
                          !config.enable_ai_ab_testing
                        )
                      }
                    />
                  </div>

                  {config.enable_ai_ab_testing && (
                    <div>
                      <label className={labelClass}>Test Ratio</label>
                      <input
                        type="number"
                        min={0.05}
                        max={0.5}
                        step={0.05}
                        value={config.ai_ab_test_ratio || 0.2}
                        onChange={(e) =>
                          updateField(
                            'ai_ab_test_ratio',
                            parseFloat(e.target.value) || 0.2
                          )
                        }
                        className={inputClass}
                      />
                      <p className="text-xs text-neutral-500 mt-1">
                        Percentage of trades using new strategy (0.05-0.5)
                      </p>
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-3">
                <div>
                  <label className={labelClass}>Evolution API Key (optional)</label>
                  <input
                    type="password"
                    value={config.ai_evolution_api_key || ''}
                    onChange={(e) =>
                      updateField('ai_evolution_api_key', e.target.value)
                    }
                    placeholder="Leave empty to use AI Signal config"
                    className={inputClass}
                  />
                </div>

                <div>
                  <label className={labelClass}>Evolution API URL (optional)</label>
                  <input
                    type="text"
                    value={config.ai_evolution_api_url || ''}
                    onChange={(e) =>
                      updateField('ai_evolution_api_url', e.target.value)
                    }
                    placeholder="Leave empty to use AI Signal config"
                    className={inputClass}
                  />
                </div>

                <div>
                  <label className={labelClass}>Evolution Model (optional)</label>
                  <input
                    type="text"
                    value={config.ai_evolution_model || ''}
                    onChange={(e) =>
                      updateField('ai_evolution_model', e.target.value)
                    }
                    placeholder="Leave empty to use AI Signal config"
                    className={inputClass}
                  />
                </div>
              </div>

              <div className="glass-panel rounded-lg p-3 bg-green-500/5 border-green-500/10">
                <div className="flex items-start gap-2">
                  <Star className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                  <div className="text-xs text-neutral-400">
                    <p className="font-medium text-green-400 mb-1">
                      Self-Learning AI
                    </p>
                    <p>
                      AI analyzes trading performance, discovers patterns, and
                      automatically optimizes strategy parameters. A/B testing ensures
                      new strategies are validated before full deployment.
                    </p>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title="Long Strategy"
        description="Long trading controls"
        icon={<TrendingUp className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm text-neutral-400">Enable long</label>
              {config.enable_ai_mode && (
                <p className="text-xs text-neutral-500 mt-1">
                  (Disabled in AI Mode)
                </p>
              )}
            </div>
            <Toggle
              checked={config.long_trading_enabled !== false}
              onChange={() =>
                updateField('long_trading_enabled', !config.long_trading_enabled)
              }
              variant="green"
            />
          </div>
          <TakeProfitEditor
            levels={takeProfitLevels}
            onChange={handleTakeProfitChange}
            stopLossPercent={config.stop_loss_percent}
            onStopLossChange={(v) => updateField('stop_loss_percent', v)}
          />
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">Enable pyramiding exit</label>
            <Toggle
              checked={!!config.enable_pyramiding_exit}
              onChange={() =>
                updateField('enable_pyramiding_exit', !config.enable_pyramiding_exit)
              }
            />
          </div>
          {config.enable_pyramiding_exit && (
            <div>
              <label className={labelClass}>Pyramiding execution</label>
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
                <option value="market">Market</option>
                <option value="orders">Orders</option>
              </select>
            </div>
          )}
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title="Short Strategy"
        description="Short trading controls"
        icon={<TrendingDown className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">Enable short</label>
            <Toggle
              checked={!!config.short_trading_enabled}
              onChange={() =>
                updateField('short_trading_enabled', !config.short_trading_enabled)
              }
              variant="red"
            />
          </div>
          {config.short_trading_enabled && (
            <>
              <div>
                <label className={labelClass}>Short stop loss (%)</label>
                <input
                  type="number"
                  min={0}
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
              </div>
              <div className="flex items-center justify-between">
                <label className="text-sm text-neutral-400">
                  Enable short pyramiding exit
                </label>
                <Toggle
                  checked={!!config.short_enable_pyramiding_exit}
                  onChange={() =>
                    updateField(
                      'short_enable_pyramiding_exit',
                      !config.short_enable_pyramiding_exit
                    )
                  }
                />
              </div>
              {config.short_enable_pyramiding_exit ? (
                <ShortTakeProfitEditor
                  levels={shortTakeProfitLevels}
                  onChange={handleShortTakeProfitChange}
                />
              ) : (
                <div>
                  <label className={labelClass}>Short take profit (%)</label>
                  <input
                    type="number"
                    min={0}
                    step={0.1}
                    value={config.short_take_profit_percent || 3}
                    onChange={(e) =>
                      updateField(
                        'short_take_profit_percent',
                        parseFloat(e.target.value) || 3
                      )
                    }
                    className={inputClass}
                  />
                </div>
              )}
            </>
          )}
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title="Trailing Stop"
        description="Trailing stop settings"
        icon={<Activity className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
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
                <label className={labelClass}>Callback (%)</label>
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
              <div>
                <label className={labelClass}>Update interval (s)</label>
                <input
                  type="number"
                  min={1}
                  value={config.trailing_stop_update_interval || 10}
                  onChange={(e) =>
                    updateField(
                      'trailing_stop_update_interval',
                      parseInt(e.target.value, 10) || 10
                    )
                  }
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Type</label>
                <select
                  value={config.trailing_stop_type || 'PERCENTAGE'}
                  onChange={(e) =>
                    updateField('trailing_stop_type', e.target.value)
                  }
                  className={selectClass}
                >
                  <option value="PERCENTAGE">Percentage</option>
                  <option value="FIXED">Fixed</option>
                </select>
              </div>
            </div>
          )}
        </div>
      </ConfigFieldGroup>
      <ConfigFieldGroup
        title="Signal Aggregation"
        description="Signal merging and cache"
        icon={<Zap className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>Signal time window (s)</label>
            <input
              type="number"
              min={30}
              value={config.signal_time_window || 300}
              onChange={(e) =>
                updateField(
                  'signal_time_window',
                  parseInt(e.target.value, 10) || 300
                )
              }
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>Min signal score</label>
            <input
              type="number"
              min={0}
              max={1}
              step={0.1}
              value={config.min_signal_score || 0.6}
              onChange={(e) =>
                updateField('min_signal_score', parseFloat(e.target.value) || 0.6)
              }
              className={inputClass}
            />
          </div>
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">Enable signal state cache</label>
            <Toggle
              checked={!!config.enable_signal_state_cache}
              onChange={() =>
                updateField(
                  'enable_signal_state_cache',
                  !config.enable_signal_state_cache
                )
              }
            />
          </div>
          {config.enable_signal_state_cache && (
            <div>
              <label className={labelClass}>Signal state file</label>
              <input
                type="text"
                value={config.signal_state_file || 'data/signal_state.json'}
                onChange={(e) => updateField('signal_state_file', e.target.value)}
                className={inputClass}
              />
            </div>
          )}
          <div>
            <label className={labelClass}>Max processed signal IDs</label>
            <input
              type="number"
              min={100}
              value={config.max_processed_signal_ids || 5000}
              onChange={(e) =>
                updateField(
                  'max_processed_signal_ids',
                  parseInt(e.target.value, 10) || 5000
                )
              }
              className={inputClass}
            />
          </div>
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">Enable FOMO intensify</label>
            <Toggle
              checked={!!config.enable_fomo_intensify}
              onChange={() =>
                updateField('enable_fomo_intensify', !config.enable_fomo_intensify)
              }
            />
          </div>
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title="Risk Management"
        description="Position limits and daily limits"
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
              <label className={labelClass}>Major total position (%)</label>
              <input
                type="number"
                min={0}
                max={100}
                step={0.1}
                value={config.major_total_position_percent || 30}
                onChange={(e) =>
                  updateField(
                    'major_total_position_percent',
                    parseFloat(e.target.value) || 30
                  )
                }
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>Alt total position (%)</label>
              <input
                type="number"
                min={0}
                max={100}
                step={0.1}
                value={config.alt_total_position_percent || 30}
                onChange={(e) =>
                  updateField(
                    'alt_total_position_percent',
                    parseFloat(e.target.value) || 30
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
                value={config.max_daily_trades || 10}
                onChange={(e) =>
                  updateField('max_daily_trades', parseInt(e.target.value, 10) || 10)
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
          <div>
            <label className={labelClass}>Max single trade value (USDT)</label>
            <input
              type="number"
              min={0}
              value={config.max_single_trade_value || 1000}
              onChange={(e) =>
                updateField(
                  'max_single_trade_value',
                  parseFloat(e.target.value) || 1000
                )
              }
              className={inputClass}
            />
          </div>
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title="Monitoring"
        description="Position and balance monitoring"
        icon={<Activity className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>Position monitor interval (s)</label>
            <input
              type="number"
              min={1}
              value={config.position_monitor_interval || 10}
              onChange={(e) =>
                updateField(
                  'position_monitor_interval',
                  parseInt(e.target.value, 10) || 10
                )
              }
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>Balance update interval (s)</label>
            <input
              type="number"
              min={1}
              value={config.balance_update_interval || 60}
              onChange={(e) =>
                updateField(
                  'balance_update_interval',
                  parseInt(e.target.value, 10) || 60
                )
              }
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>Liquidation warning margin (%)</label>
            <input
              type="number"
              min={0}
              max={100}
              step={0.1}
              value={config.liquidation_warning_margin_ratio || 30}
              onChange={(e) =>
                updateField(
                  'liquidation_warning_margin_ratio',
                  parseFloat(e.target.value) || 30
                )
              }
              className={inputClass}
            />
          </div>
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title="Safety"
        description="Emergency controls"
        icon={<AlertTriangle className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>Force close margin ratio (%)</label>
            <input
              type="number"
              min={0}
              max={100}
              step={0.1}
              value={config.force_close_margin_ratio || 20}
              onChange={(e) =>
                updateField(
                  'force_close_margin_ratio',
                  parseFloat(e.target.value) || 20
                )
              }
              className={inputClass}
            />
          </div>
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">Emergency stop</label>
            <Toggle
              checked={!!config.enable_emergency_stop}
              onChange={() =>
                updateField('enable_emergency_stop', !config.enable_emergency_stop)
              }
              variant="red"
            />
          </div>
          {config.enable_emergency_stop && (
            <div>
              <label className={labelClass}>Emergency stop file</label>
              <input
                type="text"
                value={config.emergency_stop_file || 'STOP_TRADING'}
                onChange={(e) => updateField('emergency_stop_file', e.target.value)}
                className={inputClass}
              />
            </div>
          )}
        </div>
      </ConfigFieldGroup>
      <ConfigFieldGroup
        title="Notifications"
        description="Telegram notifications"
        icon={<Bell className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">Enable notifications</label>
            <Toggle
              checked={!!config.enable_trade_notifications}
              onChange={() =>
                updateField(
                  'enable_trade_notifications',
                  !config.enable_trade_notifications
                )
              }
              variant="green"
            />
          </div>
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">Enable alert mode</label>
            <Toggle
              checked={!!config.enable_telegram_alerts}
              onChange={() =>
                updateField('enable_telegram_alerts', !config.enable_telegram_alerts)
              }
            />
          </div>
          <SensitiveFieldInput
            fieldKey="telegram_bot_token"
            value={config.telegram_bot_token || ''}
            onChange={(v) => updateField('telegram_bot_token', v)}
            label="Telegram Bot Token"
          />
          <SensitiveFieldInput
            fieldKey="telegram_chat_id"
            value={config.telegram_chat_id || ''}
            onChange={(v) => updateField('telegram_chat_id', v)}
            label="Telegram Chat ID"
          />
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center justify-between">
              <label className="text-sm text-neutral-400">Open</label>
              <Toggle
                checked={!!config.notify_open_position}
                onChange={() =>
                  updateField('notify_open_position', !config.notify_open_position)
                }
              />
            </div>
            <div className="flex items-center justify-between">
              <label className="text-sm text-neutral-400">Close</label>
              <Toggle
                checked={!!config.notify_close_position}
                onChange={() =>
                  updateField('notify_close_position', !config.notify_close_position)
                }
              />
            </div>
            <div className="flex items-center justify-between">
              <label className="text-sm text-neutral-400">Stop loss</label>
              <Toggle
                checked={!!config.notify_stop_loss}
                onChange={() =>
                  updateField('notify_stop_loss', !config.notify_stop_loss)
                }
              />
            </div>
            <div className="flex items-center justify-between">
              <label className="text-sm text-neutral-400">Take profit</label>
              <Toggle
                checked={!!config.notify_take_profit}
                onChange={() =>
                  updateField('notify_take_profit', !config.notify_take_profit)
                }
              />
            </div>
            <div className="flex items-center justify-between">
              <label className="text-sm text-neutral-400">Partial close</label>
              <Toggle
                checked={!!config.notify_partial_close}
                onChange={() =>
                  updateField('notify_partial_close', !config.notify_partial_close)
                }
              />
            </div>
            <div className="flex items-center justify-between">
              <label className="text-sm text-neutral-400">Errors</label>
              <Toggle
                checked={!!config.notify_errors}
                onChange={() => updateField('notify_errors', !config.notify_errors)}
                variant="red"
              />
            </div>
          </div>
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title="Execution"
        description="Order cleanup and exit types"
        icon={<Zap className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">
              Cancel exit orders before entry
            </label>
            <Toggle
              checked={!!config.cancel_exit_orders_before_entry}
              onChange={() =>
                updateField(
                  'cancel_exit_orders_before_entry',
                  !config.cancel_exit_orders_before_entry
                )
              }
            />
          </div>
          <TagInput
            tags={config.exit_order_types_to_cancel || []}
            onChange={(tags) => updateField('exit_order_types_to_cancel', tags)}
            label="Exit order types to cancel"
            description="Order types treated as exit orders"
            placeholder="STOP_MARKET"
          />
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title="API Settings"
        description="Retry and timeout"
        icon={<Clock className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>API retry count</label>
            <input
              type="number"
              min={0}
              value={config.api_retry_count || 3}
              onChange={(e) =>
                updateField('api_retry_count', parseInt(e.target.value, 10) || 3)
              }
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>API timeout (s)</label>
            <input
              type="number"
              min={1}
              value={config.api_timeout || 30}
              onChange={(e) =>
                updateField('api_timeout', parseInt(e.target.value, 10) || 30)
              }
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>Slippage tolerance (%)</label>
            <input
              type="number"
              min={0}
              step={0.1}
              value={config.slippage_tolerance || 0.5}
              onChange={(e) =>
                updateField('slippage_tolerance', parseFloat(e.target.value) || 0.5)
              }
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>Binance recv window (ms)</label>
            <input
              type="number"
              min={1000}
              value={config.binance_recv_window_ms || 10000}
              onChange={(e) =>
                updateField(
                  'binance_recv_window_ms',
                  parseInt(e.target.value, 10) || 10000
                )
              }
              className={inputClass}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>Time sync interval (s)</label>
              <input
                type="number"
                min={30}
                value={config.binance_time_sync_interval || 300}
                onChange={(e) =>
                  updateField(
                    'binance_time_sync_interval',
                    parseInt(e.target.value, 10) || 300
                  )
                }
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>Time sync safety (ms)</label>
              <input
                type="number"
                min={0}
                value={config.binance_time_sync_safety_ms || 1500}
                onChange={(e) =>
                  updateField(
                    'binance_time_sync_safety_ms',
                    parseInt(e.target.value, 10) || 1500
                  )
                }
                className={inputClass}
              />
            </div>
          </div>
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title="WebSocket"
        description="Realtime price feed"
        icon={<Activity className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">Enable WebSocket</label>
            <Toggle
              checked={!!config.enable_websocket}
              onChange={() =>
                updateField('enable_websocket', !config.enable_websocket)
              }
              variant="green"
            />
          </div>
          {config.enable_websocket && (
            <div>
              <label className={labelClass}>Reconnect interval (s)</label>
              <input
                type="number"
                min={1}
                value={config.websocket_reconnect_interval || 5}
                onChange={(e) =>
                  updateField(
                    'websocket_reconnect_interval',
                    parseInt(e.target.value, 10) || 5
                  )
                }
                className={inputClass}
              />
            </div>
          )}
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title="Backtest"
        description="Backtest settings"
        icon={<Clock className="w-5 h-5" />}
        defaultExpanded={false}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">Enable backtest</label>
            <Toggle
              checked={!!config.enable_backtest}
              onChange={() => updateField('enable_backtest', !config.enable_backtest)}
            />
          </div>
          {config.enable_backtest && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelClass}>Start date</label>
                <input
                  type="text"
                  value={config.backtest_start_date || '2024-01-01'}
                  onChange={(e) => updateField('backtest_start_date', e.target.value)}
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>End date</label>
                <input
                  type="text"
                  value={config.backtest_end_date || '2024-12-31'}
                  onChange={(e) => updateField('backtest_end_date', e.target.value)}
                  className={inputClass}
                />
              </div>
            </div>
          )}
        </div>
      </ConfigFieldGroup>

      <ConfigFieldGroup
        title="Major Coin Strategy"
        description="Dedicated settings for major coins"
        icon={<Star className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm text-neutral-400">Enable major coins</label>
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
              <TagInput
                tags={config.major_coins || ['BTC', 'ETH', 'BNB', 'SOL', 'XRP']}
                onChange={(tags) =>
                  updateField(
                    'major_coins',
                    tags.map((t) => t.toUpperCase())
                  )
                }
                label="Major coins"
                description="Coin symbols without suffix"
                placeholder="BTC"
              />

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={labelClass}>Major leverage</label>
                  <input
                    type="number"
                    min={1}
                    max={125}
                    value={config.major_coin_leverage || 5}
                    onChange={(e) =>
                      updateField(
                        'major_coin_leverage',
                        parseInt(e.target.value, 10) || 5
                      )
                    }
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>Major max position (%)</label>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    step={0.1}
                    value={config.major_coin_max_position_percent || 20}
                    onChange={(e) =>
                      updateField(
                        'major_coin_max_position_percent',
                        parseFloat(e.target.value) || 20
                      )
                    }
                    className={inputClass}
                  />
                </div>
              </div>

              <div>
                <label className={labelClass}>Major stop loss (%)</label>
                <input
                  type="number"
                  min={0}
                  step={0.1}
                  value={config.major_coin_stop_loss_percent || 1.5}
                  onChange={(e) =>
                    updateField(
                      'major_coin_stop_loss_percent',
                      parseFloat(e.target.value) || 1.5
                    )
                  }
                  className={inputClass}
                />
              </div>

              <TakeProfitEditor
                levels={
                  config.major_coin_pyramiding_exit_levels?.map(
                    ([percent, ratio]) => ({ percent, ratio })
                  ) || [
                    { percent: 1.5, ratio: 0.3 },
                    { percent: 2.5, ratio: 0.4 },
                    { percent: 4, ratio: 1.0 },
                  ]
                }
                onChange={(levels) =>
                  updateField(
                    'major_coin_pyramiding_exit_levels',
                    levels.map((l) => [l.percent, l.ratio] as [number, number])
                  )
                }
                stopLossPercent={config.major_coin_stop_loss_percent}
                onStopLossChange={(v) => updateField('major_coin_stop_loss_percent', v)}
              />

              <div className="flex items-center justify-between">
                <label className="text-sm text-neutral-400">
                  Major trailing stop
                </label>
                <Toggle
                  checked={config.major_coin_enable_trailing_stop ?? true}
                  onChange={() =>
                    updateField(
                      'major_coin_enable_trailing_stop',
                      !(config.major_coin_enable_trailing_stop ?? true)
                    )
                  }
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={labelClass}>Major trailing activation</label>
                  <input
                    type="number"
                    min={0}
                    step={0.1}
                    value={config.major_coin_trailing_stop_activation ?? 1}
                    onChange={(e) =>
                      updateField(
                        'major_coin_trailing_stop_activation',
                        parseFloat(e.target.value) || 1
                      )
                    }
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>Major trailing callback</label>
                  <input
                    type="number"
                    min={0}
                    step={0.1}
                    value={config.major_coin_trailing_stop_callback ?? 0.8}
                    onChange={(e) =>
                      updateField(
                        'major_coin_trailing_stop_callback',
                        parseFloat(e.target.value) || 0.8
                      )
                    }
                    className={inputClass}
                  />
                </div>
              </div>
            </>
          )}
        </div>
      </ConfigFieldGroup>
      <ConfigFieldGroup
        title="Logging"
        description="Trader log settings"
        icon={<Clock className="w-5 h-5" />}
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
              value={config.log_file || 'logs/binance_futures_trader.log'}
              onChange={(e) => updateField('log_file', e.target.value)}
              className={inputClass}
            />
          </div>
        </div>
      </ConfigFieldGroup>
    </div>
  )
}

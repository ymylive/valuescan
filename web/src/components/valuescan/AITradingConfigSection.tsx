import {
  Brain,
  Zap,
  Activity,
  Star,
  AlertTriangle,
  TrendingUp,
  Target,
  Shield,
  Clock,
  BarChart3,
} from 'lucide-react'
import type { TraderConfig } from '../../types/config'
import { ConfigFieldGroup } from './ConfigFieldGroup'

interface AITradingConfigSectionProps {
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

export function AITradingConfigSection({
  config,
  onChange,
  errors = {},
}: AITradingConfigSectionProps) {
  const updateField = (field: keyof TraderConfig, value: any) => {
    onChange({ ...config, [field]: value })
  }

  const labelClass = 'block text-sm font-medium text-neutral-300 mb-2'
  const inputClass =
    'w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-transparent transition-all'
  const selectClass = inputClass

  return (
    <div className="space-y-6">
      {/* AI 托管模式 */}
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

      {/* AI 自我进化系统 */}
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
              {/* 策略配置 */}
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
                    <optgroup label="🛡️ Conservative (Low Risk)">
                      <option value="conservative_scalping">
                        稳健剥头皮 - Low risk ultra-short term
                      </option>
                      <option value="conservative_swing">
                        稳健波段 - Low risk swing trading
                      </option>
                    </optgroup>
                    <optgroup label="⚖️ Balanced (Recommended)">
                      <option value="balanced_day">
                        平衡日内 - Balanced day trading ⭐
                      </option>
                      <option value="balanced_swing">
                        平衡波段 - Balanced swing trading
                      </option>
                    </optgroup>
                    <optgroup label="⚠️ Aggressive (High Risk)">
                      <option value="aggressive_scalping">
                        激进剥头皮 - High frequency high risk
                      </option>
                      <option value="aggressive_day">
                        激进日内 - Aggressive day trading
                      </option>
                    </optgroup>
                  </select>
                  <div className="mt-3 p-3 rounded-lg bg-black/20 border border-white/5">
                    <p className="text-xs text-neutral-300">
                      {config.ai_evolution_profile === 'conservative_scalping' &&
                        '⏱️ Ultra-short term (1-5 min) | 🎯 Win rate focused | 🛡️ Tight stop loss | Max leverage: 5x'}
                      {config.ai_evolution_profile === 'conservative_swing' &&
                        '📅 Medium term (2-10 days) | 🎯 Stable returns | 🛡️ Low risk | Max leverage: 5x'}
                      {config.ai_evolution_profile === 'balanced_day' &&
                        '⏰ Day trading (1-8 hours) | ⚖️ Balanced risk/reward | 👍 Most popular | Max leverage: 10x'}
                      {config.ai_evolution_profile === 'balanced_swing' &&
                        '📊 Swing trading (2-10 days) | ⚖️ Balanced approach | 💼 Good for busy traders | Max leverage: 10x'}
                      {config.ai_evolution_profile === 'aggressive_scalping' &&
                        '⚡ High frequency (1-5 min) | 💰 Profit focused | ⚠️ High risk | Max leverage: 20x'}
                      {config.ai_evolution_profile === 'aggressive_day' &&
                        '🔥 Aggressive day (1-8 hours) | 💰 Max profit | ⚠️ High risk | Max leverage: 20x'}
                    </p>
                  </div>
                </div>
              </div>

              {/* 学习参数 */}
              <div className="glass-panel rounded-lg p-4 bg-blue-500/5 border-blue-500/10">
                <div className="flex items-center gap-2 mb-3">
                  <BarChart3 className="w-4 h-4 text-blue-400" />
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

              {/* A/B 测试 */}
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

              {/* API 配置 */}
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
                      automatically optimizes strategy parameters based on your
                      selected profile. A/B testing ensures new strategies are
                      validated before full deployment.
                    </p>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </ConfigFieldGroup>

      {/* 币种黑名单 */}
      <ConfigFieldGroup
        title="Coin Blacklist"
        description="Coins to exclude from AI trading"
        icon={<Shield className="w-5 h-5" />}
      >
        <div className="space-y-4">
          <div>
            <label className={labelClass}>Blacklisted Coins</label>
            <input
              type="text"
              value={(config.coin_blacklist || []).join(', ')}
              onChange={(e) => {
                const coins = e.target.value
                  .split(',')
                  .map((s) => s.trim().toUpperCase())
                  .filter((s) => s.length > 0)
                updateField('coin_blacklist', coins)
              }}
              placeholder="e.g., DOGE, SHIB, PEPE"
              className={inputClass}
            />
            <p className="text-xs text-neutral-500 mt-1">
              Comma-separated list of coin symbols to exclude from trading
            </p>
          </div>

          {config.coin_blacklist && config.coin_blacklist.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {config.coin_blacklist.map((coin) => (
                <span
                  key={coin}
                  className="px-2 py-1 bg-red-500/10 border border-red-500/20 rounded text-xs text-red-400"
                >
                  {coin}
                </span>
              ))}
            </div>
          )}
        </div>
      </ConfigFieldGroup>

      {/* 信息提示 */}
      <div className="glass-panel rounded-lg p-4 bg-gradient-to-br from-blue-500/5 to-purple-500/5 border-blue-500/10">
        <div className="flex items-start gap-3">
          <Brain className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-white">
              AI Trading System Overview
            </h3>
            <div className="text-xs text-neutral-400 space-y-1">
              <p>
                <strong className="text-neutral-300">AI Mode:</strong> Complete
                autonomous trading with AI signal analysis
              </p>
              <p>
                <strong className="text-neutral-300">Position Agent:</strong>{' '}
                Intelligent position management (add/reduce/close)
              </p>
              <p>
                <strong className="text-neutral-300">Evolution:</strong> Self-learning
                system that optimizes based on performance
              </p>
              <p>
                <strong className="text-neutral-300">Strategy Profiles:</strong> Choose
                from 6 pre-configured risk/style combinations
              </p>
              <p>
                <strong className="text-neutral-300">Blacklist:</strong> Exclude
                specific coins from all AI trading
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

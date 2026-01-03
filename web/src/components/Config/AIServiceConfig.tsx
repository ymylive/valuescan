import React from 'react';
import { useTranslation } from 'react-i18next';
import { GlassCard } from '../Common/GlassCard';
import { Input } from '../Common/Input';
import { Brain, Zap, TrendingUp } from 'lucide-react';
import { AIServiceConfig, AI_EVOLUTION_PROFILES } from '../../types/config';

interface AIServiceConfigProps {
  config: AIServiceConfig;
  onChange: (config: AIServiceConfig) => void;
}

export const AIServiceConfigComponent: React.FC<AIServiceConfigProps> = ({ config, onChange }) => {
  const { t } = useTranslation();

  const handleChange = (field: keyof AIServiceConfig, value: any) => {
    onChange({ ...config, [field]: value });
  };

  return (
    <div className="space-y-6">
      {/* AI 数据源配置 */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <TrendingUp className="text-green-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">AI 分析数据源</h3>
        </div>
        
        <div className="text-sm text-gray-400 space-y-2">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-green-500 rounded-full"></span>
            <span><strong>ValuScan</strong>: 主力位、主力成本、资金流、信号（优先级最高）</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-yellow-500 rounded-full"></span>
            <span><strong>Binance</strong>: K线、资金费率、持仓量、多空比、订单簿（补充数据）</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-blue-500 rounded-full"></span>
            <span><strong>外部API</strong>: Fear & Greed Index（情绪数据）</span>
          </div>
          <p className="text-xs text-gray-500 mt-3 pt-2 border-t border-gray-700">
            所有数据源已默认启用，ValuScan数据优先用于主力位分析
          </p>
        </div>
      </GlassCard>

      {/* AI Position Management */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Brain className="text-purple-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">AI 仓位管理</h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_ai_position_agent"
              checked={config.enable_ai_position_agent}
              onChange={(e) => handleChange('enable_ai_position_agent', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
            />
            <label htmlFor="enable_ai_position_agent" className="text-gray-700 dark:text-gray-300 font-medium">
              启用 AI 仓位管理代理
            </label>
          </div>

          {config.enable_ai_position_agent && (
            <div className="space-y-4 pl-8 border-l-2 border-purple-500/30">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API 端点 URL
                </label>
                <Input
                  type="text"
                  value={config.ai_position_api_url}
                  onChange={(e) => handleChange('ai_position_api_url', e.target.value)}
                  placeholder="https://api.example.com/v1"
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API 密钥
                </label>
                <Input
                  type="password"
                  value={config.ai_position_api_key}
                  onChange={(e) => handleChange('ai_position_api_key', e.target.value)}
                  placeholder="sk-..."
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  模型名称
                </label>
                <Input
                  type="text"
                  value={config.ai_position_model}
                  onChange={(e) => handleChange('ai_position_model', e.target.value)}
                  placeholder="gpt-4, claude-3-opus, etc."
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  检查间隔（秒）
                </label>
                <Input
                  type="number"
                  value={config.ai_position_check_interval}
                  onChange={(e) => handleChange('ai_position_check_interval', parseInt(e.target.value))}
                  min={60}
                  max={3600}
                  className="w-full"
                />
                <p className="text-xs text-gray-500 mt-1">AI 仓位管理检查间隔时间</p>
              </div>
            </div>
          )}
        </div>
      </GlassCard>

      {/* AI Evolution System */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <TrendingUp className="text-blue-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">AI 自我进化系统</h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_ai_evolution"
              checked={config.enable_ai_evolution}
              onChange={(e) => handleChange('enable_ai_evolution', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="enable_ai_evolution" className="text-gray-700 dark:text-gray-300 font-medium">
              启用 AI 自我进化
            </label>
          </div>

          {config.enable_ai_evolution && (
            <div className="space-y-4 pl-8 border-l-2 border-blue-500/30">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API 端点 URL
                </label>
                <Input
                  type="text"
                  value={config.ai_evolution_api_url}
                  onChange={(e) => handleChange('ai_evolution_api_url', e.target.value)}
                  placeholder="https://api.example.com/v1"
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API 密钥
                </label>
                <Input
                  type="password"
                  value={config.ai_evolution_api_key}
                  onChange={(e) => handleChange('ai_evolution_api_key', e.target.value)}
                  placeholder="sk-..."
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  模型名称
                </label>
                <Input
                  type="text"
                  value={config.ai_evolution_model}
                  onChange={(e) => handleChange('ai_evolution_model', e.target.value)}
                  placeholder="gpt-4, claude-3-opus, etc."
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  进化策略配置
                </label>
                <select
                  value={config.ai_evolution_profile}
                  onChange={(e) => handleChange('ai_evolution_profile', e.target.value)}
                  className="w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {AI_EVOLUTION_PROFILES.map((profile) => (
                    <option key={profile.value} value={profile.value}>
                      {profile.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    最少交易数
                  </label>
                  <Input
                    type="number"
                    value={config.ai_evolution_min_trades}
                    onChange={(e) => handleChange('ai_evolution_min_trades', parseInt(e.target.value))}
                    min={10}
                    className="w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    学习周期（天）
                  </label>
                  <Input
                    type="number"
                    value={config.ai_evolution_learning_period_days}
                    onChange={(e) => handleChange('ai_evolution_learning_period_days', parseInt(e.target.value))}
                    min={1}
                    className="w-full"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  进化间隔（小时）
                </label>
                <Input
                  type="number"
                  value={config.ai_evolution_interval_hours}
                  onChange={(e) => handleChange('ai_evolution_interval_hours', parseInt(e.target.value))}
                  min={1}
                  max={168}
                  className="w-full"
                />
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="enable_ai_ab_testing"
                  checked={config.enable_ai_ab_testing}
                  onChange={(e) => handleChange('enable_ai_ab_testing', e.target.checked)}
                  className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="enable_ai_ab_testing" className="text-gray-700 dark:text-gray-300">
                  启用 A/B 测试
                </label>
              </div>

              {config.enable_ai_ab_testing && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    A/B 测试比例（0-1）
                  </label>
                  <Input
                    type="number"
                    value={config.ai_ab_test_ratio}
                    onChange={(e) => handleChange('ai_ab_test_ratio', parseFloat(e.target.value))}
                    min={0}
                    max={1}
                    step={0.1}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">用于测试新策略的交易比例</p>
                </div>
              )}
            </div>
          )}
        </div>
      </GlassCard>

      {/* AI Summary Proxy */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Zap className="text-yellow-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">AI 市场总结代理</h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              代理地址
            </label>
            <Input
              type="text"
              value={config.ai_summary_proxy}
              onChange={(e) => handleChange('ai_summary_proxy', e.target.value)}
              placeholder="http://127.0.0.1:7890"
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">用于 AI API 调用的代理地址（可选）</p>
          </div>
        </div>
      </GlassCard>

      {/* AI Signal Analysis (单币简评) */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Brain className="text-green-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">AI 单币简评服务</h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_ai_signal_analysis_service"
              checked={config.enable_ai_signal_analysis_service}
              onChange={(e) => handleChange('enable_ai_signal_analysis_service', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-green-600 focus:ring-green-500"
            />
            <label htmlFor="enable_ai_signal_analysis_service" className="text-gray-700 dark:text-gray-300 font-medium">
              启用 AI 单币简评
            </label>
          </div>

          {config.enable_ai_signal_analysis_service && (
            <div className="space-y-4 pl-8 border-l-2 border-green-500/30">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API 端点 URL
                </label>
                <Input
                  type="text"
                  value={config.ai_signal_analysis_api_url}
                  onChange={(e) => handleChange('ai_signal_analysis_api_url', e.target.value)}
                  placeholder="https://api.example.com/v1"
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API 密钥
                </label>
                <Input
                  type="password"
                  value={config.ai_signal_analysis_api_key}
                  onChange={(e) => handleChange('ai_signal_analysis_api_key', e.target.value)}
                  placeholder="sk-..."
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  模型名称
                </label>
                <Input
                  type="text"
                  value={config.ai_signal_analysis_model}
                  onChange={(e) => handleChange('ai_signal_analysis_model', e.target.value)}
                  placeholder="gpt-4, claude-3-opus, etc."
                  className="w-full"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    生成间隔（秒）
                  </label>
                  <Input
                    type="number"
                    value={config.ai_signal_analysis_interval}
                    onChange={(e) => handleChange('ai_signal_analysis_interval', parseInt(e.target.value))}
                    min={300}
                    max={86400}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">AI 简评生成间隔</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    回溯时间（小时）
                  </label>
                  <Input
                    type="number"
                    value={config.ai_signal_analysis_lookback_hours}
                    onChange={(e) => handleChange('ai_signal_analysis_lookback_hours', parseInt(e.target.value))}
                    min={1}
                    max={168}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">分析历史数据时长</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </GlassCard>

      {/* AI Key Levels (主力位分析) */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <TrendingUp className="text-orange-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">AI 主力位分析</h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_ai_key_levels_service"
              checked={config.enable_ai_key_levels_service}
              onChange={(e) => handleChange('enable_ai_key_levels_service', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-orange-600 focus:ring-orange-500"
            />
            <label htmlFor="enable_ai_key_levels_service" className="text-gray-700 dark:text-gray-300 font-medium">
              启用 AI 主力位分析
            </label>
          </div>

          {config.enable_ai_key_levels_service && (
            <div className="space-y-4 pl-8 border-l-2 border-orange-500/30">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API 端点 URL
                </label>
                <Input
                  type="text"
                  value={config.ai_key_levels_api_url}
                  onChange={(e) => handleChange('ai_key_levels_api_url', e.target.value)}
                  placeholder="https://api.example.com/v1"
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API 密钥
                </label>
                <Input
                  type="password"
                  value={config.ai_key_levels_api_key}
                  onChange={(e) => handleChange('ai_key_levels_api_key', e.target.value)}
                  placeholder="sk-..."
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  模型名称
                </label>
                <Input
                  type="text"
                  value={config.ai_key_levels_model}
                  onChange={(e) => handleChange('ai_key_levels_model', e.target.value)}
                  placeholder="gpt-4, claude-3-opus, etc."
                  className="w-full"
                />
              </div>
            </div>
          )}
        </div>
      </GlassCard>

      {/* AI Overlays (图表叠加层) */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Zap className="text-cyan-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">AI 图表叠加层</h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_ai_overlays_service"
              checked={config.enable_ai_overlays_service}
              onChange={(e) => handleChange('enable_ai_overlays_service', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-cyan-600 focus:ring-cyan-500"
            />
            <label htmlFor="enable_ai_overlays_service" className="text-gray-700 dark:text-gray-300 font-medium">
              启用 AI 图表叠加层
            </label>
          </div>

          {config.enable_ai_overlays_service && (
            <div className="space-y-4 pl-8 border-l-2 border-cyan-500/30">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API 端点 URL
                </label>
                <Input
                  type="text"
                  value={config.ai_overlays_api_url}
                  onChange={(e) => handleChange('ai_overlays_api_url', e.target.value)}
                  placeholder="https://api.example.com/v1"
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API 密钥
                </label>
                <Input
                  type="password"
                  value={config.ai_overlays_api_key}
                  onChange={(e) => handleChange('ai_overlays_api_key', e.target.value)}
                  placeholder="sk-..."
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  模型名称
                </label>
                <Input
                  type="text"
                  value={config.ai_overlays_model}
                  onChange={(e) => handleChange('ai_overlays_model', e.target.value)}
                  placeholder="gpt-4, claude-3-opus, etc."
                  className="w-full"
                />
              </div>
            </div>
          )}
        </div>
      </GlassCard>

      {/* AI Market Analysis (市场宏观分析) */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Brain className="text-indigo-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">AI 市场宏观分析</h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_ai_market_analysis"
              checked={config.enable_ai_market_analysis}
              onChange={(e) => handleChange('enable_ai_market_analysis', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <label htmlFor="enable_ai_market_analysis" className="text-gray-700 dark:text-gray-300 font-medium">
              启用 AI 市场宏观分析
            </label>
          </div>

          {config.enable_ai_market_analysis && (
            <div className="space-y-4 pl-8 border-l-2 border-indigo-500/30">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API 端点 URL
                </label>
                <Input
                  type="text"
                  value={config.ai_market_analysis_api_url}
                  onChange={(e) => handleChange('ai_market_analysis_api_url', e.target.value)}
                  placeholder="https://api.example.com/v1"
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API 密钥
                </label>
                <Input
                  type="password"
                  value={config.ai_market_analysis_api_key}
                  onChange={(e) => handleChange('ai_market_analysis_api_key', e.target.value)}
                  placeholder="sk-..."
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  模型名称
                </label>
                <Input
                  type="text"
                  value={config.ai_market_analysis_model}
                  onChange={(e) => handleChange('ai_market_analysis_model', e.target.value)}
                  placeholder="gpt-4, claude-3-opus, etc."
                  className="w-full"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    生成间隔（秒）
                  </label>
                  <Input
                    type="number"
                    value={config.ai_market_analysis_interval}
                    onChange={(e) => handleChange('ai_market_analysis_interval', parseInt(e.target.value))}
                    min={300}
                    max={86400}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">市场分析生成间隔</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    回溯时间（小时）
                  </label>
                  <Input
                    type="number"
                    value={config.ai_market_analysis_lookback_hours}
                    onChange={(e) => handleChange('ai_market_analysis_lookback_hours', parseInt(e.target.value))}
                    min={1}
                    max={168}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">分析历史数据时长</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </GlassCard>
    </div>
  );
};

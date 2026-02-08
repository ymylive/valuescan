import React from 'react';
import { GlassCard } from '../shared';
import { Input } from '../ui';
import { Brain, Zap, TrendingUp, Activity } from 'lucide-react';
import { AIProtocol, AIServiceConfig } from '../../types/config';
import { parseFloatSafe, parseIntSafe } from '../../utils/number';

interface AIServiceConfigProps {
  config: AIServiceConfig;
  onChange: (config: AIServiceConfig) => void;
}

export const AIServiceConfigComponent: React.FC<AIServiceConfigProps> = ({ config, onChange }) => {
  const handleChange = <K extends keyof AIServiceConfig>(field: K, value: AIServiceConfig[K]) => {
    onChange({ ...config, [field]: value });
  };

  const renderProtocolToggle = (value: AIProtocol, onChangeValue: (next: AIProtocol) => void) => (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
        API 协议
      </label>
      <div className="flex flex-wrap gap-2">
        {[
          { value: 'auto' as const, label: '自动' },
          { value: 'compatible' as const, label: '兼容模式' },
          { value: 'responses' as const, label: 'Responses' },
        ].map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onChangeValue(option.value)}
            className={`px-3 py-2 rounded text-xs font-semibold border transition-colors ${
              value === option.value
                ? 'bg-gray-900 text-white border-gray-900'
                : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600'
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>
      <p className="text-xs text-gray-500 mt-1">自动模式会根据 URL 是否包含 /responses 自动判断协议</p>
    </div>
  );

  return (
    <div className="space-y-6">
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Activity className="text-yellow-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">AI 代理设置</h3>
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
            <p className="text-xs text-gray-500 mt-1">用于 AI API 访问的代理地址（可空）</p>
          </div>
        </div>
      </GlassCard>

      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Brain className="text-green-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">AI 简评服务</h3>
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
              启用 AI 简评
            </label>
          </div>

          {config.enable_ai_signal_analysis_service && (
            <div className="space-y-4 pl-8 border-l-2 border-green-500/30">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API 基础 URL
                </label>
                <Input
                  type="text"
                  value={config.ai_signal_analysis_api_url}
                  onChange={(e) => handleChange('ai_signal_analysis_api_url', e.target.value)}
                  placeholder="https://api.example.com/v1"
                  className="w-full"
                />
              </div>
              {renderProtocolToggle(
                config.ai_signal_analysis_api_protocol,
                (next) => handleChange('ai_signal_analysis_api_protocol', next),
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API Key
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
                    简评频率(小时)
                  </label>
                  <Input
                    type="number"
                    value={config.ai_signal_analysis_interval_hours}
                    onChange={(e) => handleChange('ai_signal_analysis_interval_hours', parseFloatSafe(e.target.value, config.ai_signal_analysis_interval_hours))}
                    min={0.1}
                    max={168}
                    step={0.1}
                    className="w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    回溯窗口(小时)
                  </label>
                  <Input
                    type="number"
                    value={config.ai_signal_analysis_lookback_hours}
                    onChange={(e) => handleChange('ai_signal_analysis_lookback_hours', parseIntSafe(e.target.value, config.ai_signal_analysis_lookback_hours))}
                    min={1}
                    max={168}
                    className="w-full"
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </GlassCard>

      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <TrendingUp className="text-orange-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">AI 主力位</h3>
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
              启用 AI 主力位
            </label>
          </div>

          {config.enable_ai_key_levels_service && (
            <div className="space-y-4 pl-8 border-l-2 border-orange-500/30">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API 基础 URL
                </label>
                <Input
                  type="text"
                  value={config.ai_key_levels_api_url}
                  onChange={(e) => handleChange('ai_key_levels_api_url', e.target.value)}
                  placeholder="https://api.example.com/v1"
                  className="w-full"
                />
              </div>
              {renderProtocolToggle(
                config.ai_key_levels_api_protocol,
                (next) => handleChange('ai_key_levels_api_protocol', next),
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API Key
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

      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Zap className="text-cyan-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">AI 形态叠加</h3>
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
              启用 AI 形态叠加
            </label>
          </div>

          {config.enable_ai_overlays_service && (
            <div className="space-y-4 pl-8 border-l-2 border-cyan-500/30">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API 基础 URL
                </label>
                <Input
                  type="text"
                  value={config.ai_overlays_api_url}
                  onChange={(e) => handleChange('ai_overlays_api_url', e.target.value)}
                  placeholder="https://api.example.com/v1"
                  className="w-full"
                />
              </div>
              {renderProtocolToggle(
                config.ai_overlays_api_protocol,
                (next) => handleChange('ai_overlays_api_protocol', next),
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API Key
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

      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Brain className="text-indigo-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">AI 市场分析</h3>
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
              启用 AI 市场分析
            </label>
          </div>

          {config.enable_ai_market_analysis && (
            <div className="space-y-4 pl-8 border-l-2 border-indigo-500/30">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API 基础 URL
                </label>
                <Input
                  type="text"
                  value={config.ai_market_analysis_api_url}
                  onChange={(e) => handleChange('ai_market_analysis_api_url', e.target.value)}
                  placeholder="https://api.example.com/v1"
                  className="w-full"
                />
              </div>
              {renderProtocolToggle(
                config.ai_market_analysis_api_protocol,
                (next) => handleChange('ai_market_analysis_api_protocol', next),
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API Key
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
                    分析频率(小时)
                  </label>
                  <Input
                    type="number"
                    value={config.ai_market_analysis_interval_hours}
                    onChange={(e) => handleChange('ai_market_analysis_interval_hours', parseFloatSafe(e.target.value, config.ai_market_analysis_interval_hours))}
                    min={0.1}
                    max={168}
                    step={0.1}
                    className="w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    回溯窗口(小时)
                  </label>
                  <Input
                    type="number"
                    value={config.ai_market_analysis_lookback_hours}
                    onChange={(e) => handleChange('ai_market_analysis_lookback_hours', parseIntSafe(e.target.value, config.ai_market_analysis_lookback_hours))}
                    min={1}
                    max={168}
                    className="w-full"
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </GlassCard>
    </div>
  );
};

import React from 'react';
import { useTranslation } from 'react-i18next';
import { GlassCard } from '../Common/GlassCard';
import { Input } from '../Common/Input';
import { Shield, TrendingUp, AlertTriangle, Target } from 'lucide-react';
import { TradingBotConfig, TRAILING_STOP_TYPES } from '../../types/config';

interface RiskManagementConfigProps {
  config: TradingBotConfig;
  onChange: (config: TradingBotConfig) => void;
}

export const RiskManagementConfig: React.FC<RiskManagementConfigProps> = ({ config, onChange }) => {
  const { t } = useTranslation();

  const handleChange = (field: keyof TradingBotConfig, value: any) => {
    onChange({ ...config, [field]: value });
  };

  const handleArrayChange = (field: keyof TradingBotConfig, value: string) => {
    const array = value.split(',').map(item => item.trim()).filter(item => item);
    onChange({ ...config, [field]: array });
  };

  return (
    <div className="space-y-6">
      {/* Risk Management */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Shield className="text-red-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">风险管理</h3>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                单个标的最大仓位比例（%）
              </label>
              <Input
                type="number"
                value={config.max_position_percent}
                onChange={(e) => handleChange('max_position_percent', parseFloat(e.target.value))}
                min={0.1}
                max={100}
                step={0.1}
                className="w-full"
              />
              <p className="text-xs text-gray-500 mt-1">占总资金的百分比</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                总仓位比例上限（%）
              </label>
              <Input
                type="number"
                value={config.max_total_position_percent}
                onChange={(e) => handleChange('max_total_position_percent', parseFloat(e.target.value))}
                min={0.1}
                max={100}
                step={0.1}
                className="w-full"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                主流币总仓位上限（%）
              </label>
              <Input
                type="number"
                value={config.major_total_position_percent}
                onChange={(e) => handleChange('major_total_position_percent', parseFloat(e.target.value))}
                min={0.1}
                max={100}
                step={0.1}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                山寨币总仓位上限（%）
              </label>
              <Input
                type="number"
                value={config.alt_total_position_percent}
                onChange={(e) => handleChange('alt_total_position_percent', parseFloat(e.target.value))}
                min={0.1}
                max={100}
                step={0.1}
                className="w-full"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                每日最大交易次数
              </label>
              <Input
                type="number"
                value={config.max_daily_trades}
                onChange={(e) => handleChange('max_daily_trades', parseInt(e.target.value))}
                min={1}
                max={100}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                每日最大亏损比例（%）
              </label>
              <Input
                type="number"
                value={config.max_daily_loss_percent}
                onChange={(e) => handleChange('max_daily_loss_percent', parseFloat(e.target.value))}
                min={0.1}
                max={50}
                step={0.1}
                className="w-full"
              />
            </div>
          </div>
        </div>
      </GlassCard>

      {/* Stop Loss & Take Profit */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Target className="text-orange-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">止损止盈配置</h3>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                固定止损百分比（%）
              </label>
              <Input
                type="number"
                value={config.stop_loss_percent}
                onChange={(e) => handleChange('stop_loss_percent', parseFloat(e.target.value))}
                min={0.1}
                max={10}
                step={0.1}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                第一目标盈利（%）
              </label>
              <Input
                type="number"
                value={config.take_profit_1_percent}
                onChange={(e) => handleChange('take_profit_1_percent', parseFloat(e.target.value))}
                min={0.1}
                max={50}
                step={0.1}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                第二目标盈利（%）
              </label>
              <Input
                type="number"
                value={config.take_profit_2_percent}
                onChange={(e) => handleChange('take_profit_2_percent', parseFloat(e.target.value))}
                min={0.1}
                max={100}
                step={0.1}
                className="w-full"
              />
            </div>
          </div>
        </div>
      </GlassCard>

      {/* Trailing Stop */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <TrendingUp className="text-green-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">移动止损配置</h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_trailing_stop"
              checked={config.enable_trailing_stop}
              onChange={(e) => handleChange('enable_trailing_stop', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-green-600 focus:ring-green-500"
            />
            <label htmlFor="enable_trailing_stop" className="text-gray-700 dark:text-gray-300 font-medium">
              启用移动止损
            </label>
          </div>

          {config.enable_trailing_stop && (
            <div className="space-y-4 pl-8 border-l-2 border-green-500/30">
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    激活阈值（%）
                  </label>
                  <Input
                    type="number"
                    value={config.trailing_stop_activation}
                    onChange={(e) => handleChange('trailing_stop_activation', parseFloat(e.target.value))}
                    min={0.1}
                    max={20}
                    step={0.1}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">盈利达到此值时激活</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    回调比例（%）
                  </label>
                  <Input
                    type="number"
                    value={config.trailing_stop_callback}
                    onChange={(e) => handleChange('trailing_stop_callback', parseFloat(e.target.value))}
                    min={0.1}
                    max={10}
                    step={0.1}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">从最高点回调触发</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    更新间隔（秒）
                  </label>
                  <Input
                    type="number"
                    value={config.trailing_stop_update_interval}
                    onChange={(e) => handleChange('trailing_stop_update_interval', parseInt(e.target.value))}
                    min={1}
                    max={60}
                    className="w-full"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  移动止损类型
                </label>
                <select
                  value={config.trailing_stop_type}
                  onChange={(e) => handleChange('trailing_stop_type', e.target.value)}
                  className="w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                >
                  {TRAILING_STOP_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}
        </div>
      </GlassCard>

      {/* Pyramiding Exit */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Target className="text-blue-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">分批止盈配置</h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_pyramiding_exit"
              checked={config.enable_pyramiding_exit}
              onChange={(e) => handleChange('enable_pyramiding_exit', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="enable_pyramiding_exit" className="text-gray-700 dark:text-gray-300 font-medium">
              启用分批止盈
            </label>
          </div>

          {config.enable_pyramiding_exit && (
            <div className="space-y-4 pl-8 border-l-2 border-blue-500/30">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  执行方式
                </label>
                <select
                  value={config.pyramiding_exit_execution}
                  onChange={(e) => handleChange('pyramiding_exit_execution', e.target.value)}
                  className="w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="orders">挂单（orders）</option>
                  <option value="market">市价（market）</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  分批止盈策略
                </label>
                <div className="space-y-2">
                  <p className="text-xs text-gray-500">格式：盈利百分比,平仓比例（每行一个，用逗号分隔）</p>
                  <textarea
                    value={config.pyramiding_exit_levels.map(([profit, ratio]) => `${profit},${ratio}`).join('\n')}
                    onChange={(e) => {
                      const levels = e.target.value.split('\n')
                        .map(line => line.trim())
                        .filter(line => line)
                        .map(line => {
                          const [profit, ratio] = line.split(',').map(v => parseFloat(v.trim()));
                          return [profit, ratio] as [number, number];
                        })
                        .filter(([profit, ratio]) => !isNaN(profit) && !isNaN(ratio));
                      handleChange('pyramiding_exit_levels', levels);
                    }}
                    rows={4}
                    className="w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                    placeholder="3.0,0.5&#10;5.0,0.5&#10;8.0,1.0"
                  />
                  <p className="text-xs text-gray-500">
                    示例：3.0,0.5 表示盈利3%时平仓50%；5.0,0.5 表示盈利5%时再平仓50%（剩余仓位的50%）
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </GlassCard>

      {/* Major Coins Strategy */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <TrendingUp className="text-purple-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">主流币独立策略</h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              主流币列表（逗号分隔，大写，不带后缀）
            </label>
            <Input
              type="text"
              value={config.major_coins.join(', ')}
              onChange={(e) => handleArrayChange('major_coins', e.target.value)}
              placeholder="BTC, ETH, BNB, SOL, XRP"
              className="w-full"
            />
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_major_coin_strategy"
              checked={config.enable_major_coin_strategy}
              onChange={(e) => handleChange('enable_major_coin_strategy', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
            />
            <label htmlFor="enable_major_coin_strategy" className="text-gray-700 dark:text-gray-300 font-medium">
              启用主流币独立策略
            </label>
          </div>

          {config.enable_major_coin_strategy && (
            <div className="space-y-4 pl-8 border-l-2 border-purple-500/30">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    主流币杠杆倍数（留空使用默认）
                  </label>
                  <Input
                    type="number"
                    value={config.major_coin_leverage || ''}
                    onChange={(e) => handleChange('major_coin_leverage', e.target.value ? parseInt(e.target.value) : null)}
                    min={1}
                    max={125}
                    placeholder="留空使用默认"
                    className="w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    主流币最大仓位比例（%，留空使用默认）
                  </label>
                  <Input
                    type="number"
                    value={config.major_coin_max_position_percent || ''}
                    onChange={(e) => handleChange('major_coin_max_position_percent', e.target.value ? parseFloat(e.target.value) : null)}
                    min={0.1}
                    max={100}
                    step={0.1}
                    placeholder="留空使用默认"
                    className="w-full"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  主流币止损百分比（%）
                </label>
                <Input
                  type="number"
                  value={config.major_coin_stop_loss_percent}
                  onChange={(e) => handleChange('major_coin_stop_loss_percent', parseFloat(e.target.value))}
                  min={0.1}
                  max={10}
                  step={0.1}
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  主流币金字塔止盈策略
                </label>
                <textarea
                  value={config.major_coin_pyramiding_exit_levels.map(([profit, ratio]) => `${profit},${ratio}`).join('\n')}
                  onChange={(e) => {
                    const levels = e.target.value.split('\n')
                      .map(line => line.trim())
                      .filter(line => line)
                      .map(line => {
                        const [profit, ratio] = line.split(',').map(v => parseFloat(v.trim()));
                        return [profit, ratio] as [number, number];
                      })
                      .filter(([profit, ratio]) => !isNaN(profit) && !isNaN(ratio));
                    handleChange('major_coin_pyramiding_exit_levels', levels);
                  }}
                  rows={3}
                  className="w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent font-mono text-sm"
                  placeholder="1.5,0.3&#10;2.5,0.4&#10;4.0,1.0"
                />
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="major_coin_enable_trailing_stop"
                  checked={config.major_coin_enable_trailing_stop}
                  onChange={(e) => handleChange('major_coin_enable_trailing_stop', e.target.checked)}
                  className="w-5 h-5 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                />
                <label htmlFor="major_coin_enable_trailing_stop" className="text-gray-700 dark:text-gray-300">
                  主流币启用移动止损
                </label>
              </div>

              {config.major_coin_enable_trailing_stop && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      移动止损激活（%）
                    </label>
                    <Input
                      type="number"
                      value={config.major_coin_trailing_stop_activation}
                      onChange={(e) => handleChange('major_coin_trailing_stop_activation', parseFloat(e.target.value))}
                      min={0.1}
                      max={20}
                      step={0.1}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      移动止损回调（%）
                    </label>
                    <Input
                      type="number"
                      value={config.major_coin_trailing_stop_callback}
                      onChange={(e) => handleChange('major_coin_trailing_stop_callback', parseFloat(e.target.value))}
                      min={0.1}
                      max={10}
                      step={0.1}
                      className="w-full"
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </GlassCard>

      {/* Safety Configuration */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <AlertTriangle className="text-red-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">安全配置</h3>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                最大单笔交易金额（USDT）
              </label>
              <Input
                type="number"
                value={config.max_single_trade_value}
                onChange={(e) => handleChange('max_single_trade_value', parseFloat(e.target.value))}
                min={10}
                max={100000}
                step={10}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                强制平仓保证金率（%）
              </label>
              <Input
                type="number"
                value={config.force_close_margin_ratio}
                onChange={(e) => handleChange('force_close_margin_ratio', parseFloat(e.target.value))}
                min={10}
                max={50}
                step={1}
                className="w-full"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_emergency_stop"
              checked={config.enable_emergency_stop}
              onChange={(e) => handleChange('enable_emergency_stop', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-red-600 focus:ring-red-500"
            />
            <label htmlFor="enable_emergency_stop" className="text-gray-700 dark:text-gray-300 font-medium">
              启用紧急停止按钮
            </label>
          </div>

          {config.enable_emergency_stop && (
            <div className="pl-8 border-l-2 border-red-500/30">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                紧急停止文件路径
              </label>
              <Input
                type="text"
                value={config.emergency_stop_file}
                onChange={(e) => handleChange('emergency_stop_file', e.target.value)}
                placeholder="STOP_TRADING"
                className="w-full"
              />
              <p className="text-xs text-gray-500 mt-1">创建此文件将立即停止所有交易</p>
            </div>
          )}
        </div>
      </GlassCard>
    </div>
  );
};

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { GlassCard } from '../Common/GlassCard';
import { Input } from '../Common/Input';
import { Bot, TrendingUp, TrendingDown, Shield, Settings, Zap } from 'lucide-react';
import { TradingBotConfig, MARGIN_TYPES, POSITION_SIDES, ORDER_TYPES, TRAILING_STOP_TYPES } from '../../types/config';

interface TradingBotConfigProps {
  config: TradingBotConfig;
  onChange: (config: TradingBotConfig) => void;
}

export const TradingBotConfigComponent: React.FC<TradingBotConfigProps> = ({ config, onChange }) => {
  const { t } = useTranslation();
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleChange = (field: keyof TradingBotConfig, value: any) => {
    onChange({ ...config, [field]: value });
  };

  const handleArrayChange = (field: keyof TradingBotConfig, value: string) => {
    const array = value.split(',').map(item => item.trim()).filter(item => item);
    onChange({ ...config, [field]: array });
  };

  return (
    <div className="space-y-6">
      {/* Binance API Configuration */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Bot className="text-yellow-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">币安 API 配置</h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              API Key
            </label>
            <Input
              type="password"
              value={config.binance_api_key}
              onChange={(e) => handleChange('binance_api_key', e.target.value)}
              placeholder="your_api_key_here"
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              API Secret
            </label>
            <Input
              type="password"
              value={config.binance_api_secret}
              onChange={(e) => handleChange('binance_api_secret', e.target.value)}
              placeholder="your_api_secret_here"
              className="w-full"
            />
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="use_testnet"
              checked={config.use_testnet}
              onChange={(e) => handleChange('use_testnet', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-yellow-600 focus:ring-yellow-500"
            />
            <label htmlFor="use_testnet" className="text-gray-700 dark:text-gray-300">
              使用测试网
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              SOCKS5 代理（可选）
            </label>
            <Input
              type="text"
              value={config.socks5_proxy}
              onChange={(e) => handleChange('socks5_proxy', e.target.value)}
              placeholder="socks5://127.0.0.1:1080"
              className="w-full"
            />
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="auto_proxy_binance"
              checked={config.auto_proxy_binance}
              onChange={(e) => handleChange('auto_proxy_binance', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-yellow-600 focus:ring-yellow-500"
            />
            <label htmlFor="auto_proxy_binance" className="text-gray-700 dark:text-gray-300">
              自动使用本地 SOCKS5 代理
            </label>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_proxy_fallback"
              checked={config.enable_proxy_fallback}
              onChange={(e) => handleChange('enable_proxy_fallback', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-yellow-600 focus:ring-yellow-500"
            />
            <label htmlFor="enable_proxy_fallback" className="text-gray-700 dark:text-gray-300">
              代理失败时自动切换直连
            </label>
          </div>
        </div>
      </GlassCard>

      {/* Contract Trading Configuration */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Settings className="text-blue-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">合约交易配置</h3>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                交易对后缀
              </label>
              <Input
                type="text"
                value={config.symbol_suffix}
                onChange={(e) => handleChange('symbol_suffix', e.target.value)}
                placeholder="USDT"
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                杠杆倍数（1-125）
              </label>
              <Input
                type="number"
                value={config.leverage}
                onChange={(e) => handleChange('leverage', parseInt(e.target.value))}
                min={1}
                max={125}
                className="w-full"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                保证金模式
              </label>
              <select
                value={config.margin_type}
                onChange={(e) => handleChange('margin_type', e.target.value)}
                className="w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {MARGIN_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                持仓方向
              </label>
              <select
                value={config.position_side}
                onChange={(e) => handleChange('position_side', e.target.value)}
                className="w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {POSITION_SIDES.map((side) => (
                  <option key={side.value} value={side.value}>
                    {side.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              币种黑名单（逗号分隔，大写，不带后缀）
            </label>
            <Input
              type="text"
              value={config.coin_blacklist.join(', ')}
              onChange={(e) => handleArrayChange('coin_blacklist', e.target.value)}
              placeholder="BTC, ETH, BNB"
              className="w-full"
            />
          </div>
        </div>
      </GlassCard>

      {/* Trading Strategies */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <TrendingUp className="text-green-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">交易策略</h3>
        </div>

        <div className="space-y-6">
          {/* Long Trading */}
          <div>
            <div className="flex items-center gap-3 mb-4">
              <input
                type="checkbox"
                id="long_trading_enabled"
                checked={config.long_trading_enabled}
                onChange={(e) => handleChange('long_trading_enabled', e.target.checked)}
                className="w-5 h-5 rounded border-gray-300 text-green-600 focus:ring-green-500"
              />
              <label htmlFor="long_trading_enabled" className="text-gray-700 dark:text-gray-300 font-medium text-lg">
                启用做多策略
              </label>
            </div>
          </div>

          {/* Short Trading */}
          <div>
            <div className="flex items-center gap-3 mb-4">
              <input
                type="checkbox"
                id="short_trading_enabled"
                checked={config.short_trading_enabled}
                onChange={(e) => handleChange('short_trading_enabled', e.target.checked)}
                className="w-5 h-5 rounded border-gray-300 text-red-600 focus:ring-red-500"
              />
              <label htmlFor="short_trading_enabled" className="text-gray-700 dark:text-gray-300 font-medium text-lg">
                启用做空策略
              </label>
            </div>

            {config.short_trading_enabled && (
              <div className="space-y-4 pl-8 border-l-2 border-red-500/30">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      做空止损百分比
                    </label>
                    <Input
                      type="number"
                      value={config.short_stop_loss_percent}
                      onChange={(e) => handleChange('short_stop_loss_percent', parseFloat(e.target.value))}
                      min={0.1}
                      max={10}
                      step={0.1}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      做空止盈百分比
                    </label>
                    <Input
                      type="number"
                      value={config.short_take_profit_percent}
                      onChange={(e) => handleChange('short_take_profit_percent', parseFloat(e.target.value))}
                      min={0.1}
                      max={20}
                      step={0.1}
                      className="w-full"
                    />
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="short_enable_pyramiding_exit"
                    checked={config.short_enable_pyramiding_exit}
                    onChange={(e) => handleChange('short_enable_pyramiding_exit', e.target.checked)}
                    className="w-5 h-5 rounded border-gray-300 text-red-600 focus:ring-red-500"
                  />
                  <label htmlFor="short_enable_pyramiding_exit" className="text-gray-700 dark:text-gray-300">
                    启用做空金字塔退出
                  </label>
                </div>
              </div>
            )}
          </div>
        </div>
      </GlassCard>

      {/* Signal Aggregation */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Zap className="text-purple-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">信号聚合配置</h3>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                信号匹配时间窗口（秒）
              </label>
              <Input
                type="number"
                value={config.signal_time_window}
                onChange={(e) => handleChange('signal_time_window', parseInt(e.target.value))}
                min={60}
                max={600}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                最低信号评分阈值（0-1）
              </label>
              <Input
                type="number"
                value={config.min_signal_score}
                onChange={(e) => handleChange('min_signal_score', parseFloat(e.target.value))}
                min={0}
                max={1}
                step={0.1}
                className="w-full"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_signal_state_cache"
              checked={config.enable_signal_state_cache}
              onChange={(e) => handleChange('enable_signal_state_cache', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
            />
            <label htmlFor="enable_signal_state_cache" className="text-gray-700 dark:text-gray-300">
              持久化信号状态
            </label>
          </div>

          {config.enable_signal_state_cache && (
            <div className="space-y-4 pl-8 border-l-2 border-purple-500/30">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  信号状态存储文件
                </label>
                <Input
                  type="text"
                  value={config.signal_state_file}
                  onChange={(e) => handleChange('signal_state_file', e.target.value)}
                  placeholder="data/signal_state.json"
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  已处理信号ID数量上限
                </label>
                <Input
                  type="number"
                  value={config.max_processed_signal_ids}
                  onChange={(e) => handleChange('max_processed_signal_ids', parseInt(e.target.value))}
                  min={1000}
                  max={10000}
                  className="w-full"
                />
              </div>
            </div>
          )}

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_fomo_intensify"
              checked={config.enable_fomo_intensify}
              onChange={(e) => handleChange('enable_fomo_intensify', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
            />
            <label htmlFor="enable_fomo_intensify" className="text-gray-700 dark:text-gray-300">
              启用 FOMO 加剧信号
            </label>
          </div>
        </div>
      </GlassCard>

      {/* Trading Execution */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Zap className="text-orange-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">交易执行配置</h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="auto_trading_enabled"
              checked={config.auto_trading_enabled}
              onChange={(e) => handleChange('auto_trading_enabled', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-orange-600 focus:ring-orange-500"
            />
            <label htmlFor="auto_trading_enabled" className="text-gray-700 dark:text-gray-300 font-medium text-lg">
              启用自动交易
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              订单类型
            </label>
            <select
              value={config.order_type}
              onChange={(e) => handleChange('order_type', e.target.value)}
              className="w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
            >
              {ORDER_TYPES.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="cancel_exit_orders_before_entry"
              checked={config.cancel_exit_orders_before_entry}
              onChange={(e) => handleChange('cancel_exit_orders_before_entry', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-orange-600 focus:ring-orange-500"
            />
            <label htmlFor="cancel_exit_orders_before_entry" className="text-gray-700 dark:text-gray-300">
              开仓前自动清理历史止盈/止损挂单
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              仓位精度
            </label>
            <Input
              type="number"
              value={config.position_precision}
              onChange={(e) => handleChange('position_precision', parseInt(e.target.value))}
              min={0}
              max={8}
              className="w-full"
            />
          </div>
        </div>
      </GlassCard>

      {/* Monitoring */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Shield className="text-cyan-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">监控配置</h3>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                持仓监控间隔（秒）
              </label>
              <Input
                type="number"
                value={config.position_monitor_interval}
                onChange={(e) => handleChange('position_monitor_interval', parseInt(e.target.value))}
                min={1}
                max={60}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                余额更新间隔（秒）
              </label>
              <Input
                type="number"
                value={config.balance_update_interval}
                onChange={(e) => handleChange('balance_update_interval', parseInt(e.target.value))}
                min={10}
                max={300}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                强平风险监控阈值（%）
              </label>
              <Input
                type="number"
                value={config.liquidation_warning_margin_ratio}
                onChange={(e) => handleChange('liquidation_warning_margin_ratio', parseFloat(e.target.value))}
                min={10}
                max={50}
                step={1}
                className="w-full"
              />
            </div>
          </div>
        </div>
      </GlassCard>
    </div>
  );
};

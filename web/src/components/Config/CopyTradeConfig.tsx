import React from 'react';
import { useTranslation } from 'react-i18next';
import { GlassCard } from '../Common/GlassCard';
import { Input } from '../Common/Input';
import { MessageSquare, Users, Filter, Bell, TrendingUp } from 'lucide-react';
import { CopyTradeConfig, COPYTRADE_MODES, POSITION_MODES, DIRECTION_FILTERS } from '../../types/config';

interface CopyTradeConfigProps {
  config: CopyTradeConfig;
  onChange: (config: CopyTradeConfig) => void;
}

export const CopyTradeConfigComponent: React.FC<CopyTradeConfigProps> = ({ config, onChange }) => {
  const { t } = useTranslation();

  const handleChange = (field: keyof CopyTradeConfig, value: any) => {
    onChange({ ...config, [field]: value });
  };

  const handleArrayChange = (field: keyof CopyTradeConfig, value: string, isNumber: boolean = false) => {
    const array = value.split(',').map(item => item.trim()).filter(item => item);
    const parsedArray = isNumber ? array.map(item => parseInt(item)).filter(n => !isNaN(n)) : array;
    onChange({ ...config, [field]: parsedArray });
  };

  return (
    <div className="space-y-6">
      {/* Telegram API Configuration */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <MessageSquare className="text-blue-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">Telegram API 配置</h3>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Telegram API ID
              </label>
              <Input
                type="number"
                value={config.telegram_api_id}
                onChange={(e) => handleChange('telegram_api_id', parseInt(e.target.value))}
                placeholder="从 my.telegram.org 获取"
                className="w-full"
              />
              <p className="text-xs text-gray-500 mt-1">访问 my.telegram.org 获取 API ID</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Telegram API Hash
              </label>
              <Input
                type="password"
                value={config.telegram_api_hash}
                onChange={(e) => handleChange('telegram_api_hash', e.target.value)}
                placeholder="从 my.telegram.org 获取"
                className="w-full"
              />
              <p className="text-xs text-gray-500 mt-1">访问 my.telegram.org 获取 API Hash</p>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              监控的群组/频道 ID 列表（逗号分隔）
            </label>
            <Input
              type="text"
              value={config.monitor_group_ids.join(', ')}
              onChange={(e) => handleArrayChange('monitor_group_ids', e.target.value, true)}
              placeholder="-1001234567890, -1009876543210"
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">
              监控这些群组/频道的交易信号。使用负数表示群组/频道 ID
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              信号来源用户 ID 过滤（逗号分隔，可选）
            </label>
            <Input
              type="text"
              value={config.signal_user_ids.join(', ')}
              onChange={(e) => handleArrayChange('signal_user_ids', e.target.value, true)}
              placeholder="123456789, 987654321"
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">
              仅跟随这些用户发送的信号。留空表示跟随所有用户
            </p>
          </div>
        </div>
      </GlassCard>

      {/* Copy Trade Settings */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <TrendingUp className="text-green-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">跟单设置</h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="copytrade_enabled"
              checked={config.copytrade_enabled}
              onChange={(e) => handleChange('copytrade_enabled', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-green-600 focus:ring-green-500"
            />
            <label htmlFor="copytrade_enabled" className="text-gray-700 dark:text-gray-300 font-medium">
              启用跟单交易
            </label>
          </div>

          {config.copytrade_enabled && (
            <div className="space-y-4 pl-8 border-l-2 border-green-500/30">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  跟单模式
                </label>
                <select
                  value={config.copytrade_mode}
                  onChange={(e) => handleChange('copytrade_mode', e.target.value)}
                  className="w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                >
                  {COPYTRADE_MODES.map((mode) => (
                    <option key={mode.value} value={mode.value}>
                      {mode.label}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  仅开仓：只跟随开仓信号；完全跟单：同时跟随开仓和平仓信号
                </p>
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="follow_close_signal"
                  checked={config.follow_close_signal}
                  onChange={(e) => handleChange('follow_close_signal', e.target.checked)}
                  className="w-5 h-5 rounded border-gray-300 text-green-600 focus:ring-green-500"
                />
                <label htmlFor="follow_close_signal" className="text-gray-700 dark:text-gray-300">
                  跟随平仓信号
                </label>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  仓位模式
                </label>
                <select
                  value={config.position_mode}
                  onChange={(e) => handleChange('position_mode', e.target.value)}
                  className="w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                >
                  {POSITION_MODES.map((mode) => (
                    <option key={mode.value} value={mode.value}>
                      {mode.label}
                    </option>
                  ))}
                </select>
              </div>

              {config.position_mode === 'RATIO' ? (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    跟单比例（0-1）
                  </label>
                  <Input
                    type="number"
                    value={config.position_ratio}
                    onChange={(e) => handleChange('position_ratio', parseFloat(e.target.value))}
                    min={0}
                    max={1}
                    step={0.01}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    相对于信号仓位的比例。例如 0.1 表示跟随 10% 的仓位
                  </p>
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    固定仓位金额（USDT）
                  </label>
                  <Input
                    type="number"
                    value={config.fixed_position_size}
                    onChange={(e) => handleChange('fixed_position_size', parseFloat(e.target.value))}
                    min={10}
                    step={10}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    每次跟单使用的固定金额
                  </p>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  第三目标止盈百分比（%）
                </label>
                <Input
                  type="number"
                  value={config.take_profit_3_percent}
                  onChange={(e) => handleChange('take_profit_3_percent', parseFloat(e.target.value))}
                  min={0.1}
                  max={100}
                  step={0.1}
                  className="w-full"
                />
              </div>
            </div>
          )}
        </div>
      </GlassCard>

      {/* Signal Filtering */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Filter className="text-purple-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">信号过滤</h3>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                最小杠杆倍数
              </label>
              <Input
                type="number"
                value={config.min_leverage}
                onChange={(e) => handleChange('min_leverage', parseInt(e.target.value))}
                min={1}
                max={125}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                最大杠杆倍数
              </label>
              <Input
                type="number"
                value={config.max_leverage}
                onChange={(e) => handleChange('max_leverage', parseInt(e.target.value))}
                min={1}
                max={125}
                className="w-full"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              方向过滤
            </label>
            <select
              value={config.direction_filter}
              onChange={(e) => handleChange('direction_filter', e.target.value)}
              className="w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              {DIRECTION_FILTERS.map((filter) => (
                <option key={filter.value} value={filter.value}>
                  {filter.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              选择只跟随做多、做空或两者都跟
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              币种白名单（逗号分隔，可选）
            </label>
            <Input
              type="text"
              value={config.symbol_whitelist.join(', ')}
              onChange={(e) => handleArrayChange('symbol_whitelist', e.target.value)}
              placeholder="BTC, ETH, BNB"
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">
              仅跟随这些币种的信号。留空表示跟随所有币种
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              币种黑名单（逗号分隔，可选）
            </label>
            <Input
              type="text"
              value={config.symbol_blacklist.join(', ')}
              onChange={(e) => handleArrayChange('symbol_blacklist', e.target.value)}
              placeholder="DOGE, SHIB"
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">
              不跟随这些币种的信号
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              信号延迟容忍（秒）
            </label>
            <Input
              type="number"
              value={config.max_signal_delay}
              onChange={(e) => handleChange('max_signal_delay', parseInt(e.target.value))}
              min={10}
              max={300}
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">
              超过此时间的信号将被忽略
            </p>
          </div>
        </div>
      </GlassCard>

      {/* Notifications */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Bell className="text-yellow-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">通知配置</h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              通知 Bot Token
            </label>
            <Input
              type="password"
              value={config.notify_bot_token}
              onChange={(e) => handleChange('notify_bot_token', e.target.value)}
              placeholder="从 @BotFather 获取"
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              通知 Chat ID
            </label>
            <Input
              type="text"
              value={config.notify_chat_id}
              onChange={(e) => handleChange('notify_chat_id', e.target.value)}
              placeholder="接收通知的 Chat ID"
              className="w-full"
            />
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="notify_new_signal"
              checked={config.notify_new_signal}
              onChange={(e) => handleChange('notify_new_signal', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-yellow-600 focus:ring-yellow-500"
            />
            <label htmlFor="notify_new_signal" className="text-gray-700 dark:text-gray-300">
              新信号通知
            </label>
          </div>
        </div>
      </GlassCard>
    </div>
  );
};

import React from 'react';
import { GlassCard } from '../Common/GlassCard';
import { Input } from '../Common/Input';
import { MessageSquare, Bell, Send } from 'lucide-react';
import { SignalMonitorConfig, TradingBotConfig } from '../../types/config';

interface NotificationConfigProps {
  signalConfig: SignalMonitorConfig;
  tradingConfig: TradingBotConfig;
  onSignalChange: (config: SignalMonitorConfig) => void;
  onTradingChange: (config: TradingBotConfig) => void;
}

export const NotificationConfig: React.FC<NotificationConfigProps> = ({
  signalConfig,
  tradingConfig,
  onSignalChange,
  onTradingChange,
}) => {
  const handleSignalChange = (field: keyof SignalMonitorConfig, value: any) => {
    onSignalChange({ ...signalConfig, [field]: value });
  };

  const handleTradingChange = (field: keyof TradingBotConfig, value: any) => {
    onTradingChange({ ...tradingConfig, [field]: value });
  };

  return (
    <div className="space-y-6">
      {/* Telegram Bot Configuration */}
      <GlassCard className="p-6 animate-slide-up">
        <div className="flex items-center gap-3 mb-6">
          <MessageSquare className="text-blue-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">Telegram Bot 配置</h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Bot Token
            </label>
            <Input
              type="password"
              value={signalConfig.telegram_bot_token}
              onChange={(e) => handleSignalChange('telegram_bot_token', e.target.value)}
              placeholder="从 @BotFather 获取"
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">从 Telegram @BotFather 获取 Bot Token</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Chat ID
            </label>
            <Input
              type="text"
              value={signalConfig.telegram_chat_id}
              onChange={(e) => handleSignalChange('telegram_chat_id', e.target.value)}
              placeholder="目标用户/频道 ID"
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">接收通知的 Telegram 用户或频道 ID</p>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_telegram"
              checked={signalConfig.enable_telegram}
              onChange={(e) => handleSignalChange('enable_telegram', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="enable_telegram" className="text-gray-700 dark:text-gray-300 font-medium">
              启用 Telegram 通知（总开关）
            </label>
          </div>
        </div>
      </GlassCard>

      {/* Signal Notifications */}
      <GlassCard className="p-6 animate-slide-up" style={{ animationDelay: '100ms' }}>
        <div className="flex items-center gap-3 mb-6">
          <Send className="text-purple-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">信号通知配置</h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="send_tg_in_mode_1"
              checked={signalConfig.send_tg_in_mode_1}
              onChange={(e) => handleSignalChange('send_tg_in_mode_1', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
            />
            <label htmlFor="send_tg_in_mode_1" className="text-gray-700 dark:text-gray-300">
              发送信号 TG 消息（模式1）
            </label>
          </div>
          <p className="text-xs text-gray-500 pl-8">当检测到新信号时发送 Telegram 通知</p>
        </div>
      </GlassCard>

      {/* Trading Notifications */}
      <GlassCard className="p-6 animate-slide-up" style={{ animationDelay: '200ms' }}>
        <div className="flex items-center gap-3 mb-6">
          <Bell className="text-green-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">交易通知配置</h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_telegram_alerts"
              checked={tradingConfig.enable_telegram_alerts}
              onChange={(e) => handleTradingChange('enable_telegram_alerts', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-green-600 focus:ring-green-500"
            />
            <label htmlFor="enable_telegram_alerts" className="text-gray-700 dark:text-gray-300 font-medium">
              启用 Telegram 重要通知
            </label>
          </div>
          <p className="text-xs text-gray-500 pl-8">发送系统错误、风险警告等重要通知</p>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_trade_notifications"
              checked={tradingConfig.enable_trade_notifications}
              onChange={(e) => handleTradingChange('enable_trade_notifications', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-green-600 focus:ring-green-500"
            />
            <label htmlFor="enable_trade_notifications" className="text-gray-700 dark:text-gray-300 font-medium">
              启用交易通知
            </label>
          </div>

          {tradingConfig.enable_trade_notifications && (
            <div className="space-y-3 pl-8 border-l-2 border-green-500/30 ml-2">
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="notify_open_position"
                  checked={tradingConfig.notify_open_position}
                  onChange={(e) => handleTradingChange('notify_open_position', e.target.checked)}
                  className="w-5 h-5 rounded border-gray-300 text-green-600 focus:ring-green-500"
                />
                <label htmlFor="notify_open_position" className="text-gray-700 dark:text-gray-300">
                  开仓通知
                </label>
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="notify_close_position"
                  checked={tradingConfig.notify_close_position}
                  onChange={(e) => handleTradingChange('notify_close_position', e.target.checked)}
                  className="w-5 h-5 rounded border-gray-300 text-green-600 focus:ring-green-500"
                />
                <label htmlFor="notify_close_position" className="text-gray-700 dark:text-gray-300">
                  平仓通知
                </label>
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="notify_stop_loss"
                  checked={tradingConfig.notify_stop_loss}
                  onChange={(e) => handleTradingChange('notify_stop_loss', e.target.checked)}
                  className="w-5 h-5 rounded border-gray-300 text-red-600 focus:ring-red-500"
                />
                <label htmlFor="notify_stop_loss" className="text-gray-700 dark:text-gray-300">
                  止损触发通知
                </label>
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="notify_take_profit"
                  checked={tradingConfig.notify_take_profit}
                  onChange={(e) => handleTradingChange('notify_take_profit', e.target.checked)}
                  className="w-5 h-5 rounded border-gray-300 text-green-600 focus:ring-green-500"
                />
                <label htmlFor="notify_take_profit" className="text-gray-700 dark:text-gray-300">
                  止盈触发通知
                </label>
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="notify_partial_close"
                  checked={tradingConfig.notify_partial_close}
                  onChange={(e) => handleTradingChange('notify_partial_close', e.target.checked)}
                  className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="notify_partial_close" className="text-gray-700 dark:text-gray-300">
                  部分平仓通知
                </label>
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="notify_errors"
                  checked={tradingConfig.notify_errors}
                  onChange={(e) => handleTradingChange('notify_errors', e.target.checked)}
                  className="w-5 h-5 rounded border-gray-300 text-red-600 focus:ring-red-500"
                />
                <label htmlFor="notify_errors" className="text-gray-700 dark:text-gray-300">
                  错误通知
                </label>
              </div>
            </div>
          )}
        </div>
      </GlassCard>
    </div>
  );
};

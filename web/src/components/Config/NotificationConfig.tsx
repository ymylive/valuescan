import React from 'react';
import { GlassCard } from '../shared';
import { Input } from '../ui';
import { MessageSquare, Send } from 'lucide-react';
import { SignalMonitorConfig } from '../../types/config';

interface NotificationConfigProps {
  signalConfig: SignalMonitorConfig;
  onSignalChange: (config: SignalMonitorConfig) => void;
}

export const NotificationConfig: React.FC<NotificationConfigProps> = ({
  signalConfig,
  onSignalChange,
}) => {
  const handleSignalChange = <K extends keyof SignalMonitorConfig>(field: K, value: SignalMonitorConfig[K]) => {
    onSignalChange({ ...signalConfig, [field]: value });
  };

  return (
    <div className="space-y-6">
      <GlassCard className="p-6 animate-slide-up">
        <div className="flex items-center gap-3 mb-6">
          <MessageSquare className="text-blue-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">Telegram Bot 设置</h3>
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
              placeholder="来自 @BotFather"
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Chat ID
            </label>
            <Input
              type="text"
              value={signalConfig.telegram_chat_id}
              onChange={(e) => handleSignalChange('telegram_chat_id', e.target.value)}
              placeholder="群组/用户 ID"
              className="w-full"
            />
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
              启用 Telegram 通知
            </label>
          </div>
        </div>
      </GlassCard>

      <GlassCard className="p-6 animate-slide-up" style={{ animationDelay: '100ms' }}>
        <div className="flex items-center gap-3 mb-6">
          <Send className="text-purple-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">推送策略</h3>
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
              启用 TG 推送模式 1
            </label>
          </div>
          <p className="text-xs text-gray-500 pl-8">用于信号类消息的 Telegram 推送</p>
        </div>
      </GlassCard>
    </div>
  );
};

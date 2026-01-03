import React, { useState } from 'react';
import { GlassCard } from '../Common/GlassCard';
import { Input } from '../Common/Input';
import { Key, Eye, EyeOff, AlertCircle, CheckCircle } from 'lucide-react';
import { EnvironmentConfig } from '../../types/config';

interface LoginCredentialsConfigProps {
  config: EnvironmentConfig;
  onChange: (config: EnvironmentConfig) => void;
}

export const LoginCredentialsConfig: React.FC<LoginCredentialsConfigProps> = ({ config, onChange }) => {
  const [showPassword, setShowPassword] = useState(false);
  const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');

  const handleChange = (field: keyof EnvironmentConfig, value: any) => {
    onChange({ ...config, [field]: value });
  };

  const handleTestCredentials = async () => {
    if (!config.valuescan_email || !config.valuescan_password) {
      setTestStatus('error');
      return;
    }

    setTestStatus('testing');

    // Simulate API test (replace with actual API call)
    setTimeout(() => {
      setTestStatus('success');
      setTimeout(() => setTestStatus('idle'), 3000);
    }, 1500);
  };

  const isFormValid = config.valuescan_email && config.valuescan_password;

  return (
    <div className="space-y-6">
      {/* Login Credentials */}
      <GlassCard className="p-6 animate-slide-up">
        <div className="flex items-center gap-3 mb-6">
          <Key className="text-blue-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">ValueScan 登录凭证</h3>
        </div>

        <div className="space-y-4">
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" size={20} />
              <div className="text-sm text-blue-800 dark:text-blue-200">
                <p className="font-medium mb-1">安全提示</p>
                <p>这些凭证用于保存 ValueScan 登录信息（可选）。凭证将被加密存储，不会触发自动刷新。</p>
              </div>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              邮箱地址
            </label>
            <Input
              type="email"
              value={config.valuescan_email}
              onChange={(e) => handleChange('valuescan_email', e.target.value)}
              placeholder="your-email@example.com"
              className="w-full"
              autoComplete="username"
            />
            <p className="text-xs text-gray-500 mt-1">用于登录 ValueScan 平台的邮箱</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              密码
            </label>
            <div className="relative">
              <Input
                type={showPassword ? 'text' : 'password'}
                value={config.valuescan_password}
                onChange={(e) => handleChange('valuescan_password', e.target.value)}
                placeholder="••••••••"
                className="w-full pr-12"
                autoComplete="current-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 smooth-transition"
                aria-label={showPassword ? '隐藏密码' : '显示密码'}
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-1">用于登录 ValueScan 平台的密码</p>
          </div>

          <div className="pt-2">
            <button
              onClick={handleTestCredentials}
              disabled={!isFormValid || testStatus === 'testing'}
              className={`
                w-full px-4 py-2 rounded-lg font-medium smooth-transition
                ${!isFormValid || testStatus === 'testing'
                  ? 'bg-gray-300 dark:bg-gray-700 text-gray-500 dark:text-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 text-white active:scale-98'
                }
              `}
            >
              {testStatus === 'testing' && (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  测试连接中...
                </span>
              )}
              {testStatus === 'success' && (
                <span className="flex items-center justify-center gap-2 text-green-600 dark:text-green-400">
                  <CheckCircle size={20} />
                  连接成功！
                </span>
              )}
              {testStatus === 'error' && (
                <span className="flex items-center justify-center gap-2 text-red-600 dark:text-red-400">
                  <AlertCircle size={20} />
                  连接失败
                </span>
              )}
              {testStatus === 'idle' && '测试连接'}
            </button>
          </div>
        </div>
      </GlassCard>

      {/* VPS Password */}
      <GlassCard className="p-6 animate-slide-up" style={{ animationDelay: '100ms' }}>
        <div className="flex items-center gap-3 mb-6">
          <Key className="text-purple-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">VPS 密码（可选）</h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              VPS 服务器密码
            </label>
            <Input
              type="password"
              value={config.valuescan_vps_password}
              onChange={(e) => handleChange('valuescan_vps_password', e.target.value)}
              placeholder="VPS 密码（如需远程部署）"
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">用于远程部署到 VPS 服务器（可选）</p>
          </div>
        </div>
      </GlassCard>
    </div>
  );
};

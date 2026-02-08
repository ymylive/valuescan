import React from 'react';
import { GlassCard } from '../shared';
import { Input, Button } from '../ui';
import { Server, FileText, Key } from 'lucide-react';
import { SystemConfig, LoggingConfig, LOG_LEVELS } from '../../types/config';
import { parseIntSafe } from '../../utils/number';

interface SystemConfigProps {
  systemConfig: SystemConfig;
  loggingConfig: LoggingConfig;
  onSystemChange: (config: SystemConfig) => void;
  onLoggingChange: (config: LoggingConfig) => void;
}

export const SystemConfigComponent: React.FC<SystemConfigProps> = ({
  systemConfig,
  loggingConfig,
  onSystemChange,
  onLoggingChange,
}) => {
  const handleSystemChange = <K extends keyof SystemConfig>(field: K, value: SystemConfig[K]) => {
    onSystemChange({ ...systemConfig, [field]: value });
  };

  const handleLoggingChange = <K extends keyof LoggingConfig>(field: K, value: LoggingConfig[K]) => {
    onLoggingChange({ ...loggingConfig, [field]: value });
  };

  const generateJwtSecret = () => {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+-=[]{}|;:,.<>?';
    let secret = '';
    for (let i = 0; i < 64; i += 1) {
      secret += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    handleSystemChange('jwt_secret', secret);
  };

  const generateEncryptionKey = () => {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    const base64 = btoa(String.fromCharCode(...array));
    handleSystemChange('data_encryption_key', base64);
  };

  const generateRsaKey = () => {
    const mockRsaKey = `-----BEGIN RSA PRIVATE KEY-----
${btoa(
      String.fromCharCode(...crypto.getRandomValues(new Uint8Array(128)))
    ).substring(0, 64)}
${btoa(
      String.fromCharCode(...crypto.getRandomValues(new Uint8Array(128)))
    ).substring(0, 64)}
${btoa(
      String.fromCharCode(...crypto.getRandomValues(new Uint8Array(128)))
    ).substring(0, 64)}
-----END RSA PRIVATE KEY-----`;
    handleSystemChange('rsa_private_key', mockRsaKey);
  };

  return (
    <div className="space-y-6">
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Server className="text-blue-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">服务端口与时区</h3>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                后端端口
              </label>
              <Input
                type="number"
                value={systemConfig.nofx_backend_port}
                onChange={(e) => handleSystemChange('nofx_backend_port', parseIntSafe(e.target.value, systemConfig.nofx_backend_port))}
                min={1024}
                max={65535}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                前端端口
              </label>
              <Input
                type="number"
                value={systemConfig.nofx_frontend_port}
                onChange={(e) => handleSystemChange('nofx_frontend_port', parseIntSafe(e.target.value, systemConfig.nofx_frontend_port))}
                min={1024}
                max={65535}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                时区
              </label>
              <Input
                type="text"
                value={systemConfig.nofx_timezone}
                onChange={(e) => handleSystemChange('nofx_timezone', e.target.value)}
                placeholder="Asia/Shanghai"
                className="w-full"
              />
            </div>
          </div>
        </div>
      </GlassCard>

      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Server className="text-purple-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">安全与密钥</h3>
        </div>

        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                JWT Secret（至少 32 位）
              </label>
              <Button
                onClick={generateJwtSecret}
                className="flex items-center gap-1 px-3 py-1 text-xs bg-purple-500 hover:bg-purple-600"
              >
                <Key size={14} />
                生成
              </Button>
            </div>
            <Input
              type="password"
              value={systemConfig.jwt_secret}
              onChange={(e) => handleSystemChange('jwt_secret', e.target.value)}
              placeholder="至少 32 位随机字符"
              className="w-full"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                数据加密密钥（Base64，32 字节）
              </label>
              <Button
                onClick={generateEncryptionKey}
                className="flex items-center gap-1 px-3 py-1 text-xs bg-purple-500 hover:bg-purple-600"
              >
                <Key size={14} />
                生成
              </Button>
            </div>
            <Input
              type="password"
              value={systemConfig.data_encryption_key}
              onChange={(e) => handleSystemChange('data_encryption_key', e.target.value)}
              placeholder="Base64 编码的 AES-256 密钥"
              className="w-full"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                RSA 私钥（PEM 格式）
              </label>
              <Button
                onClick={generateRsaKey}
                className="flex items-center gap-1 px-3 py-1 text-xs bg-purple-500 hover:bg-purple-600"
              >
                <Key size={14} />
                生成
              </Button>
            </div>
            <textarea
              value={systemConfig.rsa_private_key}
              onChange={(e) => handleSystemChange('rsa_private_key', e.target.value)}
              placeholder="-----BEGIN RSA PRIVATE KEY-----
...
-----END RSA PRIVATE KEY-----"
              rows={6}
              className="w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent font-mono text-sm"
            />
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="transport_encryption"
              checked={systemConfig.transport_encryption}
              onChange={(e) => handleSystemChange('transport_encryption', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
            />
            <label htmlFor="transport_encryption" className="text-gray-700 dark:text-gray-300">
              启用传输加密（强制 HTTPS）
            </label>
          </div>
        </div>
      </GlassCard>

      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <FileText className="text-green-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">日志配置</h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              日志等级
            </label>
            <select
              value={loggingConfig.log_level}
              onChange={(e) => handleLoggingChange('log_level', e.target.value)}
              className="w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            >
              {LOG_LEVELS.map((level) => (
                <option key={level.value} value={level.value}>
                  {level.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="log_to_file"
              checked={loggingConfig.log_to_file}
              onChange={(e) => handleLoggingChange('log_to_file', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-green-600 focus:ring-green-500"
            />
            <label htmlFor="log_to_file" className="text-gray-700 dark:text-gray-300">
              写入文件
            </label>
          </div>

          {loggingConfig.log_to_file && (
            <div className="space-y-4 pl-8 border-l-2 border-green-500/30">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  日志文件
                </label>
                <Input
                  type="text"
                  value={loggingConfig.log_file}
                  onChange={(e) => handleLoggingChange('log_file', e.target.value)}
                  placeholder="signal_monitor.log"
                  className="w-full"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    日志最大大小(字节)
                  </label>
                  <Input
                    type="number"
                    value={loggingConfig.log_max_size}
                    onChange={(e) => handleLoggingChange('log_max_size', parseIntSafe(e.target.value, loggingConfig.log_max_size))}
                    min={1048576}
                    max={104857600}
                    step={1048576}
                    className="w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    日志备份数量
                  </label>
                  <Input
                    type="number"
                    value={loggingConfig.log_backup_count}
                    onChange={(e) => handleLoggingChange('log_backup_count', parseIntSafe(e.target.value, loggingConfig.log_backup_count))}
                    min={1}
                    max={20}
                    className="w-full"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  日志格式
                </label>
                <Input
                  type="text"
                  value={loggingConfig.log_format}
                  onChange={(e) => handleLoggingChange('log_format', e.target.value)}
                  placeholder="%(asctime)s [%(levelname)s] %(message)s"
                  className="w-full font-mono text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  时间格式
                </label>
                <Input
                  type="text"
                  value={loggingConfig.log_date_format}
                  onChange={(e) => handleLoggingChange('log_date_format', e.target.value)}
                  placeholder="%Y-%m-%d %H:%M:%S"
                  className="w-full font-mono text-sm"
                />
              </div>
            </div>
          )}
        </div>
      </GlassCard>
    </div>
  );
};

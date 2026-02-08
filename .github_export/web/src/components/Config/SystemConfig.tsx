import React from 'react';
import { useTranslation } from 'react-i18next';
import { GlassCard } from '../Common/GlassCard';
import { Input } from '../Common/Input';
import { Button } from '../Common/Button';
import { Server, FileText, Network, Zap, Key } from 'lucide-react';
import { SystemConfig, LoggingConfig, TradingBotConfig, LOG_LEVELS } from '../../types/config';

interface SystemConfigProps {
  systemConfig: SystemConfig;
  loggingConfig: LoggingConfig;
  tradingConfig: TradingBotConfig;
  onSystemChange: (config: SystemConfig) => void;
  onLoggingChange: (config: LoggingConfig) => void;
  onTradingChange: (config: TradingBotConfig) => void;
}

export const SystemConfigComponent: React.FC<SystemConfigProps> = ({
  systemConfig,
  loggingConfig,
  tradingConfig,
  onSystemChange,
  onLoggingChange,
  onTradingChange,
}) => {
  const { t } = useTranslation();

  const handleSystemChange = (field: keyof SystemConfig, value: any) => {
    onSystemChange({ ...systemConfig, [field]: value });
  };

  const handleLoggingChange = (field: keyof LoggingConfig, value: any) => {
    onLoggingChange({ ...loggingConfig, [field]: value });
  };

  const handleTradingChange = (field: keyof TradingBotConfig, value: any) => {
    onTradingChange({ ...tradingConfig, [field]: value });
  };

  // Generate random JWT secret
  const generateJwtSecret = () => {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+-=[]{}|;:,.<>?';
    let secret = '';
    for (let i = 0; i < 64; i++) {
      secret += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    handleSystemChange('jwt_secret', secret);
  };

  // Generate random encryption key (Base64 encoded 32 bytes)
  const generateEncryptionKey = () => {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    const base64 = btoa(String.fromCharCode(...array));
    handleSystemChange('data_encryption_key', base64);
  };

  // Generate RSA key pair (simplified - in production use proper crypto library)
  const generateRsaKey = () => {
    // This is a placeholder - in production, you should use a proper crypto library
    // For now, we'll generate a mock RSA private key format
    const mockRsaKey = `-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA${btoa(String.fromCharCode(...crypto.getRandomValues(new Uint8Array(128)))).substring(0, 64)}
${btoa(String.fromCharCode(...crypto.getRandomValues(new Uint8Array(128)))).substring(0, 64)}
${btoa(String.fromCharCode(...crypto.getRandomValues(new Uint8Array(128)))).substring(0, 64)}
-----END RSA PRIVATE KEY-----`;
    handleSystemChange('rsa_private_key', mockRsaKey);
  };

  return (
    <div className="space-y-6">
      {/* Server Configuration */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Server className="text-blue-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">服务器配置</h3>
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
                onChange={(e) => handleSystemChange('nofx_backend_port', parseInt(e.target.value))}
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
                onChange={(e) => handleSystemChange('nofx_frontend_port', parseInt(e.target.value))}
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

      {/* Authentication Configuration */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Server className="text-purple-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">认证配置</h3>
        </div>

        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                JWT Secret（至少32字符）
              </label>
              <Button
                onClick={generateJwtSecret}
                className="flex items-center gap-1 px-3 py-1 text-xs bg-purple-500 hover:bg-purple-600"
              >
                <Key size={14} />
                生成密钥
              </Button>
            </div>
            <Input
              type="password"
              value={systemConfig.jwt_secret}
              onChange={(e) => handleSystemChange('jwt_secret', e.target.value)}
              placeholder="至少32字符的随机字符串"
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">用于签名 JWT Token 的密钥</p>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                数据加密密钥（Base64编码，32字节）
              </label>
              <Button
                onClick={generateEncryptionKey}
                className="flex items-center gap-1 px-3 py-1 text-xs bg-purple-500 hover:bg-purple-600"
              >
                <Key size={14} />
                生成密钥
              </Button>
            </div>
            <Input
              type="password"
              value={systemConfig.data_encryption_key}
              onChange={(e) => handleSystemChange('data_encryption_key', e.target.value)}
              placeholder="Base64 编码的 AES-256 密钥"
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">用于加密敏感数据的 AES-256 密钥</p>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                RSA 私钥（PEM格式）
              </label>
              <Button
                onClick={generateRsaKey}
                className="flex items-center gap-1 px-3 py-1 text-xs bg-purple-500 hover:bg-purple-600"
              >
                <Key size={14} />
                生成密钥
              </Button>
            </div>
            <textarea
              value={systemConfig.rsa_private_key}
              onChange={(e) => handleSystemChange('rsa_private_key', e.target.value)}
              placeholder="-----BEGIN RSA PRIVATE KEY-----&#10;...&#10;-----END RSA PRIVATE KEY-----"
              rows={6}
              className="w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent font-mono text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">用于客户端-服务器加密通信的 RSA 私钥</p>
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
              启用传输加密（需要 HTTPS）
            </label>
          </div>
        </div>
      </GlassCard>

      {/* Logging Configuration */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <FileText className="text-green-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">日志配置</h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              日志级别
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
              输出日志到文件
            </label>
          </div>

          {loggingConfig.log_to_file && (
            <div className="space-y-4 pl-8 border-l-2 border-green-500/30">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  日志文件路径
                </label>
                <Input
                  type="text"
                  value={loggingConfig.log_file}
                  onChange={(e) => handleLoggingChange('log_file', e.target.value)}
                  placeholder="valuescan.log"
                  className="w-full"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    日志文件最大大小（字节）
                  </label>
                  <Input
                    type="number"
                    value={loggingConfig.log_max_size}
                    onChange={(e) => handleLoggingChange('log_max_size', parseInt(e.target.value))}
                    min={1048576}
                    max={104857600}
                    step={1048576}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">默认 10MB = 10485760 字节</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    保留的日志文件数量
                  </label>
                  <Input
                    type="number"
                    value={loggingConfig.log_backup_count}
                    onChange={(e) => handleLoggingChange('log_backup_count', parseInt(e.target.value))}
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
                  日期格式
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

      {/* Advanced Trading Configuration */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Zap className="text-yellow-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">高级交易配置</h3>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                价格滑点容忍度（%）
              </label>
              <Input
                type="number"
                value={tradingConfig.slippage_tolerance}
                onChange={(e) => handleTradingChange('slippage_tolerance', parseFloat(e.target.value))}
                min={0.1}
                max={5}
                step={0.1}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                API 请求重试次数
              </label>
              <Input
                type="number"
                value={tradingConfig.api_retry_count}
                onChange={(e) => handleTradingChange('api_retry_count', parseInt(e.target.value))}
                min={1}
                max={10}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                API 请求超时（秒）
              </label>
              <Input
                type="number"
                value={tradingConfig.api_timeout}
                onChange={(e) => handleTradingChange('api_timeout', parseInt(e.target.value))}
                min={5}
                max={120}
                className="w-full"
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Binance 时间窗口（毫秒）
              </label>
              <Input
                type="number"
                value={tradingConfig.binance_recv_window_ms}
                onChange={(e) => handleTradingChange('binance_recv_window_ms', parseInt(e.target.value))}
                min={5000}
                max={60000}
                step={1000}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                自动对时间隔（秒）
              </label>
              <Input
                type="number"
                value={tradingConfig.binance_time_sync_interval}
                onChange={(e) => handleTradingChange('binance_time_sync_interval', parseInt(e.target.value))}
                min={60}
                max={3600}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                安全余量（毫秒）
              </label>
              <Input
                type="number"
                value={tradingConfig.binance_time_sync_safety_ms}
                onChange={(e) => handleTradingChange('binance_time_sync_safety_ms', parseInt(e.target.value))}
                min={500}
                max={5000}
                step={100}
                className="w-full"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="use_hedge_mode"
              checked={tradingConfig.use_hedge_mode}
              onChange={(e) => handleTradingChange('use_hedge_mode', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-yellow-600 focus:ring-yellow-500"
            />
            <label htmlFor="use_hedge_mode" className="text-gray-700 dark:text-gray-300">
              使用对冲模式
            </label>
          </div>
        </div>
      </GlassCard>

      {/* Performance Optimization */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Network className="text-cyan-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">性能优化</h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_websocket"
              checked={tradingConfig.enable_websocket}
              onChange={(e) => handleTradingChange('enable_websocket', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-cyan-600 focus:ring-cyan-500"
            />
            <label htmlFor="enable_websocket" className="text-gray-700 dark:text-gray-300 font-medium">
              启用 WebSocket 实时价格推送
            </label>
          </div>

          {tradingConfig.enable_websocket && (
            <div className="pl-8 border-l-2 border-cyan-500/30">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                WebSocket 重连间隔（秒）
              </label>
              <Input
                type="number"
                value={tradingConfig.websocket_reconnect_interval}
                onChange={(e) => handleTradingChange('websocket_reconnect_interval', parseInt(e.target.value))}
                min={1}
                max={60}
                className="w-full"
              />
            </div>
          )}
        </div>
      </GlassCard>

      {/* Backtest Configuration */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Server className="text-indigo-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">回测配置</h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_backtest"
              checked={tradingConfig.enable_backtest}
              onChange={(e) => handleTradingChange('enable_backtest', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <label htmlFor="enable_backtest" className="text-gray-700 dark:text-gray-300 font-medium">
              启用回测模式
            </label>
          </div>

          {tradingConfig.enable_backtest && (
            <div className="space-y-4 pl-8 border-l-2 border-indigo-500/30">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    回测起始日期
                  </label>
                  <Input
                    type="date"
                    value={tradingConfig.backtest_start_date}
                    onChange={(e) => handleTradingChange('backtest_start_date', e.target.value)}
                    className="w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    回测结束日期
                  </label>
                  <Input
                    type="date"
                    value={tradingConfig.backtest_end_date}
                    onChange={(e) => handleTradingChange('backtest_end_date', e.target.value)}
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

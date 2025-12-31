import React from 'react';
import { useTranslation } from 'react-i18next';
import { GlassCard } from '../Common/GlassCard';
import { Input } from '../Common/Input';
import { Activity, Chrome, RefreshCw, Network, BarChart3 } from 'lucide-react';
import { SignalMonitorConfig, LOGIN_METHODS } from '../../types/config';

interface SignalMonitorConfigProps {
  config: SignalMonitorConfig;
  onChange: (config: SignalMonitorConfig) => void;
}

export const SignalMonitorConfigComponent: React.FC<SignalMonitorConfigProps> = ({ config, onChange }) => {
  const { t } = useTranslation();

  const handleChange = (field: keyof SignalMonitorConfig, value: any) => {
    onChange({ ...config, [field]: value });
  };

  return (
    <div className="space-y-6">
      {/* Browser Configuration */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Chrome className="text-blue-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">浏览器配置</h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Chrome 调试端口
            </label>
            <Input
              type="number"
              value={config.chrome_debug_port}
              onChange={(e) => handleChange('chrome_debug_port', parseInt(e.target.value))}
              min={1024}
              max={65535}
              className="w-full"
            />
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="headless_mode"
              checked={config.headless_mode}
              onChange={(e) => handleChange('headless_mode', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="headless_mode" className="text-gray-700 dark:text-gray-300">
              无头模式（不显示浏览器窗口）
            </label>
          </div>
        </div>
      </GlassCard>

      {/* API Configuration */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Activity className="text-green-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">API 配置</h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              API 路径
            </label>
            <Input
              type="text"
              value={config.api_path}
              onChange={(e) => handleChange('api_path', e.target.value)}
              placeholder="api/account/message/getWarnMessage"
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              AI API 路径
            </label>
            <Input
              type="text"
              value={config.ai_api_path}
              onChange={(e) => handleChange('ai_api_path', e.target.value)}
              placeholder="api/account/message/aiMessagePage"
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              语言设置
            </label>
            <select
              value={config.language}
              onChange={(e) => handleChange('language', e.target.value)}
              className="w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            >
              <option value="zh">中文</option>
              <option value="en">English</option>
            </select>
          </div>
        </div>
      </GlassCard>

      {/* External Data APIs */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <BarChart3 className="text-purple-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">外部数据 API</h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              CoinMarketCap API Key
            </label>
            <Input
              type="password"
              value={config.coinmarketcap_api_key}
              onChange={(e) => handleChange('coinmarketcap_api_key', e.target.value)}
              placeholder="API Key"
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              CryptoCompare API Key
            </label>
            <Input
              type="password"
              value={config.cryptocompare_api_key}
              onChange={(e) => handleChange('cryptocompare_api_key', e.target.value)}
              placeholder="API Key"
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              CoinGecko API Key
            </label>
            <Input
              type="password"
              value={config.coingecko_api_key}
              onChange={(e) => handleChange('coingecko_api_key', e.target.value)}
              placeholder="API Key"
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Etherscan API Key（可选）
            </label>
            <Input
              type="password"
              value={config.etherscan_api_key}
              onChange={(e) => handleChange('etherscan_api_key', e.target.value)}
              placeholder="API Key"
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Crypto News API Key（可选）
            </label>
            <Input
              type="password"
              value={config.crypto_news_api_key}
              onChange={(e) => handleChange('crypto_news_api_key', e.target.value)}
              placeholder="API Key"
              className="w-full"
            />
          </div>
        </div>
      </GlassCard>

      {/* Polling Configuration */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <RefreshCw className="text-orange-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">轮询监控配置</h3>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                轮询间隔（秒）
              </label>
              <Input
                type="number"
                value={config.poll_interval}
                onChange={(e) => handleChange('poll_interval', parseInt(e.target.value))}
                min={1}
                max={300}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                请求超时（秒）
              </label>
              <Input
                type="number"
                value={config.request_timeout}
                onChange={(e) => handleChange('request_timeout', parseInt(e.target.value))}
                min={5}
                max={60}
                className="w-full"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                最大连续失败次数
              </label>
              <Input
                type="number"
                value={config.max_consecutive_failures}
                onChange={(e) => handleChange('max_consecutive_failures', parseInt(e.target.value))}
                min={1}
                max={20}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                失败冷却时间（秒）
              </label>
              <Input
                type="number"
                value={config.failure_cooldown}
                onChange={(e) => handleChange('failure_cooldown', parseInt(e.target.value))}
                min={10}
                max={600}
                className="w-full"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="auto_relogin"
              checked={config.auto_relogin}
              onChange={(e) => handleChange('auto_relogin', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-orange-600 focus:ring-orange-500"
            />
            <label htmlFor="auto_relogin" className="text-gray-700 dark:text-gray-300">
              Token 过期时自动重新登录
            </label>
          </div>

          {config.auto_relogin && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                重新登录冷却时间（秒）
              </label>
              <Input
                type="number"
                value={config.auto_relogin_cooldown}
                onChange={(e) => handleChange('auto_relogin_cooldown', parseInt(e.target.value))}
                min={300}
                max={7200}
                className="w-full"
              />
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                启动时信号最大年龄（秒）
              </label>
              <Input
                type="number"
                value={config.startup_signal_max_age_seconds}
                onChange={(e) => handleChange('startup_signal_max_age_seconds', parseInt(e.target.value))}
                min={60}
                max={3600}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                运行时信号最大年龄（秒）
              </label>
              <Input
                type="number"
                value={config.signal_max_age_seconds}
                onChange={(e) => handleChange('signal_max_age_seconds', parseInt(e.target.value))}
                min={60}
                max={3600}
                className="w-full"
              />
            </div>
          </div>
        </div>
      </GlassCard>

      {/* Token Refresh Configuration */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <RefreshCw className="text-cyan-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">Token 刷新配置</h3>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                刷新间隔（小时）
              </label>
              <Input
                type="number"
                value={config.token_refresh_interval_hours}
                onChange={(e) => handleChange('token_refresh_interval_hours', parseFloat(e.target.value))}
                min={0.1}
                max={24}
                step={0.1}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                安全余量（秒）
              </label>
              <Input
                type="number"
                value={config.token_refresh_safety_seconds}
                onChange={(e) => handleChange('token_refresh_safety_seconds', parseInt(e.target.value))}
                min={60}
                max={1800}
                className="w-full"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              登录方法
            </label>
            <select
              value={config.login_method}
              onChange={(e) => handleChange('login_method', e.target.value)}
              className="w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
            >
              {LOGIN_METHODS.map((method) => (
                <option key={method.value} value={method.value}>
                  {method.label}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                刷新窗口开始（小时）
              </label>
              <Input
                type="number"
                value={config.refresh_window_start}
                onChange={(e) => handleChange('refresh_window_start', parseInt(e.target.value))}
                min={0}
                max={23}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                刷新窗口结束（小时）
              </label>
              <Input
                type="number"
                value={config.refresh_window_end}
                onChange={(e) => handleChange('refresh_window_end', parseInt(e.target.value))}
                min={0}
                max={23}
                className="w-full"
              />
            </div>
          </div>
        </div>
      </GlassCard>

      {/* IPC Forwarding */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Network className="text-indigo-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">IPC 转发配置</h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_ipc_forwarding"
              checked={config.enable_ipc_forwarding}
              onChange={(e) => handleChange('enable_ipc_forwarding', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <label htmlFor="enable_ipc_forwarding" className="text-gray-700 dark:text-gray-300 font-medium">
              启用 IPC 转发（将信号转发给交易模块）
            </label>
          </div>

          {config.enable_ipc_forwarding && (
            <div className="space-y-4 pl-8 border-l-2 border-indigo-500/30">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    IPC 主机
                  </label>
                  <Input
                    type="text"
                    value={config.ipc_host}
                    onChange={(e) => handleChange('ipc_host', e.target.value)}
                    placeholder="127.0.0.1"
                    className="w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    IPC 端口
                  </label>
                  <Input
                    type="number"
                    value={config.ipc_port}
                    onChange={(e) => handleChange('ipc_port', parseInt(e.target.value))}
                    min={1024}
                    max={65535}
                    className="w-full"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    连接超时（秒）
                  </label>
                  <Input
                    type="number"
                    value={config.ipc_connect_timeout}
                    onChange={(e) => handleChange('ipc_connect_timeout', parseFloat(e.target.value))}
                    min={0.5}
                    max={10}
                    step={0.5}
                    className="w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    重试延迟（秒）
                  </label>
                  <Input
                    type="number"
                    value={config.ipc_retry_delay}
                    onChange={(e) => handleChange('ipc_retry_delay', parseFloat(e.target.value))}
                    min={0.5}
                    max={10}
                    step={0.5}
                    className="w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    最大重试次数
                  </label>
                  <Input
                    type="number"
                    value={config.ipc_max_retries}
                    onChange={(e) => handleChange('ipc_max_retries', parseInt(e.target.value))}
                    min={1}
                    max={10}
                    className="w-full"
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </GlassCard>

      {/* Chart Features */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <BarChart3 className="text-pink-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">图表功能配置</h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_pro_chart"
              checked={config.enable_pro_chart}
              onChange={(e) => handleChange('enable_pro_chart', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-pink-600 focus:ring-pink-500"
            />
            <label htmlFor="enable_pro_chart" className="text-gray-700 dark:text-gray-300">
              启用 Pro 图表（本地生成K线+热力图+资金流）
            </label>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_ai_key_levels"
              checked={config.enable_ai_key_levels}
              onChange={(e) => handleChange('enable_ai_key_levels', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-pink-600 focus:ring-pink-500"
            />
            <label htmlFor="enable_ai_key_levels" className="text-gray-700 dark:text-gray-300 font-medium">
              启用 AI 主力位分析（开启后忽视本地算法）
            </label>
          </div>
          <p className="text-xs text-gray-500 ml-8 -mt-2">
            使用 AI 分析并输出主力位坐标，替代本地算法计算
          </p>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_ai_overlays"
              checked={config.enable_ai_overlays}
              onChange={(e) => handleChange('enable_ai_overlays', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-pink-600 focus:ring-pink-500"
            />
            <label htmlFor="enable_ai_overlays" className="text-gray-700 dark:text-gray-300 font-medium">
              启用 AI 辅助线绘制（开启后忽视本地算法）
            </label>
          </div>
          <p className="text-xs text-gray-500 ml-8 -mt-2">
            使用 AI 生成图表叠加层和辅助线，替代本地算法绘制
          </p>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_ai_signal_analysis"
              checked={config.enable_ai_signal_analysis}
              onChange={(e) => handleChange('enable_ai_signal_analysis', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-pink-600 focus:ring-pink-500"
            />
            <label htmlFor="enable_ai_signal_analysis" className="text-gray-700 dark:text-gray-300">
              启用 AI 单币简评
            </label>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_tradingview_chart"
              checked={config.enable_tradingview_chart}
              onChange={(e) => handleChange('enable_tradingview_chart', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-pink-600 focus:ring-pink-500"
            />
            <label htmlFor="enable_tradingview_chart" className="text-gray-700 dark:text-gray-300">
              启用 TradingView 图表生成
            </label>
          </div>

          {config.enable_tradingview_chart && (
            <div className="space-y-4 pl-8 border-l-2 border-pink-500/30">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  chart-img.com API Key
                </label>
                <Input
                  type="password"
                  value={config.chart_img_api_key}
                  onChange={(e) => handleChange('chart_img_api_key', e.target.value)}
                  placeholder="API Key"
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  TradingView 布局 ID
                </label>
                <Input
                  type="text"
                  value={config.chart_img_layout_id}
                  onChange={(e) => handleChange('chart_img_layout_id', e.target.value)}
                  placeholder="oeTZqtUR"
                  className="w-full"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    图表宽度（像素）
                  </label>
                  <Input
                    type="number"
                    value={config.chart_img_width}
                    onChange={(e) => handleChange('chart_img_width', parseInt(e.target.value))}
                    min={400}
                    max={2000}
                    className="w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    图表高度（像素）
                  </label>
                  <Input
                    type="number"
                    value={config.chart_img_height}
                    onChange={(e) => handleChange('chart_img_height', parseInt(e.target.value))}
                    min={300}
                    max={1500}
                    className="w-full"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  图表生成超时（秒）
                </label>
                <Input
                  type="number"
                  value={config.chart_img_timeout}
                  onChange={(e) => handleChange('chart_img_timeout', parseInt(e.target.value))}
                  min={30}
                  max={300}
                  className="w-full"
                />
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="auto_delete_charts"
                  checked={config.auto_delete_charts}
                  onChange={(e) => handleChange('auto_delete_charts', e.target.checked)}
                  className="w-5 h-5 rounded border-gray-300 text-pink-600 focus:ring-pink-500"
                />
                <label htmlFor="auto_delete_charts" className="text-gray-700 dark:text-gray-300">
                  自动删除生成的图表文件
                </label>
              </div>
            </div>
          )}
        </div>
      </GlassCard>

      {/* Network Proxy */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Network className="text-teal-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">网络代理配置</h3>
        </div>

        <div className="space-y-4">
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
            <p className="text-xs text-gray-500 mt-1">用于访问币安 API</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              HTTP/HTTPS 代理（可选）
            </label>
            <Input
              type="text"
              value={config.http_proxy}
              onChange={(e) => handleChange('http_proxy', e.target.value)}
              placeholder="http://127.0.0.1:7890"
              className="w-full"
            />
          </div>
        </div>
      </GlassCard>
    </div>
  );
};

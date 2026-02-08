import React from 'react';
import { useTranslation } from 'react-i18next';
import { GlassCard } from '../Common/GlassCard';
import { Input } from '../Common/Input';
import { Activity, Chrome, RefreshCw, Network, BarChart3 } from 'lucide-react';
import { SignalMonitorConfig } from '../../types/config';

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

          {/* 主力位数据源选择（互斥，只能选择一个） */}
          <div className="space-y-4 pl-4 border-l-2 border-green-500/30">
            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
              主力位数据源（三选一）
            </h4>
            <p className="text-xs text-gray-500 mb-4">
              选择图表主力位线和 AI 分析使用的数据源，只能启用其中一个
            </p>
            
            {/* ValuScan 主力位（推荐，默认） */}
            <div className="p-3 rounded-lg border-2 border-green-500 bg-green-50 dark:bg-green-900/20">
              <div className="flex items-center gap-3">
                <input
                  type="radio"
                  name="key_levels_source"
                  id="key_levels_valuescan"
                  checked={config.enable_valuescan_key_levels && !config.enable_ai_key_levels}
                  onChange={() => {
                    handleChange('enable_valuescan_key_levels', true);
                    handleChange('valuescan_key_levels_as_primary', true);
                    handleChange('enable_ai_key_levels', false);
                  }}
                  className="w-5 h-5 text-green-600 focus:ring-green-500"
                />
                <label htmlFor="key_levels_valuescan" className="text-gray-700 dark:text-gray-300 font-medium">
                  🟢 ValuScan 主力位（推荐）
                </label>
              </div>
              <p className="text-xs text-gray-500 ml-8 mt-1">
                使用 ValuScan API 提供的主力位数据，数据更准确可靠
              </p>
            </div>

            {/* AI 主力位 */}
            <div className="p-3 rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3">
                <input
                  type="radio"
                  name="key_levels_source"
                  id="key_levels_ai"
                  checked={config.enable_ai_key_levels && !config.enable_valuescan_key_levels}
                  onChange={() => {
                    handleChange('enable_valuescan_key_levels', false);
                    handleChange('valuescan_key_levels_as_primary', false);
                    handleChange('enable_ai_key_levels', true);
                  }}
                  className="w-5 h-5 text-pink-600 focus:ring-pink-500"
                />
                <label htmlFor="key_levels_ai" className="text-gray-700 dark:text-gray-300 font-medium">
                  🤖 AI 主力位
                </label>
              </div>
              <p className="text-xs text-gray-500 ml-8 mt-1">
                使用 AI 分析并输出主力位坐标
              </p>
            </div>

            {/* 本地算法主力位 */}
            <div className="p-3 rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3">
                <input
                  type="radio"
                  name="key_levels_source"
                  id="key_levels_local"
                  checked={!config.enable_valuescan_key_levels && !config.enable_ai_key_levels}
                  onChange={() => {
                    handleChange('enable_valuescan_key_levels', false);
                    handleChange('valuescan_key_levels_as_primary', false);
                    handleChange('enable_ai_key_levels', false);
                  }}
                  className="w-5 h-5 text-gray-600 focus:ring-gray-500"
                />
                <label htmlFor="key_levels_local" className="text-gray-700 dark:text-gray-300 font-medium">
                  📊 本地算法主力位
                </label>
              </div>
              <p className="text-xs text-gray-500 ml-8 mt-1">
                使用本地算法计算主力位（不推荐）
              </p>
            </div>

            {/* AI 辅助线（独立选项） */}
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="enable_ai_overlays"
                  checked={config.enable_ai_overlays}
                  onChange={(e) => handleChange('enable_ai_overlays', e.target.checked)}
                  className="w-5 h-5 rounded border-gray-300 text-pink-600 focus:ring-pink-500"
                />
                <label htmlFor="enable_ai_overlays" className="text-gray-700 dark:text-gray-300 font-medium">
                  使用 AI 辅助线
                </label>
              </div>
              <p className="text-xs text-gray-500 ml-8 mt-1">
                使用 AI 生成图表叠加层和辅助线
              </p>
            </div>

            {/* ValuScan 天数配置（仅当选择 ValuScan 时显示） */}
            {config.enable_valuescan_key_levels && (
              <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 space-y-3">

                <div className="flex items-center gap-3 ml-4">
                  <label htmlFor="valuescan_key_levels_days" className="text-sm text-gray-600 dark:text-gray-400 w-32">
                    图表主力位天数
                  </label>
                  <input
                    type="number"
                    id="valuescan_key_levels_days"
                    value={config.valuescan_key_levels_days}
                    onChange={(e) => handleChange('valuescan_key_levels_days', parseInt(e.target.value) || 7)}
                    disabled={!config.enable_valuescan_key_levels}
                    min={1}
                    max={30}
                    className="w-20 px-2 py-1 text-sm border rounded dark:bg-gray-700 dark:border-gray-600 dark:text-white disabled:opacity-50"
                  />
                    <span className="text-xs text-gray-500">days (default 7)</span>
                </div>

                <div className="flex items-center gap-3 ml-4">
                  <label htmlFor="valuescan_ai_analysis_days" className="text-sm text-gray-600 dark:text-gray-400 w-32">
                    AI分析天数
                  </label>
                  <input
                    type="number"
                    id="valuescan_ai_analysis_days"
                    value={config.valuescan_ai_analysis_days}
                    onChange={(e) => handleChange('valuescan_ai_analysis_days', parseInt(e.target.value) || 15)}
                    disabled={!config.enable_valuescan_key_levels}
                    min={7}
                    max={90}
                    className="w-20 px-2 py-1 text-sm border rounded dark:bg-gray-700 dark:border-gray-600 dark:text-white disabled:opacity-50"
                  />
                    <span className="text-xs text-gray-500">days (default 15)</span>
                </div>
              </div>
            )}
          </div>

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

          {config.enable_ai_signal_analysis && (
            <div className="space-y-3 pl-8 border-l-2 border-pink-500/30">
              <div className="flex items-center gap-3">
                <label htmlFor="ai_brief_wait_timeout_seconds" className="text-sm text-gray-600 dark:text-gray-400 w-40">
                  AI简评等待超时
                </label>
                <input
                  type="number"
                  id="ai_brief_wait_timeout_seconds"
                  value={config.ai_brief_wait_timeout_seconds}
                  onChange={(e) => handleChange('ai_brief_wait_timeout_seconds', parseInt(e.target.value) || 90)}
                  min={90}
                  max={300}
                  className="w-24 px-2 py-1 text-sm border rounded dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                />
                <span className="text-xs text-gray-500">秒 (默认90秒)</span>
              </div>

              <div className="flex items-center gap-3">
                <label htmlFor="bull_bear_signal_ttl_seconds" className="text-sm text-gray-600 dark:text-gray-400 w-40">
                  看涨/看跌信号有效期
                </label>
                <input
                  type="number"
                  id="bull_bear_signal_ttl_seconds"
                  value={config.bull_bear_signal_ttl_seconds}
                  onChange={(e) => handleChange('bull_bear_signal_ttl_seconds', parseInt(e.target.value) || 86400)}
                  min={3600}
                  max={172800}
                  className="w-24 px-2 py-1 text-sm border rounded dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                />
                <span className="text-xs text-gray-500">秒 (默认86400秒)</span>
              </div>
            </div>
          )}

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

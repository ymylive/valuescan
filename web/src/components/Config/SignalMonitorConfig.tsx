import React from 'react';
import { Activity, BarChart3, Network, RefreshCw } from 'lucide-react';
import { GlassCard } from '../shared';
import { Input } from '../ui';
import { SignalMonitorConfig } from '../../types/config';
import { parseFloatSafe, parseIntSafe } from '../../utils/number';

interface SignalMonitorConfigProps {
  config: SignalMonitorConfig;
  onChange: (config: SignalMonitorConfig) => void;
}

export const SignalMonitorConfigComponent: React.FC<SignalMonitorConfigProps> = ({ config, onChange }) => {
  const handleChange = <K extends keyof SignalMonitorConfig>(field: K, value: SignalMonitorConfig[K]) => {
    onChange({ ...config, [field]: value });
  };

  return (
    <div className="space-y-6">
      <GlassCard className="p-6">
        <div className="mb-6 flex items-center gap-3">
          <Activity className="text-green-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">Runtime Settings</h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">Language</label>
            <select
              value={config.language}
              onChange={(e) => handleChange('language', e.target.value)}
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-green-500 dark:border-gray-600 dark:bg-gray-800"
            >
              <option value="zh">中文</option>
              <option value="en">English</option>
            </select>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
              AI Signal Interval (minutes)
            </label>
            <Input
              type="number"
              value={config.ai_signal_interval_minutes}
              onChange={(e) => handleChange('ai_signal_interval_minutes', parseIntSafe(e.target.value, config.ai_signal_interval_minutes))}
              min={1}
              max={1440}
              className="w-full"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
                Startup Signal Max Age (sec)
              </label>
              <Input
                type="number"
                value={config.startup_signal_max_age_seconds}
                onChange={(e) => handleChange('startup_signal_max_age_seconds', parseIntSafe(e.target.value, config.startup_signal_max_age_seconds))}
                min={60}
                max={3600}
                className="w-full"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
                Runtime Signal Max Age (sec)
              </label>
              <Input
                type="number"
                value={config.signal_max_age_seconds}
                onChange={(e) => handleChange('signal_max_age_seconds', parseIntSafe(e.target.value, config.signal_max_age_seconds))}
                min={60}
                max={3600}
                className="w-full"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="realtime_market_enabled"
              checked={config.realtime_market_enabled}
              onChange={(e) => handleChange('realtime_market_enabled', e.target.checked)}
              className="h-5 w-5 rounded border-gray-300 text-green-600 focus:ring-green-500"
            />
            <label htmlFor="realtime_market_enabled" className="text-gray-700 dark:text-gray-300">
              Enable realtime market monitoring
            </label>
          </div>
        </div>
      </GlassCard>

      <GlassCard className="p-6">
        <div className="mb-6 flex items-center gap-3">
          <BarChart3 className="text-purple-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">External Data APIs</h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">CoinMarketCap API Key</label>
            <Input
              type="password"
              value={config.coinmarketcap_api_key}
              onChange={(e) => handleChange('coinmarketcap_api_key', e.target.value)}
              placeholder="API Key"
              className="w-full"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">CryptoCompare API Key</label>
            <Input
              type="password"
              value={config.cryptocompare_api_key}
              onChange={(e) => handleChange('cryptocompare_api_key', e.target.value)}
              placeholder="API Key"
              className="w-full"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">CoinGecko API Key</label>
            <Input
              type="password"
              value={config.coingecko_api_key}
              onChange={(e) => handleChange('coingecko_api_key', e.target.value)}
              placeholder="API Key"
              className="w-full"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">Etherscan API Key (optional)</label>
            <Input
              type="password"
              value={config.etherscan_api_key}
              onChange={(e) => handleChange('etherscan_api_key', e.target.value)}
              placeholder="API Key"
              className="w-full"
            />
          </div>
        </div>
      </GlassCard>

      <GlassCard className="p-6">
        <div className="mb-6 flex items-center gap-3">
          <Network className="text-indigo-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">IPC Forwarding</h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_ipc_forwarding"
              checked={config.enable_ipc_forwarding}
              onChange={(e) => handleChange('enable_ipc_forwarding', e.target.checked)}
              className="h-5 w-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <label htmlFor="enable_ipc_forwarding" className="font-medium text-gray-700 dark:text-gray-300">
              Enable IPC forwarding
            </label>
          </div>

          {config.enable_ipc_forwarding && (
            <div className="space-y-4 border-l-2 border-indigo-500/30 pl-8">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">IPC Host</label>
                  <Input
                    type="text"
                    value={config.ipc_host}
                    onChange={(e) => handleChange('ipc_host', e.target.value)}
                    placeholder="127.0.0.1"
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">IPC Port</label>
                  <Input
                    type="number"
                    value={config.ipc_port}
                    onChange={(e) => handleChange('ipc_port', parseIntSafe(e.target.value, config.ipc_port))}
                    min={1024}
                    max={65535}
                    className="w-full"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">Connect Timeout (s)</label>
                  <Input
                    type="number"
                    value={config.ipc_connect_timeout}
                    onChange={(e) => handleChange('ipc_connect_timeout', parseFloatSafe(e.target.value, config.ipc_connect_timeout))}
                    min={0.5}
                    max={10}
                    step={0.5}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">Retry Delay (s)</label>
                  <Input
                    type="number"
                    value={config.ipc_retry_delay}
                    onChange={(e) => handleChange('ipc_retry_delay', parseFloatSafe(e.target.value, config.ipc_retry_delay))}
                    min={0.5}
                    max={10}
                    step={0.5}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">Max Retries</label>
                  <Input
                    type="number"
                    value={config.ipc_max_retries}
                    onChange={(e) => handleChange('ipc_max_retries', parseIntSafe(e.target.value, config.ipc_max_retries))}
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

      <GlassCard className="p-6">
        <div className="mb-6 flex items-center gap-3">
          <RefreshCw className="text-pink-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">Chart Features</h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_pro_chart"
              checked={config.enable_pro_chart}
              onChange={(e) => handleChange('enable_pro_chart', e.target.checked)}
              className="h-5 w-5 rounded border-gray-300 text-pink-600 focus:ring-pink-500"
            />
            <label htmlFor="enable_pro_chart" className="text-gray-700 dark:text-gray-300">
              Enable Pro chart rendering
            </label>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_ai_key_levels"
              checked={config.enable_ai_key_levels}
              onChange={(e) => handleChange('enable_ai_key_levels', e.target.checked)}
              className="h-5 w-5 rounded border-gray-300 text-pink-600 focus:ring-pink-500"
            />
            <label htmlFor="enable_ai_key_levels" className="text-gray-700 dark:text-gray-300">
              Use AI key levels
            </label>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_ai_overlays"
              checked={config.enable_ai_overlays}
              onChange={(e) => handleChange('enable_ai_overlays', e.target.checked)}
              className="h-5 w-5 rounded border-gray-300 text-pink-600 focus:ring-pink-500"
            />
            <label htmlFor="enable_ai_overlays" className="text-gray-700 dark:text-gray-300">
              Use AI overlays
            </label>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_ai_signal_analysis"
              checked={config.enable_ai_signal_analysis}
              onChange={(e) => handleChange('enable_ai_signal_analysis', e.target.checked)}
              className="h-5 w-5 rounded border-gray-300 text-pink-600 focus:ring-pink-500"
            />
            <label htmlFor="enable_ai_signal_analysis" className="text-gray-700 dark:text-gray-300">
              Enable AI per-signal analysis
            </label>
          </div>

          {config.enable_ai_signal_analysis && (
            <div className="grid grid-cols-2 gap-4 border-l-2 border-pink-500/30 pl-8">
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">AI Wait Timeout (sec)</label>
                <Input
                  type="number"
                  value={config.ai_brief_wait_timeout_seconds}
                  onChange={(e) => handleChange('ai_brief_wait_timeout_seconds', parseIntSafe(e.target.value, config.ai_brief_wait_timeout_seconds))}
                  min={10}
                  max={300}
                  className="w-full"
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">Bull/Bear TTL (sec)</label>
                <Input
                  type="number"
                  value={config.bull_bear_signal_ttl_seconds}
                  onChange={(e) => handleChange('bull_bear_signal_ttl_seconds', parseIntSafe(e.target.value, config.bull_bear_signal_ttl_seconds))}
                  min={300}
                  max={604800}
                  className="w-full"
                />
              </div>
            </div>
          )}

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_tradingview_chart"
              checked={config.enable_tradingview_chart}
              onChange={(e) => handleChange('enable_tradingview_chart', e.target.checked)}
              className="h-5 w-5 rounded border-gray-300 text-pink-600 focus:ring-pink-500"
            />
            <label htmlFor="enable_tradingview_chart" className="text-gray-700 dark:text-gray-300">
              Enable TradingView rendering
            </label>
          </div>

          {config.enable_tradingview_chart && (
            <div className="space-y-4 border-l-2 border-pink-500/30 pl-8">
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">chart-img API Key</label>
                <Input
                  type="password"
                  value={config.chart_img_api_key}
                  onChange={(e) => handleChange('chart_img_api_key', e.target.value)}
                  placeholder="API Key"
                  className="w-full"
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">Layout ID</label>
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
                  <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">Width (px)</label>
                  <Input
                    type="number"
                    value={config.chart_img_width}
                    onChange={(e) => handleChange('chart_img_width', parseIntSafe(e.target.value, config.chart_img_width))}
                    min={400}
                    max={2000}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">Height (px)</label>
                  <Input
                    type="number"
                    value={config.chart_img_height}
                    onChange={(e) => handleChange('chart_img_height', parseIntSafe(e.target.value, config.chart_img_height))}
                    min={300}
                    max={1500}
                    className="w-full"
                  />
                </div>
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">Timeout (sec)</label>
                <Input
                  type="number"
                  value={config.chart_img_timeout}
                  onChange={(e) => handleChange('chart_img_timeout', parseIntSafe(e.target.value, config.chart_img_timeout))}
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
                  className="h-5 w-5 rounded border-gray-300 text-pink-600 focus:ring-pink-500"
                />
                <label htmlFor="auto_delete_charts" className="text-gray-700 dark:text-gray-300">
                  Auto-delete generated charts
                </label>
              </div>
            </div>
          )}
        </div>
      </GlassCard>

      <GlassCard className="p-6">
        <div className="mb-6 flex items-center gap-3">
          <Network className="text-teal-500" size={24} />
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">Network Proxy</h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">SOCKS5 Proxy (optional)</label>
            <Input
              type="text"
              value={config.socks5_proxy}
              onChange={(e) => handleChange('socks5_proxy', e.target.value)}
              placeholder="socks5://127.0.0.1:1080"
              className="w-full"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">HTTP/HTTPS Proxy (optional)</label>
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

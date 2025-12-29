import React, { useState, useEffect } from 'react'
import { api } from '../lib/api'
import {
  MinimalSection,
  MinimalField,
  MinimalToggle,
  MinimalInput,
  MinimalSelect,
} from '../components/minimal/MinimalComponents'
import type { AllConfig } from '../types/config'
import '../styles/minimal.css'

export function MinimalSettingsPage() {
  const [config, setConfig] = useState<AllConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [activeTab, setActiveTab] = useState<'signal' | 'trader'>('signal')

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      const data = await api.getConfig()
      setConfig(data)
    } catch (error) {
      console.error('Failed to load config:', error)
    } finally {
      setLoading(false)
    }
  }

  const updateSignalConfig = (key: string, value: any) => {
    if (!config) return
    setConfig({
      ...config,
      signal: { ...config.signal, [key]: value },
    })
  }

  const updateTraderConfig = (key: string, value: any) => {
    if (!config) return
    setConfig({
      ...config,
      trader: { ...config.trader, [key]: value },
    })
  }

  const saveConfig = async () => {
    if (!config) return
    setSaving(true)
    try {
      await api.saveConfig(config)
      alert('配置已保存')
    } catch (error) {
      console.error('Failed to save config:', error)
      alert('保存失败')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="minimal-container">
        <div className="text-gray">加载中...</div>
      </div>
    )
  }

  if (!config) {
    return (
      <div className="minimal-container">
        <div className="text-gray">配置加载失败</div>
      </div>
    )
  }

  return (
    <div className="minimal-container">
      {/* Header */}
      <div className="mb-3">
        <h1 className="text-white" style={{ fontSize: '1.5rem', fontWeight: 600 }}>
          系统配置
        </h1>
        <p className="text-gray" style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
          管理信号监控和交易机器人的所有配置选项
        </p>
      </div>

      {/* Tabs */}
      <div className="minimal-tabs">
        <button
          className={`minimal-tab ${activeTab === 'signal' ? 'active' : ''}`}
          onClick={() => setActiveTab('signal')}
        >
          信号监控
        </button>
        <button
          className={`minimal-tab ${activeTab === 'trader' ? 'active' : ''}`}
          onClick={() => setActiveTab('trader')}
        >
          交易机器人
        </button>
      </div>

      {/* Signal Monitor Config */}
      {activeTab === 'signal' && (
        <div>
          {/* Basic Settings */}
          <MinimalSection title="基础设置">
            <MinimalField
              label="轮询间隔"
              description="轮询ValueScan API的时间间隔(秒)"
            >
              <MinimalInput
                type="number"
                value={config.signal?.poll_interval ?? 10}
                onChange={(v) => updateSignalConfig('poll_interval', parseInt(v))}
                min={5}
                max={60}
              />
            </MinimalField>

            <MinimalField
              label="请求超时"
              description="API请求的超时时间(秒)"
            >
              <MinimalInput
                type="number"
                value={config.signal?.request_timeout ?? 30}
                onChange={(v) => updateSignalConfig('request_timeout', parseInt(v))}
                min={10}
                max={120}
              />
            </MinimalField>

            <MinimalField
              label="启用Telegram通知"
              description="发送信号通知到Telegram"
            >
              <MinimalToggle
                checked={config.signal?.enable_telegram ?? false}
                onChange={() =>
                  updateSignalConfig('enable_telegram', !config.signal?.enable_telegram)
                }
              />
            </MinimalField>
          </MinimalSection>

          {/* Chart Settings */}
          <MinimalSection title="图表设置">
            <MinimalField
              label="启用TradingView图表"
              description="生成TradingView风格的图表"
            >
              <MinimalToggle
                checked={config.signal?.enable_tradingview_chart ?? false}
                onChange={() =>
                  updateSignalConfig(
                    'enable_tradingview_chart',
                    !config.signal?.enable_tradingview_chart
                  )
                }
              />
            </MinimalField>

            <MinimalField
              label="启用Pro图表"
              description="本地K线+热力图+资金流"
            >
              <MinimalToggle
                checked={config.signal?.enable_pro_chart ?? true}
                onChange={() =>
                  updateSignalConfig('enable_pro_chart', !config.signal?.enable_pro_chart)
                }
              />
            </MinimalField>

            <MinimalField
              label="图表生成超时"
              description="图表生成的超时时间(秒)"
            >
              <MinimalInput
                type="number"
                value={config.signal?.chart_img_timeout ?? 90}
                onChange={(v) => updateSignalConfig('chart_img_timeout', parseInt(v))}
                min={30}
                max={120}
              />
            </MinimalField>

            <MinimalField
              label="自动删除图表"
              description="发送后自动删除图表文件"
            >
              <MinimalToggle
                checked={config.signal?.auto_delete_charts ?? true}
                onChange={() =>
                  updateSignalConfig(
                    'auto_delete_charts',
                    !config.signal?.auto_delete_charts
                  )
                }
              />
            </MinimalField>
          </MinimalSection>

          {/* AI Features */}
          <MinimalSection title="AI功能">
            <MinimalField
              label="AI主力位"
              description="使用AI生成的关键位/支撑阻力线"
            >
              <MinimalToggle
                checked={config.signal?.enable_ai_key_levels ?? false}
                onChange={() =>
                  updateSignalConfig(
                    'enable_ai_key_levels',
                    !config.signal?.enable_ai_key_levels
                  )
                }
              />
            </MinimalField>

            <MinimalField
              label="AI图表叠加层"
              description="使用AI生成的图表叠加层"
            >
              <MinimalToggle
                checked={config.signal?.enable_ai_overlays ?? false}
                onChange={() =>
                  updateSignalConfig(
                    'enable_ai_overlays',
                    !config.signal?.enable_ai_overlays
                  )
                }
              />
            </MinimalField>

            <MinimalField
              label="AI信号分析"
              description="启用AI信号分析用于Telegram异步补全"
            >
              <MinimalToggle
                checked={config.signal?.enable_ai_signal_analysis ?? true}
                onChange={() =>
                  updateSignalConfig(
                    'enable_ai_signal_analysis',
                    !config.signal?.enable_ai_signal_analysis
                  )
                }
              />
            </MinimalField>
          </MinimalSection>

          {/* Logging */}
          <MinimalSection title="日志配置">
            <MinimalField
              label="日志级别"
              description="日志记录的详细程度"
            >
              <MinimalSelect
                value={config.signal?.log_level ?? 'INFO'}
                onChange={(v) => updateSignalConfig('log_level', v)}
                options={[
                  { value: 'DEBUG', label: 'DEBUG' },
                  { value: 'INFO', label: 'INFO' },
                  { value: 'WARNING', label: 'WARNING' },
                  { value: 'ERROR', label: 'ERROR' },
                ]}
              />
            </MinimalField>

            <MinimalField
              label="日志文件最大大小"
              description="单个日志文件的最大大小(MB)"
            >
              <MinimalInput
                type="number"
                value={(config.signal?.log_max_size ?? 10485760) / 1024 / 1024}
                onChange={(v) =>
                  updateSignalConfig('log_max_size', parseInt(v) * 1024 * 1024)
                }
                min={1}
                max={100}
              />
            </MinimalField>

            <MinimalField
              label="日志备份数量"
              description="保留的备份日志文件数量"
            >
              <MinimalInput
                type="number"
                value={config.signal?.log_backup_count ?? 5}
                onChange={(v) => updateSignalConfig('log_backup_count', parseInt(v))}
                min={1}
                max={20}
              />
            </MinimalField>
          </MinimalSection>
        </div>
      )}

      {/* Trader Config */}
      {activeTab === 'trader' && (
        <div>
          {/* Signal Aggregation */}
          <MinimalSection title="信号聚合">
            <MinimalField
              label="信号时间窗口"
              description="FOMO和Alpha信号聚合的时间窗口(秒)"
            >
              <MinimalInput
                type="number"
                value={config.trader?.signal_time_window ?? 300}
                onChange={(v) => updateTraderConfig('signal_time_window', parseInt(v))}
                min={60}
                max={600}
              />
            </MinimalField>

            <MinimalField
              label="最小信号分数"
              description="低于此分数的信号将被忽略(0-1)"
            >
              <MinimalInput
                type="number"
                value={config.trader?.min_signal_score ?? 0.6}
                onChange={(v) => updateTraderConfig('min_signal_score', parseFloat(v))}
                min={0}
                max={1}
                step={0.1}
              />
            </MinimalField>

            <MinimalField
              label="FOMO增强信号"
              description="启用FOMO intensify信号作为风险信号"
            >
              <MinimalToggle
                checked={config.trader?.enable_fomo_intensify ?? true}
                onChange={() =>
                  updateTraderConfig(
                    'enable_fomo_intensify',
                    !config.trader?.enable_fomo_intensify
                  )
                }
              />
            </MinimalField>

            <MinimalField
              label="信号状态缓存"
              description="持久化信号状态,防止重启后丢失"
            >
              <MinimalToggle
                checked={config.trader?.enable_signal_state_cache ?? true}
                onChange={() =>
                  updateTraderConfig(
                    'enable_signal_state_cache',
                    !config.trader?.enable_signal_state_cache
                  )
                }
              />
            </MinimalField>

            <MinimalField
              label="最大缓存信号数"
              description="用于去重的已处理信号ID缓存上限"
            >
              <MinimalInput
                type="number"
                value={config.trader?.max_processed_signal_ids ?? 5000}
                onChange={(v) =>
                  updateTraderConfig('max_processed_signal_ids', parseInt(v))
                }
                min={1000}
                max={10000}
              />
            </MinimalField>
          </MinimalSection>

          {/* Safety */}
          <MinimalSection title="安全限制">
            <MinimalField
              label="单笔最大交易额"
              description="防止单笔交易金额过大(USDT)"
            >
              <MinimalInput
                type="number"
                value={config.trader?.max_single_trade_value ?? 1000}
                onChange={(v) =>
                  updateTraderConfig('max_single_trade_value', parseFloat(v))
                }
                min={100}
                max={10000}
              />
            </MinimalField>

            <MinimalField
              label="强制平仓保证金率"
              description="保证金率低于此值时强制平仓所有仓位(%)"
            >
              <MinimalInput
                type="number"
                value={config.trader?.force_close_margin_ratio ?? 20}
                onChange={(v) =>
                  updateTraderConfig('force_close_margin_ratio', parseFloat(v))
                }
                min={10}
                max={50}
              />
            </MinimalField>

            <MinimalField
              label="紧急停止开关"
              description="启用紧急停止文件检测"
            >
              <MinimalToggle
                checked={config.trader?.enable_emergency_stop ?? true}
                onChange={() =>
                  updateTraderConfig(
                    'enable_emergency_stop',
                    !config.trader?.enable_emergency_stop
                  )
                }
              />
            </MinimalField>
          </MinimalSection>

          {/* Monitoring */}
          <MinimalSection title="监控配置">
            <MinimalField
              label="仓位监控间隔"
              description="检查仓位状态的时间间隔(秒)"
            >
              <MinimalInput
                type="number"
                value={config.trader?.position_monitor_interval ?? 10}
                onChange={(v) =>
                  updateTraderConfig('position_monitor_interval', parseInt(v))
                }
                min={5}
                max={60}
              />
            </MinimalField>

            <MinimalField
              label="余额更新间隔"
              description="更新账户余额的时间间隔(秒)"
            >
              <MinimalInput
                type="number"
                value={config.trader?.balance_update_interval ?? 60}
                onChange={(v) =>
                  updateTraderConfig('balance_update_interval', parseInt(v))
                }
                min={30}
                max={300}
              />
            </MinimalField>

            <MinimalField
              label="爆仓预警保证金率"
              description="保证金率低于此值时发送预警通知(%)"
            >
              <MinimalInput
                type="number"
                value={config.trader?.liquidation_warning_margin_ratio ?? 30}
                onChange={(v) =>
                  updateTraderConfig('liquidation_warning_margin_ratio', parseFloat(v))
                }
                min={20}
                max={50}
              />
            </MinimalField>
          </MinimalSection>

          {/* Notifications */}
          <MinimalSection title="通知设置">
            <MinimalField
              label="启用交易通知"
              description="总开关,关闭后所有交易通知都不会发送"
            >
              <MinimalToggle
                checked={config.trader?.enable_trade_notifications ?? true}
                onChange={() =>
                  updateTraderConfig(
                    'enable_trade_notifications',
                    !config.trader?.enable_trade_notifications
                  )
                }
              />
            </MinimalField>

            {config.trader?.enable_trade_notifications && (
              <>
                <MinimalField label="开仓通知" description="发送开仓通知">
                  <MinimalToggle
                    checked={config.trader?.notify_open_position ?? true}
                    onChange={() =>
                      updateTraderConfig(
                        'notify_open_position',
                        !config.trader?.notify_open_position
                      )
                    }
                  />
                </MinimalField>

                <MinimalField label="平仓通知" description="发送平仓通知">
                  <MinimalToggle
                    checked={config.trader?.notify_close_position ?? true}
                    onChange={() =>
                      updateTraderConfig(
                        'notify_close_position',
                        !config.trader?.notify_close_position
                      )
                    }
                  />
                </MinimalField>

                <MinimalField label="止损通知" description="发送止损通知">
                  <MinimalToggle
                    checked={config.trader?.notify_stop_loss ?? true}
                    onChange={() =>
                      updateTraderConfig(
                        'notify_stop_loss',
                        !config.trader?.notify_stop_loss
                      )
                    }
                  />
                </MinimalField>

                <MinimalField label="止盈通知" description="发送止盈通知">
                  <MinimalToggle
                    checked={config.trader?.notify_take_profit ?? true}
                    onChange={() =>
                      updateTraderConfig(
                        'notify_take_profit',
                        !config.trader?.notify_take_profit
                      )
                    }
                  />
                </MinimalField>

                <MinimalField label="部分平仓通知" description="发送部分平仓通知">
                  <MinimalToggle
                    checked={config.trader?.notify_partial_close ?? true}
                    onChange={() =>
                      updateTraderConfig(
                        'notify_partial_close',
                        !config.trader?.notify_partial_close
                      )
                    }
                  />
                </MinimalField>

                <MinimalField label="错误通知" description="发送错误通知">
                  <MinimalToggle
                    checked={config.trader?.notify_errors ?? true}
                    onChange={() =>
                      updateTraderConfig(
                        'notify_errors',
                        !config.trader?.notify_errors
                      )
                    }
                  />
                </MinimalField>
              </>
            )}
          </MinimalSection>

          {/* WebSocket */}
          <MinimalSection title="WebSocket配置">
            <MinimalField
              label="启用WebSocket"
              description="使用WebSocket获取实时价格更新"
            >
              <MinimalToggle
                checked={config.trader?.enable_websocket ?? true}
                onChange={() =>
                  updateTraderConfig('enable_websocket', !config.trader?.enable_websocket)
                }
              />
            </MinimalField>

            {config.trader?.enable_websocket && (
              <MinimalField
                label="重连间隔"
                description="WebSocket断开后的重连间隔(秒)"
              >
                <MinimalInput
                  type="number"
                  value={config.trader?.websocket_reconnect_interval ?? 5}
                  onChange={(v) =>
                    updateTraderConfig('websocket_reconnect_interval', parseInt(v))
                  }
                  min={1}
                  max={60}
                />
              </MinimalField>
            )}
          </MinimalSection>

          {/* API Settings */}
          <MinimalSection title="API设置">
            <MinimalField
              label="API重试次数"
              description="API请求失败后的重试次数"
            >
              <MinimalInput
                type="number"
                value={config.trader?.api_retry_count ?? 3}
                onChange={(v) => updateTraderConfig('api_retry_count', parseInt(v))}
                min={1}
                max={10}
              />
            </MinimalField>

            <MinimalField
              label="API超时时间"
              description="API请求的超时时间(秒)"
            >
              <MinimalInput
                type="number"
                value={config.trader?.api_timeout ?? 30}
                onChange={(v) => updateTraderConfig('api_timeout', parseInt(v))}
                min={10}
                max={120}
              />
            </MinimalField>

            <MinimalField
              label="滑点容忍度"
              description="订单价格滑点容忍度(%)"
            >
              <MinimalInput
                type="number"
                value={config.trader?.slippage_tolerance ?? 0.5}
                onChange={(v) => updateTraderConfig('slippage_tolerance', parseFloat(v))}
                min={0.1}
                max={5}
                step={0.1}
              />
            </MinimalField>
          </MinimalSection>
        </div>
      )}

      {/* Save Button */}
      <div className="mt-3" style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button
          className="minimal-button"
          onClick={saveConfig}
          disabled={saving}
        >
          {saving ? '保存中...' : '保存配置'}
        </button>
      </div>
    </div>
  )
}

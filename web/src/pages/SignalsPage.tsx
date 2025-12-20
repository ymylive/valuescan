import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import {
  RefreshCw,
  TrendingUp,
  AlertTriangle,
  Zap,
  Activity,
  Clock,
  ChevronRight,
} from 'lucide-react'

interface Signal {
  id: number
  type: 'ALPHA' | 'FOMO' | 'SIGNAL'
  symbol: string
  title: string
  timestamp: string
}

interface Alert {
  id: number
  type: 'RISK'
  symbol: string
  title: string
  timestamp: string
}

interface ServiceStatus {
  signal_monitor: 'running' | 'stopped' | 'error'
  trader: 'running' | 'stopped' | 'error'
  copytrade: 'running' | 'stopped' | 'error'
}

export function SignalsPage() {
  const [signals, setSignals] = useState<Signal[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [status, setStatus] = useState<ServiceStatus | null>(null)
  const [loginStatus, setLoginStatus] = useState<{
    logged_in: boolean
    cookies_count: number
  } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [signalsRes, alertsRes, statusRes, loginRes] = await Promise.all([
        api.getValueScanSignals(20),
        api.getValueScanAlerts(10),
        api.getValueScanStatus().catch(() => null),
        api
          .getValueScanLoginStatus()
          .catch(() => ({ logged_in: false, cookies_count: 0 })),
      ])
      setSignals(signalsRes.signals || [])
      setAlerts(alertsRes.alerts || [])
      setStatus(statusRes)
      setLoginStatus(loginRes)
    } catch (e: any) {
      setError(e.message || 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const getServiceBadge = (
    serviceStatus: 'running' | 'stopped' | 'error' | undefined
  ) => {
    if (serviceStatus === 'running') {
      return { className: 'bg-green-500/20 text-green-400', text: '运行中' }
    }
    if (serviceStatus === 'error') {
      return { className: 'bg-red-500/20 text-red-400', text: '错误' }
    }
    return { className: 'bg-gray-500/20 text-gray-400', text: '已停止' }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000) // Refresh every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const formatTime = (timestamp: string) => {
    if (!timestamp) return '--'
    try {
      const date = new Date(timestamp)
      return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return timestamp
    }
  }

  const getSignalIcon = (type: string) => {
    switch (type) {
      case 'ALPHA':
        return <Zap className="w-4 h-4 text-yellow-400" />
      case 'FOMO':
        return <TrendingUp className="w-4 h-4 text-green-400" />
      default:
        return <Activity className="w-4 h-4 text-blue-400" />
    }
  }

  const getSignalColor = (type: string) => {
    switch (type) {
      case 'ALPHA':
        return 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400'
      case 'FOMO':
        return 'bg-green-500/10 border-green-500/30 text-green-400'
      default:
        return 'bg-blue-500/10 border-blue-500/30 text-blue-400'
    }
  }

  return (
    <div className="min-h-screen bg-[#0b0e11] pt-20 pb-8 px-3 sm:px-4">
      <div className="max-w-7xl mx-auto space-y-4 sm:space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-white flex items-center gap-2 sm:gap-3">
              <Activity className="w-6 h-6 sm:w-7 sm:h-7 text-[#F0B90B]" />
              ValueScan 信号监控
            </h1>
            <p className="text-xs sm:text-sm text-gray-400 mt-1">
              实时监控 valuescan.io 交易信号和风险预警
            </p>
          </div>
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center justify-center gap-2 px-4 py-2 bg-[#F0B90B]/10 text-[#F0B90B] rounded-lg hover:bg-[#F0B90B]/20 transition-colors disabled:opacity-50 w-full sm:w-auto"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </button>
        </div>

        {/* Service Status */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 sm:gap-4">
          <div className="bg-[#1e2329] border border-[#2b3139] rounded-xl p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">ValueScan 登录</span>
              <span
                className={`px-2 py-0.5 rounded text-xs font-medium ${
                  loginStatus?.logged_in
                    ? 'bg-green-500/20 text-green-400'
                    : 'bg-red-500/20 text-red-400'
                }`}
              >
                {loginStatus?.logged_in ? '已登录' : '未登录'}
              </span>
            </div>
            {loginStatus?.logged_in && (
              <div className="text-xs text-gray-500 mt-2">
                Cookies: {loginStatus.cookies_count}
              </div>
            )}
          </div>

          <div className="bg-[#1e2329] border border-[#2b3139] rounded-xl p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">信号监控</span>
              {(() => {
                const badge = getServiceBadge(status?.signal_monitor)
                return (
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${badge.className}`}
                  >
                    {badge.text}
                  </span>
                )
              })()}
            </div>
          </div>

          <div className="bg-[#1e2329] border border-[#2b3139] rounded-xl p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">自动交易</span>
              {(() => {
                const badge = getServiceBadge(status?.trader)
                return (
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${badge.className}`}
                  >
                    {badge.text}
                  </span>
                )
              })()}
            </div>
          </div>

          <div className="bg-[#1e2329] border border-[#2b3139] rounded-xl p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">跟单服务</span>
              {(() => {
                const badge = getServiceBadge(status?.copytrade)
                return (
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${badge.className}`}
                  >
                    {badge.text}
                  </span>
                )
              })()}
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Signals List */}
          <div className="lg:col-span-2 bg-[#1e2329] border border-[#2b3139] rounded-xl">
            <div className="px-4 sm:px-6 py-3 sm:py-4 border-b border-[#2b3139] flex items-center justify-between">
              <h2 className="text-base sm:text-lg font-semibold text-white flex items-center gap-2">
                <Zap className="w-4 h-4 sm:w-5 sm:h-5 text-[#F0B90B]" />
                交易信号
              </h2>
              <span className="text-xs sm:text-sm text-gray-400">
                {signals.length} 条信号
              </span>
            </div>
            <div className="divide-y divide-[#2b3139] max-h-[400px] sm:max-h-[600px] overflow-y-auto">
              {signals.length === 0 ? (
                <div className="px-6 py-12 text-center text-gray-500">
                  暂无信号数据
                </div>
              ) : (
                signals.map((signal) => (
                  <div
                    key={signal.id}
                    className="px-3 sm:px-6 py-3 sm:py-4 hover:bg-[#2b3139]/50 transition-colors cursor-pointer group"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 sm:gap-4">
                      <div className="flex items-start gap-2 sm:gap-3 flex-1 min-w-0">
                        <div
                          className={`p-1.5 sm:p-2 rounded-lg ${getSignalColor(signal.type)} shrink-0`}
                        >
                          {getSignalIcon(signal.type)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-semibold text-white text-sm sm:text-base">
                              {signal.symbol || 'UNKNOWN'}
                            </span>
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${getSignalColor(signal.type)}`}
                            >
                              {signal.type}
                            </span>
                          </div>
                          <p className="text-xs sm:text-sm text-gray-400 mt-1 line-clamp-2">
                            {signal.title || 'No description'}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 text-gray-500 text-xs sm:text-sm shrink-0 ml-7 sm:ml-0">
                        <Clock className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                        {formatTime(signal.timestamp)}
                        <ChevronRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity hidden sm:block" />
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Alerts List */}
          <div className="bg-[#1e2329] border border-[#2b3139] rounded-xl">
            <div className="px-4 sm:px-6 py-3 sm:py-4 border-b border-[#2b3139] flex items-center justify-between">
              <h2 className="text-base sm:text-lg font-semibold text-white flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 sm:w-5 sm:h-5 text-red-400" />
                风险预警
              </h2>
              <span className="text-xs sm:text-sm text-gray-400">
                {alerts.length} 条预警
              </span>
            </div>
            <div className="divide-y divide-[#2b3139] max-h-[300px] sm:max-h-[600px] overflow-y-auto">
              {alerts.length === 0 ? (
                <div className="px-6 py-12 text-center text-gray-500">
                  暂无风险预警
                </div>
              ) : (
                alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className="px-3 sm:px-6 py-3 sm:py-4 hover:bg-[#2b3139]/50 transition-colors cursor-pointer"
                  >
                    <div className="flex items-start gap-2 sm:gap-3">
                      <div className="p-1.5 sm:p-2 rounded-lg bg-red-500/10 border border-red-500/30 shrink-0">
                        <AlertTriangle className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-red-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-white text-sm sm:text-base">
                            {alert.symbol || 'UNKNOWN'}
                          </span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-500/20 text-red-400">
                            RISK
                          </span>
                        </div>
                        <p className="text-xs sm:text-sm text-gray-400 mt-1 line-clamp-2">
                          {alert.title || 'No description'}
                        </p>
                        <div className="flex items-center gap-1 text-gray-500 text-xs mt-2">
                          <Clock className="w-3 h-3" />
                          {formatTime(alert.timestamp)}
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-[#1e2329] border border-[#2b3139] rounded-xl p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-semibold text-white mb-3 sm:mb-4">
            快捷操作
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 sm:gap-4">
            <a
              href="/dashboard"
              className="flex items-center gap-2 sm:gap-3 p-3 sm:p-4 bg-[#2b3139] rounded-xl hover:bg-[#363d45] transition-colors"
            >
              <TrendingUp className="w-4 h-4 sm:w-5 sm:h-5 text-[#F0B90B] shrink-0" />
              <span className="text-white text-xs sm:text-sm truncate">
                交易仪表板
              </span>
            </a>
            <a
              href="/traders"
              className="flex items-center gap-2 sm:gap-3 p-3 sm:p-4 bg-[#2b3139] rounded-xl hover:bg-[#363d45] transition-colors"
            >
              <Activity className="w-4 h-4 sm:w-5 sm:h-5 text-[#F0B90B] shrink-0" />
              <span className="text-white text-xs sm:text-sm truncate">
                AI 交易员
              </span>
            </a>
            <a
              href="/strategy"
              className="flex items-center gap-2 sm:gap-3 p-3 sm:p-4 bg-[#2b3139] rounded-xl hover:bg-[#363d45] transition-colors"
            >
              <Zap className="w-4 h-4 sm:w-5 sm:h-5 text-[#F0B90B] shrink-0" />
              <span className="text-white text-xs sm:text-sm truncate">
                策略工作室
              </span>
            </a>
            <a
              href="/backtest"
              className="flex items-center gap-2 sm:gap-3 p-3 sm:p-4 bg-[#2b3139] rounded-xl hover:bg-[#363d45] transition-colors"
            >
              <Clock className="w-4 h-4 sm:w-5 sm:h-5 text-[#F0B90B] shrink-0" />
              <span className="text-white text-xs sm:text-sm truncate">
                回测系统
              </span>
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SignalsPage

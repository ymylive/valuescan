import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import {
  Settings,
  Server,
  Play,
  Square,
  RotateCw,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  User,
  Activity,
  FileText,
  RefreshCw,
  Database,
  Download,
  Upload,
} from 'lucide-react'
import { api } from '../lib/api'
import { ValueScanDataEditor } from '../components/valuescan/ValueScanDataEditor'
import { SignalMonitorConfigSection } from '../components/valuescan/SignalMonitorConfigSection'
import { TraderConfigSection } from '../components/valuescan/TraderConfigSection'
import { CopyTradeConfigSection } from '../components/valuescan/CopyTradeConfigSection'
import { KeepaliveConfigSection } from '../components/valuescan/KeepaliveConfigSection'
import { ValueScanLoginSection } from '../components/valuescan/ValueScanLoginSection'
import type { KeepaliveConfig, AllConfig } from '../types/config'

type ServiceStatus = 'running' | 'stopped' | 'error'
type ServiceName = 'signal' | 'trader' | 'copytrade'

interface ServiceStatusData {
  signal_monitor: ServiceStatus
  trader: ServiceStatus
  copytrade: ServiceStatus
}

interface LoginStatus {
  logged_in: boolean
  cookies_count: number
}

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<
    'services' | 'login' | 'logs' | 'config'
  >('services')
  const [serviceStatus, setServiceStatus] = useState<ServiceStatusData>({
    signal_monitor: 'stopped',
    trader: 'stopped',
    copytrade: 'stopped',
  })
  const [loginStatus, setLoginStatus] = useState<LoginStatus>({
    logged_in: false,
    cookies_count: 0,
  })
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  // Login form (保留用于传统登录)
  const [_email, _setEmail] = useState('')
  const [_password, _setPassword] = useState('')
  const [_loginLoading, _setLoginLoading] = useState(false)

  // Logs
  const [selectedLogService, setSelectedLogService] = useState<
    'signal' | 'trader' | 'proxy' | 'xray'
  >('signal')
  const [logs, setLogs] = useState('')
  const [logsLoading, setLogsLoading] = useState(false)

  // Config
  const [config, setConfig] = useState<AllConfig | null>(null)
  const [keepaliveConfig, setKeepaliveConfig] =
    useState<KeepaliveConfig | null>(null)
  const [_aiSummaryConfig, setAiSummaryConfig] = useState<any>(null)
  const [configLoading, setConfigLoading] = useState(false)
  const [saveLoading, setSaveLoading] = useState(false)
  const [activeConfigSection, setActiveConfigSection] = useState<
    'signal' | 'trader' | 'copytrade' | 'keepalive' | 'valuescan_data'
  >('signal')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [unsavedChanges, setUnsavedChanges] = useState(false)
  const [showExportModal, setShowExportModal] = useState(false)
  const [exportIncludeSensitive, setExportIncludeSensitive] = useState(false)

  const loadStatus = useCallback(async () => {
    try {
      const [status, login] = await Promise.all([
        api.getServiceStatus(),
        api.getValuescanLoginStatus(),
      ])
      setServiceStatus(status)
      setLoginStatus(login)
    } catch (e) {
      console.error('Failed to load status:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadStatus()
    const interval = setInterval(loadStatus, 10000)
    return () => clearInterval(interval)
  }, [loadStatus])

  const handleServiceAction = async (
    service: ServiceName,
    action: 'start' | 'stop' | 'restart'
  ) => {
    const actionKey = `${service}-${action}`
    setActionLoading(actionKey)
    try {
      const result = await api.controlService(service, action)
      if (result.success) {
        const serviceNames = {
          signal: '信号监控',
          trader: '交易机器人',
          copytrade: '跟单系统',
        }
        const actionNames = {
          start: '已启动',
          stop: '已停止',
          restart: '已重启',
        }
        toast.success(`${serviceNames[service]} ${actionNames[action]}`)
        loadStatus()
      } else {
        toast.error('操作失败')
      }
    } catch (e) {
      toast.error('操作失败: ' + e)
    } finally {
      setActionLoading(null)
    }
  }

  // 传统登录方法已移至 ValueScanLoginSection 组件

  void _email
  void _password
  void _loginLoading
  void _setEmail
  void _setPassword
  void _setLoginLoading

  const loadLogs = async () => {
    setLogsLoading(true)
    try {
      const result = await api.getServiceLogs(selectedLogService, 200)
      setLogs(result.logs || '暂无日志')
    } catch (e) {
      setLogs('获取日志失败')
    } finally {
      setLogsLoading(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'logs') {
      loadLogs()
    } else if (activeTab === 'config') {
      loadConfig()
    }
  }, [activeTab, selectedLogService])

  const loadConfig = async () => {
    setConfigLoading(true)
    try {
      const [configData, keepaliveData, aiSummaryData] = await Promise.all([
        api.getConfig(),
        api.getKeepaliveConfig().catch(() => null),
        api.getAISummaryConfig().catch(() => null),
      ])
      
      // Merge AI summary config into configData before setting state
      let mergedConfig = { ...configData }
      console.log('[AI-LOAD-v2] aiSummaryData:', aiSummaryData)
      if (aiSummaryData) {
        setAiSummaryConfig(aiSummaryData)
        mergedConfig = {
          ...mergedConfig,
          signal: {
            ...(mergedConfig.signal || {}),
            ai_summary_enabled: aiSummaryData.enabled,
            ai_summary_api_key: aiSummaryData.api_key,
            ai_summary_api_url: aiSummaryData.api_url,
            ai_summary_model: aiSummaryData.model,
            ai_summary_interval_hours: aiSummaryData.interval_hours,
            ai_summary_lookback_hours: aiSummaryData.lookback_hours,
          },
        }
        console.log('[AI-LOAD-v2] mergedConfig.signal.ai_summary_enabled:', mergedConfig.signal.ai_summary_enabled)
      }
      
      setConfig(mergedConfig)
      if (keepaliveData?.config) {
        setKeepaliveConfig(keepaliveData.config)
      }
      setFieldErrors({})
      setUnsavedChanges(false)
    } catch (e) {
      toast.error('获取配置失败')
    } finally {
      setConfigLoading(false)
    }
  }

  const handleSaveConfig = async () => {
    setSaveLoading(true)
    try {
      // Save main config
      if (
        activeConfigSection !== 'keepalive' &&
        activeConfigSection !== 'valuescan_data'
      ) {
        const result = await api.saveConfig(config)
        if (result.success) {
          toast.success('配置保存成功')
          if (result.restarted) {
            toast.info('服务正在重启以应用新配置')
          }
          setUnsavedChanges(false)
        } else {
          toast.error(result.errors?.join(', ') || '保存失败')
        }

        // Also save AI summary config if in signal section
        if (activeConfigSection === 'signal') {
          const signalConfig = config?.signal || {}
          const aiConfig = {
            enabled: !!signalConfig.ai_summary_enabled,
            api_key: signalConfig.ai_summary_api_key || '',
            api_url: signalConfig.ai_summary_api_url || 'https://api.openai.com/v1/chat/completions',
            model: signalConfig.ai_summary_model || 'gpt-4o-mini',
            interval_hours: signalConfig.ai_summary_interval_hours || 1,
            lookback_hours: signalConfig.ai_summary_lookback_hours || 1,
          }
          console.log('[AI-SAVE-v2] Saving AI config:', JSON.stringify(aiConfig))
          try {
            const aiResult = await api.saveAISummaryConfig(aiConfig)
            console.log('AI config save result:', aiResult)
            setAiSummaryConfig(aiConfig)
          } catch (aiErr) {
            console.error('保存 AI 总结配置失败:', aiErr)
            toast.error('保存 AI 总结配置失败')
          }
        }
      }
      // Save keepalive config
      if (activeConfigSection === 'keepalive' && keepaliveConfig) {
        const result = await api.saveKeepaliveConfig(keepaliveConfig)
        if (result.success) {
          toast.success('Keepalive 配置保存成功')
          if (result.needs_restart?.length) {
            toast.info(`需要重启服务: ${result.needs_restart.join(', ')}`)
          }
          setUnsavedChanges(false)
        } else {
          toast.error(result.errors?.join(', ') || result.error || '保存失败')
        }
      }
    } catch (e) {
      toast.error('保存配置失败: ' + e)
    } finally {
      setSaveLoading(false)
    }
  }

  const updateConfigSection = (
    section: 'signal' | 'trader' | 'copytrade',
    data: any
  ) => {
    setConfig((prev: any) => ({
      ...prev,
      [section]: data,
    }))
    setUnsavedChanges(true)
  }

  const updateKeepaliveConfig = (data: KeepaliveConfig) => {
    setKeepaliveConfig(data)
    setUnsavedChanges(true)
  }

  // Export config to JSON file
  const handleExportConfig = () => {
    if (!config) return

    let exportData = { ...config }

    // Remove sensitive fields if not included
    if (!exportIncludeSensitive) {
      const removeSensitive = (obj: any): any => {
        if (!obj || typeof obj !== 'object') return obj
        const result: any = Array.isArray(obj) ? [] : {}
        for (const [key, value] of Object.entries(obj)) {
          if (
            /(secret|password|token|api[_-]?key|api[_-]?hash|private)/i.test(
              key
            )
          ) {
            continue // Skip sensitive fields
          }
          result[key] =
            typeof value === 'object' ? removeSensitive(value) : value
        }
        return result
      }
      exportData = removeSensitive(exportData)
    }

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `valuescan-config-${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    setShowExportModal(false)
    toast.success('配置已导出')
  }

  // Import config from JSON file
  const handleImportConfig = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const importedConfig = JSON.parse(e.target?.result as string)

        // Merge with existing config
        if (importedConfig.signal) {
          setConfig((prev: any) => ({
            ...prev,
            signal: { ...prev?.signal, ...importedConfig.signal },
          }))
        }
        if (importedConfig.trader) {
          setConfig((prev: any) => ({
            ...prev,
            trader: { ...prev?.trader, ...importedConfig.trader },
          }))
        }
        if (importedConfig.copytrade) {
          setConfig((prev: any) => ({
            ...prev,
            copytrade: { ...prev?.copytrade, ...importedConfig.copytrade },
          }))
        }

        setUnsavedChanges(true)
        toast.success('配置已导入，请检查后保存')
      } catch (err) {
        toast.error('导入失败：无效的 JSON 文件')
      }
    }
    reader.readAsText(file)

    // Reset input
    event.target.value = ''
  }

  const getStatusIcon = (status: ServiceStatus) => {
    switch (status) {
      case 'running':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'stopped':
        return <XCircle className="w-5 h-5 text-gray-500" />
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />
    }
  }

  const getStatusText = (status: ServiceStatus) => {
    switch (status) {
      case 'running':
        return '运行中'
      case 'stopped':
        return '已停止'
      case 'error':
        return '错误'
    }
  }

  const getStatusColor = (status: ServiceStatus) => {
    switch (status) {
      case 'running':
        return 'text-green-500'
      case 'stopped':
        return 'text-gray-500'
      case 'error':
        return 'text-red-500'
    }
  }

  const renderServiceCard = (
    name: string,
    service: ServiceName,
    status: ServiceStatus,
    description: string
  ) => (
    <div className="bg-[#1E2329] border border-[#2B3139] rounded-xl p-4 sm:p-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-0 mb-4">
        <div className="flex items-center gap-2 sm:gap-3">
          <Server className="w-5 h-5 sm:w-6 sm:h-6 text-[#F0B90B]" />
          <div>
            <h3 className="text-base sm:text-lg font-semibold text-white">
              {name}
            </h3>
            <p className="text-xs sm:text-sm text-gray-400">{description}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 ml-7 sm:ml-0">
          {getStatusIcon(status)}
          <span className={`text-sm font-medium ${getStatusColor(status)}`}>
            {getStatusText(status)}
          </span>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => handleServiceAction(service, 'start')}
          disabled={actionLoading !== null || status === 'running'}
          className="flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-white text-xs sm:text-sm transition-colors flex-1 sm:flex-none justify-center"
        >
          {actionLoading === `${service}-start` ? (
            <Loader2 className="w-3.5 h-3.5 sm:w-4 sm:h-4 animate-spin" />
          ) : (
            <Play className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
          )}
          启动
        </button>
        <button
          onClick={() => handleServiceAction(service, 'stop')}
          disabled={actionLoading !== null || status === 'stopped'}
          className="flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-white text-xs sm:text-sm transition-colors flex-1 sm:flex-none justify-center"
        >
          {actionLoading === `${service}-stop` ? (
            <Loader2 className="w-3.5 h-3.5 sm:w-4 sm:h-4 animate-spin" />
          ) : (
            <Square className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
          )}
          停止
        </button>
        <button
          onClick={() => handleServiceAction(service, 'restart')}
          disabled={actionLoading !== null}
          className="flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 bg-[#F0B90B] hover:bg-[#d4a50a] disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-black text-xs sm:text-sm transition-colors flex-1 sm:flex-none justify-center"
        >
          {actionLoading === `${service}-restart` ? (
            <Loader2 className="w-3.5 h-3.5 sm:w-4 sm:h-4 animate-spin" />
          ) : (
            <RotateCw className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
          )}
          重启
        </button>
      </div>
    </div>
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-[#F0B90B]" />
      </div>
    )
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2 sm:gap-3">
        <Settings className="w-6 h-6 sm:w-8 sm:h-8 text-[#F0B90B]" />
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-white">系统设置</h1>
          <p className="text-xs sm:text-sm text-gray-400">
            服务管理、登录状态和日志查看
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 sm:gap-2 border-b border-[#2B3139] pb-2 overflow-x-auto">
        {[
          { id: 'services' as const, label: '服务管理', icon: Server },
          { id: 'config' as const, label: 'ValueScan 配置', icon: Settings },
          { id: 'login' as const, label: 'ValueScan 登录', icon: User },
          { id: 'logs' as const, label: '服务日志', icon: FileText },
        ].map((tab) => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 rounded-lg text-xs sm:text-sm font-medium transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-[#F0B90B] text-black'
                  : 'text-gray-400 hover:text-white hover:bg-[#2B3139]'
              }`}
            >
              <Icon className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Services Tab */}
      {activeTab === 'services' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">服务状态</h2>
            <button
              onClick={loadStatus}
              className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-400 hover:text-white transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              刷新
            </button>
          </div>

          <div className="grid gap-3 sm:gap-4 grid-cols-1 lg:grid-cols-3">
            {renderServiceCard(
              '信号监控',
              'signal',
              serviceStatus.signal_monitor,
              'ValueScan 信号监控服务'
            )}
            {renderServiceCard(
              '交易机器人',
              'trader',
              serviceStatus.trader,
              'AI 自动交易服务'
            )}
            {renderServiceCard(
              '跟单系统',
              'copytrade',
              serviceStatus.copytrade,
              'Telegram 跟单服务'
            )}
          </div>
        </div>
      )}

      {/* Login Tab */}
      {activeTab === 'login' && (
        <div className="space-y-6">
          {/* 新的自动登录组件 */}
          <ValueScanLoginSection />

          {/* 旧的登录状态显示（保留作为备用） */}
          <div className="bg-[#1E2329] border border-[#2B3139] rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">
              传统登录状态
            </h3>
            <div className="flex items-center gap-4">
              <div
                className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
                  loginStatus.logged_in
                    ? 'bg-green-500/20 text-green-500'
                    : 'bg-red-500/20 text-red-500'
                }`}
              >
                {loginStatus.logged_in ? (
                  <CheckCircle className="w-5 h-5" />
                ) : (
                  <XCircle className="w-5 h-5" />
                )}
                {loginStatus.logged_in ? '已登录' : '未登录'}
              </div>
              {loginStatus.logged_in && (
                <span className="text-sm text-gray-400">
                  Cookies: {loginStatus.cookies_count}
                </span>
              )}
            </div>
            <p className="text-xs text-gray-500 mt-3">
              如果自动登录不工作，可以尝试使用传统的 HTTP API 登录方式。
            </p>
          </div>
        </div>
      )}

      {/* Config Tab */}
      {activeTab === 'config' && (
        <div className="space-y-6">
          {configLoading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="w-8 h-8 animate-spin text-[#F0B90B]" />
            </div>
          ) : config ? (
            <>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-white">
                    ValueScan 配置选项
                  </h2>
                  {activeConfigSection !== 'valuescan_data' &&
                    Object.keys(fieldErrors).length > 0 && (
                      <div className="text-sm text-red-400 mt-1">
                        存在未修复的配置输入错误，修复后才能保存
                      </div>
                    )}
                </div>
                {activeConfigSection !== 'valuescan_data' && (
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => setShowExportModal(true)}
                      className="flex items-center gap-2 px-3 py-2 bg-[#2B3139] hover:bg-[#3B4149] rounded-lg text-white text-sm transition-colors"
                    >
                      <Download className="w-4 h-4" />
                      导出
                    </button>
                    <label className="flex items-center gap-2 px-3 py-2 bg-[#2B3139] hover:bg-[#3B4149] rounded-lg text-white text-sm transition-colors cursor-pointer">
                      <Upload className="w-4 h-4" />
                      导入
                      <input
                        type="file"
                        accept=".json"
                        onChange={handleImportConfig}
                        className="hidden"
                      />
                    </label>
                    <button
                      onClick={handleSaveConfig}
                      disabled={
                        saveLoading || Object.keys(fieldErrors).length > 0
                      }
                      className="flex items-center justify-center gap-2 px-4 py-2 bg-[#F0B90B] hover:bg-[#d4a50a] disabled:bg-gray-600 rounded-lg text-black font-medium transition-colors"
                    >
                      {saveLoading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <CheckCircle className="w-4 h-4" />
                      )}
                      {saveLoading ? '保存中...' : '保存配置'}
                    </button>
                  </div>
                )}
              </div>

              {unsavedChanges && (
                <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 mb-4 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-yellow-500" />
                  <span className="text-sm text-yellow-500">
                    有未保存的更改
                  </span>
                </div>
              )}

              <div className="flex gap-1 sm:gap-2 border-b border-[#2B3139] pb-2 overflow-x-auto">
                {[
                  { id: 'signal' as const, label: '信号监控', icon: Activity },
                  { id: 'trader' as const, label: '交易', icon: Server },
                  { id: 'copytrade' as const, label: '跟单', icon: RefreshCw },
                  {
                    id: 'keepalive' as const,
                    label: '服务监控',
                    icon: Activity,
                  },
                  {
                    id: 'valuescan_data' as const,
                    label: '数据源',
                    icon: Database,
                  },
                ].map((tab) => {
                  const Icon = tab.icon
                  const isActive = activeConfigSection === tab.id
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveConfigSection(tab.id)}
                      className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap flex-shrink-0 ${
                        isActive
                          ? 'bg-[#F0B90B] text-black'
                          : 'text-gray-400 hover:text-white hover:bg-[#1E2329]'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      {tab.label}
                    </button>
                  )
                })}
              </div>

              {activeConfigSection === 'signal' && (
                <SignalMonitorConfigSection
                  config={config.signal || {}}
                  onChange={(data) => updateConfigSection('signal', data)}
                  errors={fieldErrors}
                />
              )}

              {activeConfigSection === 'trader' && (
                <TraderConfigSection
                  config={config.trader || {}}
                  onChange={(data) => updateConfigSection('trader', data)}
                  errors={fieldErrors}
                />
              )}

              {activeConfigSection === 'copytrade' && (
                <CopyTradeConfigSection
                  config={config.copytrade || {}}
                  onChange={(data) => updateConfigSection('copytrade', data)}
                  errors={fieldErrors}
                />
              )}

              {activeConfigSection === 'keepalive' && (
                <KeepaliveConfigSection
                  config={keepaliveConfig}
                  onChange={updateKeepaliveConfig}
                  errors={fieldErrors}
                />
              )}

              {activeConfigSection === 'valuescan_data' && (
                <ValueScanDataEditor />
              )}
            </>
          ) : (
            <div className="text-center text-gray-400 py-12">配置加载失败</div>
          )}
        </div>
      )}

      {/* Logs Tab */}
      {activeTab === 'logs' && (
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <select
              value={selectedLogService}
              onChange={(e) => setSelectedLogService(e.target.value as any)}
              className="px-4 py-2 bg-[#1E2329] border border-[#2B3139] rounded-lg text-white focus:outline-none focus:border-[#F0B90B]"
            >
              <option value="signal">信号监控</option>
              <option value="trader">交易机器人</option>
              <option value="proxy">代理检测</option>
              <option value="xray">Xray</option>
            </select>
            <button
              onClick={loadLogs}
              disabled={logsLoading}
              className="flex items-center gap-2 px-4 py-2 bg-[#2B3139] hover:bg-[#3B4149] rounded-lg text-white text-sm transition-colors"
            >
              {logsLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              刷新日志
            </button>
          </div>

          <div className="bg-[#0B0E11] border border-[#2B3139] rounded-xl p-4 h-[500px] overflow-auto">
            <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap">
              {logsLoading ? '加载中...' : logs}
            </pre>
          </div>
        </div>
      )}

      {/* Export Modal */}
      {showExportModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-[#1E2329] border border-[#2B3139] rounded-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-white mb-4">导出配置</h3>
            <div className="space-y-4">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="radio"
                  checked={!exportIncludeSensitive}
                  onChange={() => setExportIncludeSensitive(false)}
                  className="w-4 h-4 text-[#F0B90B]"
                />
                <div>
                  <div className="text-sm text-white">排除敏感字段（推荐）</div>
                  <div className="text-xs text-gray-400">
                    不包含 API Key、密码等敏感信息
                  </div>
                </div>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="radio"
                  checked={exportIncludeSensitive}
                  onChange={() => setExportIncludeSensitive(true)}
                  className="w-4 h-4 text-[#F0B90B]"
                />
                <div>
                  <div className="text-sm text-white">包含敏感字段</div>
                  <div className="text-xs text-yellow-500">
                    ⚠️ 请妥善保管导出的文件
                  </div>
                </div>
              </label>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowExportModal(false)}
                className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleExportConfig}
                className="px-4 py-2 bg-[#F0B90B] hover:bg-[#d4a50a] rounded-lg text-black font-medium transition-colors"
              >
                导出
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

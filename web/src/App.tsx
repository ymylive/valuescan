import { useState, useEffect, useCallback } from 'react'
import { Toaster, toast } from 'sonner'
import {
  Activity,
  Settings,
  FileText,
  Play,
  Square,
  RotateCw,
  CheckCircle,
  AlertCircle,
  Loader2,
  RefreshCw,
  Download,
  Upload,
  ChevronRight,
  Zap,
  Shield,
  Bot,
  Eye,
  User,
  Key,
  LogIn,
  Menu,
  X,
  Terminal,
  Cpu,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from './lib/api'
import { SignalMonitorConfigSection } from './components/valuescan/SignalMonitorConfigSection'
import { TraderConfigSection } from './components/valuescan/TraderConfigSection'
import { CopyTradeConfigSection } from './components/valuescan/CopyTradeConfigSection'
import { KeepaliveConfigSection } from './components/valuescan/KeepaliveConfigSection'
import { ParticleCanvas } from './components/ui/CanvasParticleBackground'
import { useDayNightMode } from './hooks/useDayNightMode'
import { GlassCard } from './components/ui/GlassCard'
import {
  FadeIn,
  SlideUp,
  ScaleIn,
  staggerContainer,
} from './components/ui/Motion'
import type { KeepaliveConfig, AllConfig } from './types/config'
import { cn } from './lib/utils'

type ServiceStatus = 'running' | 'stopped' | 'error'
type ServiceName = 'signal' | 'trader' | 'copytrade' | 'keepalive'
type TabId = 'dashboard' | 'config' | 'logs'
type ConfigSection = 'signal' | 'trader' | 'copytrade' | 'keepalive'

interface ServiceStatusData {
  signal_monitor: ServiceStatus
  trader: ServiceStatus
  copytrade: ServiceStatus
  keepalive: ServiceStatus
}

const SERVICE_INFO: Record<
  ServiceName,
  { name: string; icon: typeof Activity; description: string; color: string }
> = {
  signal: {
    name: '信号监控',
    icon: Zap,
    description: 'ValueScan 信号捕获',
    color: 'text-yellow-400',
  },
  trader: {
    name: '自动交易',
    icon: Bot,
    description: 'Binance 合约交易',
    color: 'text-blue-400',
  },
  copytrade: {
    name: '跟单系统',
    icon: Eye,
    description: 'Telegram 信号跟单',
    color: 'text-green-400',
  },
  keepalive: {
    name: '服务监控',
    icon: Shield,
    description: '自动重启守护',
    color: 'text-purple-400',
  },
}

export default function App() {
  const mode = useDayNightMode()
  const [activeTab, setActiveTab] = useState<TabId>('dashboard')
  const [activeConfigSection, setActiveConfigSection] =
    useState<ConfigSection>('signal')
  const [serviceStatus, setServiceStatus] = useState<ServiceStatusData>({
    signal_monitor: 'stopped',
    trader: 'stopped',
    copytrade: 'stopped',
    keepalive: 'stopped',
  })
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  // Config state
  const [config, setConfig] = useState<AllConfig | null>(null)
  const [keepaliveConfig, setKeepaliveConfig] =
    useState<KeepaliveConfig | null>(null)
  const [configLoading, setConfigLoading] = useState(false)
  const [saveLoading, setSaveLoading] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [unsavedChanges, setUnsavedChanges] = useState(false)

  // Logs state
  const [selectedLogService, setSelectedLogService] = useState<
    'signal' | 'trader' | 'proxy' | 'xray'
  >('signal')
  const [logs, setLogs] = useState('')
  const [logsLoading, setLogsLoading] = useState(false)

  // Export modal
  const [showExportModal, setShowExportModal] = useState(false)
  const [exportIncludeSensitive, setExportIncludeSensitive] = useState(false)

  // Login state
  const [loginStatus, setLoginStatus] = useState<{
    logged_in: boolean
    cookies_count: number
  }>({ logged_in: false, cookies_count: 0 })
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loginLoading, setLoginLoading] = useState(false)

  // Mobile menu
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  // Apply mode class to body
  useEffect(() => {
    if (mode === 'day') {
      document.body.classList.add('light-mode')
    } else {
      document.body.classList.remove('light-mode')
    }
  }, [mode])

  const loadStatus = useCallback(async () => {
    try {
      const [status, login] = await Promise.all([
        api.getServiceStatus(),
        api
          .getValuescanLoginStatus()
          .catch(() => ({ logged_in: false, cookies_count: 0 })),
      ])
      setServiceStatus({
        signal_monitor: status.signal_monitor || 'stopped',
        trader: status.trader || 'stopped',
        copytrade: status.copytrade || 'stopped',
        keepalive: status.keepalive || 'stopped',
      })
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
      const apiService =
        service === 'keepalive'
          ? 'signal'
          : (service as 'signal' | 'trader' | 'copytrade')
      const result = await api.controlService(apiService, action)
      if (result.success) {
        const actionNames = {
          start: '已启动',
          stop: '已停止',
          restart: '已重启',
        }
        toast.success(`${SERVICE_INFO[service].name} ${actionNames[action]}`)
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

  const loadConfig = async () => {
    setConfigLoading(true)
    try {
      const [configData, keepaliveData] = await Promise.all([
        api.getConfig(),
        api.getKeepaliveConfig().catch(() => null),
      ])
      setConfig(configData)
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

  const handleSaveConfig = async () => {
    setSaveLoading(true)
    try {
      if (activeConfigSection !== 'keepalive') {
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
      }
      if (activeConfigSection === 'keepalive' && keepaliveConfig) {
        const result = await api.saveKeepaliveConfig(keepaliveConfig)
        if (result.success) {
          toast.success('Keepalive 配置保存成功')
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
    setConfig((prev: any) => ({ ...prev, [section]: data }))
    setUnsavedChanges(true)
  }

  const updateKeepaliveConfig = (data: KeepaliveConfig) => {
    setKeepaliveConfig(data)
    setUnsavedChanges(true)
  }

  const handleLogin = async () => {
    if (!email || !password) {
      toast.error('请输入邮箱和密码')
      return
    }
    setLoginLoading(true)
    try {
      const result = await api.valuescanLogin(email, password)
      if (result.success) {
        toast.success(result.message || '登录成功')
        setEmail('')
        setPassword('')
        loadStatus()
      } else {
        toast.error(result.error || '登录失败')
      }
    } catch (e) {
      toast.error('登录失败: ' + e)
    } finally {
      setLoginLoading(false)
    }
  }

  const handleExportConfig = () => {
    if (!config) return
    let exportData = { ...config }
    if (!exportIncludeSensitive) {
      const removeSensitive = (obj: any): any => {
        if (!obj || typeof obj !== 'object') return obj
        const result: any = Array.isArray(obj) ? [] : {}
        for (const [key, value] of Object.entries(obj)) {
          if (
            /(secret|password|token|api[_-]?key|api[_-]?hash|private)/i.test(
              key
            )
          )
            continue
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

  const handleImportConfig = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const importedConfig = JSON.parse(e.target?.result as string)
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
      } catch {
        toast.error('导入失败：无效的 JSON 文件')
      }
    }
    reader.readAsText(file)
    event.target.value = ''
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <ParticleCanvas mode={mode} />
        <div className="text-center z-10">
          <div className="w-16 h-16 border-4 border-white/20 border-t-white rounded-full animate-spin mx-auto mb-6 shadow-[0_0_30px_rgba(255,255,255,0.1)]" />
          <p className="text-neutral-400 font-mono animate-pulse">
            INITIALIZING SYSTEM...
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen text-white selection:bg-white/20 overflow-x-hidden font-sans">
      <ParticleCanvas mode={mode} />
      <Toaster
        theme={mode === 'day' ? 'light' : 'dark'}
        position="top-right"
        className="!backdrop-blur-md"
      />

      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass rounded-none border-x-0 border-t-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-white to-neutral-400 flex items-center justify-center shadow-lg shadow-white/10">
                <Zap className="w-6 h-6 text-black" />
              </div>
              <div>
                <h1 className="text-xl font-bold tracking-tight text-white">
                  ValueScan
                </h1>
                <p className="text-[10px] text-neutral-400 font-mono tracking-widest uppercase">
                  Signal Monitor System
                </p>
              </div>
            </div>

            {/* Desktop Menu */}
            <div className="hidden md:flex items-center gap-1 bg-white/5 p-1 rounded-full border border-white/5 backdrop-blur-sm">
              {(['dashboard', 'config', 'logs'] as TabId[]).map((tab) => {
                const icons = {
                  dashboard: Activity,
                  config: Settings,
                  logs: Terminal,
                }
                const labels = {
                  dashboard: '仪表盘',
                  config: '系统配置',
                  logs: '运行日志',
                }
                const Icon = icons[tab]
                return (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={cn(
                      'flex items-center gap-2 px-5 py-2 rounded-full text-sm font-medium transition-all duration-300 relative',
                      activeTab === tab
                        ? 'text-black'
                        : 'text-neutral-400 hover:text-white hover:bg-white/5'
                    )}
                  >
                    {activeTab === tab && (
                      <motion.div
                        layoutId="activeTab"
                        className="absolute inset-0 bg-white rounded-full"
                        transition={{
                          type: 'spring',
                          bounce: 0.2,
                          duration: 0.6,
                        }}
                      />
                    )}
                    <span className="relative z-10 flex items-center gap-2">
                      <Icon className="w-4 h-4" />
                      {labels[tab]}
                    </span>
                  </button>
                )
              })}
            </div>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 text-neutral-400 hover:text-white"
            >
              {mobileMenuOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        <AnimatePresence>
          {mobileMenuOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="md:hidden border-t border-white/5 bg-black/90 backdrop-blur-xl overflow-hidden"
            >
              <div className="px-4 py-4 space-y-2">
                {(['dashboard', 'config', 'logs'] as TabId[]).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => {
                      setActiveTab(tab)
                      setMobileMenuOpen(false)
                    }}
                    className={cn(
                      'w-full flex items-center gap-3 px-4 py-3 rounded-xl text-left transition-colors',
                      activeTab === tab
                        ? 'bg-white/10 text-white'
                        : 'text-neutral-400 hover:bg-white/5'
                    )}
                  >
                    <span className="capitalize">{tab}</span>
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </nav>

      {/* Main Content */}
      <main className="pt-24 pb-12 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <AnimatePresence mode="wait">
          {activeTab === 'dashboard' && (
            <motion.div
              key="dashboard"
              {...staggerContainer}
              className="space-y-8"
            >
              {/* Header */}
              <SlideUp className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <h2 className="text-3xl font-bold tracking-tight text-white mb-2">
                    系统概览
                  </h2>
                  <div className="flex items-center gap-2 text-neutral-400 text-sm">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                    </span>
                    系统运行正常
                  </div>
                </div>
                <button
                  onClick={loadStatus}
                  className="btn-modern btn-modern-ghost bg-white/5 border border-white/5 hover:border-white/20"
                >
                  <RefreshCw className="w-4 h-4" />
                  刷新状态
                </button>
              </SlideUp>

              {/* Service Cards Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {(
                  Object.entries(SERVICE_INFO) as [
                    ServiceName,
                    (typeof SERVICE_INFO)[ServiceName],
                  ][]
                ).map(([key, info], index) => {
                  const status =
                    key === 'signal'
                      ? serviceStatus.signal_monitor
                      : key === 'keepalive'
                        ? serviceStatus.keepalive
                        : serviceStatus[key as keyof ServiceStatusData]
                  const Icon = info.icon
                  const isActive = status === 'running'

                  return (
                    <ScaleIn key={key} delay={index * 0.1} className="h-full">
                      <GlassCard
                        className={cn(
                          'h-full relative overflow-hidden group',
                          isActive && 'border-green-500/30 bg-green-500/5'
                        )}
                      >
                        {isActive && (
                          <div className="absolute -right-4 -top-4 w-20 h-20 bg-green-500/20 blur-2xl rounded-full group-hover:bg-green-500/30 transition-all" />
                        )}

                        <div className="flex justify-between items-start mb-6">
                          <div
                            className={cn(
                              'p-3 rounded-xl bg-white/5',
                              isActive ? 'text-green-400' : 'text-neutral-400'
                            )}
                          >
                            <Icon className="w-6 h-6" />
                          </div>
                          <div
                            className={cn(
                              'px-2.5 py-1 rounded-full text-xs font-medium border',
                              isActive
                                ? 'bg-green-500/10 border-green-500/20 text-green-400'
                                : 'bg-neutral-800/50 border-neutral-700 text-neutral-400'
                            )}
                          >
                            {status.toUpperCase()}
                          </div>
                        </div>

                        <h3 className="text-lg font-semibold mb-1">
                          {info.name}
                        </h3>
                        <p className="text-xs text-neutral-500 mb-6">
                          {info.description}
                        </p>

                        <div className="grid grid-cols-3 gap-2 mt-auto">
                          <button
                            onClick={() => handleServiceAction(key, 'start')}
                            disabled={
                              actionLoading !== null || status === 'running'
                            }
                            className="flex items-center justify-center p-2 rounded-lg bg-white/5 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors border border-white/5"
                            title="启动"
                          >
                            {actionLoading === `${key}-start` ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Play className="w-4 h-4" />
                            )}
                          </button>
                          <button
                            onClick={() => handleServiceAction(key, 'stop')}
                            disabled={
                              actionLoading !== null || status === 'stopped'
                            }
                            className="flex items-center justify-center p-2 rounded-lg bg-white/5 hover:bg-red-500/20 hover:text-red-400 disabled:opacity-30 disabled:cursor-not-allowed transition-colors border border-white/5"
                            title="停止"
                          >
                            {actionLoading === `${key}-stop` ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Square className="w-4 h-4" />
                            )}
                          </button>
                          <button
                            onClick={() => handleServiceAction(key, 'restart')}
                            disabled={actionLoading !== null}
                            className="flex items-center justify-center p-2 rounded-lg bg-white/5 hover:bg-blue-500/20 hover:text-blue-400 disabled:opacity-30 disabled:cursor-not-allowed transition-colors border border-white/5"
                            title="重启"
                          >
                            {actionLoading === `${key}-restart` ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <RotateCw className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                      </GlassCard>
                    </ScaleIn>
                  )
                })}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Quick Actions */}
                <SlideUp delay={0.2} className="lg:col-span-2">
                  <GlassCard className="h-full">
                    <div className="flex items-center gap-3 mb-6">
                      <Cpu className="w-5 h-5 text-neutral-400" />
                      <h3 className="font-semibold text-lg">系统操作</h3>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {[
                        {
                          label: '编辑配置',
                          desc: '修改系统参数',
                          icon: Settings,
                          action: () => setActiveTab('config'),
                        },
                        {
                          label: '查看日志',
                          desc: '监控运行状态',
                          icon: FileText,
                          action: () => setActiveTab('logs'),
                        },
                        {
                          label: '导出配置',
                          desc: '备份当前设置',
                          icon: Download,
                          action: () => setShowExportModal(true),
                        },
                        {
                          label: '导入配置',
                          desc: '恢复系统设置',
                          icon: Upload,
                          action: () =>
                            document.getElementById('config-import')?.click(),
                        },
                      ].map((item, i) => (
                        <button
                          key={i}
                          onClick={item.action}
                          className="flex items-center gap-4 p-4 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 hover:border-white/10 transition-all group text-left"
                        >
                          <div className="w-10 h-10 rounded-lg bg-neutral-900 flex items-center justify-center group-hover:scale-110 transition-transform">
                            <item.icon className="w-5 h-5 text-neutral-400 group-hover:text-white transition-colors" />
                          </div>
                          <div>
                            <div className="font-medium text-white">
                              {item.label}
                            </div>
                            <div className="text-xs text-neutral-500">
                              {item.desc}
                            </div>
                          </div>
                          <ChevronRight className="w-4 h-4 text-neutral-600 ml-auto group-hover:translate-x-1 transition-transform" />
                        </button>
                      ))}
                      <input
                        id="config-import"
                        type="file"
                        accept=".json"
                        onChange={handleImportConfig}
                        className="hidden"
                      />
                    </div>
                  </GlassCard>
                </SlideUp>

                {/* Login Status */}
                <SlideUp delay={0.3}>
                  <GlassCard className="h-full">
                    <div className="flex items-center justify-between mb-6">
                      <div className="flex items-center gap-3">
                        <User className="w-5 h-5 text-neutral-400" />
                        <h3 className="font-semibold text-lg">ValueScan</h3>
                      </div>
                      {loginStatus.logged_in ? (
                        <span className="px-2 py-1 rounded-md bg-green-500/10 text-green-400 text-xs font-medium border border-green-500/20">
                          已登录
                        </span>
                      ) : (
                        <span className="px-2 py-1 rounded-md bg-red-500/10 text-red-400 text-xs font-medium border border-red-500/20">
                          未登录
                        </span>
                      )}
                    </div>

                    {!loginStatus.logged_in ? (
                      <div className="space-y-4">
                        <div className="space-y-3">
                          <div className="relative group">
                            <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500 group-focus-within:text-white transition-colors" />
                            <input
                              type="email"
                              value={email}
                              onChange={(e) => setEmail(e.target.value)}
                              placeholder="邮箱地址"
                              className="input-modern pl-10"
                            />
                          </div>
                          <div className="relative group">
                            <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500 group-focus-within:text-white transition-colors" />
                            <input
                              type="password"
                              value={password}
                              onChange={(e) => setPassword(e.target.value)}
                              placeholder="密码"
                              onKeyDown={(e) =>
                                e.key === 'Enter' && handleLogin()
                              }
                              className="input-modern pl-10"
                            />
                          </div>
                        </div>
                        <button
                          onClick={handleLogin}
                          disabled={loginLoading || !email || !password}
                          className="w-full btn-modern btn-modern-primary"
                        >
                          {loginLoading ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <LogIn className="w-4 h-4" />
                          )}
                          登录
                        </button>
                      </div>
                    ) : (
                      <div className="text-center py-8 space-y-4">
                        <div className="w-16 h-16 rounded-full bg-green-500/10 mx-auto flex items-center justify-center border border-green-500/20">
                          <CheckCircle className="w-8 h-8 text-green-500" />
                        </div>
                        <div>
                          <p className="text-white font-medium">账户连接正常</p>
                          <p className="text-sm text-neutral-500 mt-1">
                            Cookies Count: {loginStatus.cookies_count}
                          </p>
                        </div>
                        <button
                          onClick={loadStatus}
                          className="btn-modern btn-modern-ghost text-xs"
                        >
                          刷新状态
                        </button>
                      </div>
                    )}
                  </GlassCard>
                </SlideUp>
              </div>
            </motion.div>
          )}

          {activeTab === 'config' && (
            <motion.div
              key="config"
              {...staggerContainer}
              className="max-w-4xl mx-auto space-y-6"
            >
              {configLoading ? (
                <div className="flex justify-center py-20">
                  <Loader2 className="w-8 h-8 animate-spin text-white" />
                </div>
              ) : config ? (
                <>
                  <SlideUp className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <h2 className="text-3xl font-bold tracking-tight">
                        系统配置
                      </h2>
                      <p className="text-neutral-400 text-sm mt-1">
                        管理核心模块参数
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      {unsavedChanges && (
                        <span className="flex items-center gap-2 text-sm text-amber-500 bg-amber-500/10 px-3 py-1.5 rounded-full border border-amber-500/20">
                          <AlertCircle className="w-4 h-4" />
                          未保存
                        </span>
                      )}
                      <button
                        onClick={handleSaveConfig}
                        disabled={
                          saveLoading || Object.keys(fieldErrors).length > 0
                        }
                        className="btn-modern btn-modern-primary"
                      >
                        {saveLoading ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <CheckCircle className="w-4 h-4" />
                        )}
                        保存配置
                      </button>
                    </div>
                  </SlideUp>

                  <SlideUp delay={0.1}>
                    <div className="flex gap-2 p-1 bg-white/5 rounded-xl backdrop-blur-md border border-white/5 overflow-x-auto">
                      {[
                        { id: 'signal' as const, label: '信号监控', icon: Zap },
                        { id: 'trader' as const, label: '自动交易', icon: Bot },
                        {
                          id: 'copytrade' as const,
                          label: '跟单系统',
                          icon: Eye,
                        },
                        {
                          id: 'keepalive' as const,
                          label: '服务监控',
                          icon: Shield,
                        },
                      ].map((tab) => {
                        const Icon = tab.icon
                        const isActive = activeConfigSection === tab.id
                        return (
                          <button
                            key={tab.id}
                            onClick={() => setActiveConfigSection(tab.id)}
                            className={cn(
                              'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap',
                              isActive
                                ? 'bg-white text-black shadow-lg'
                                : 'text-neutral-400 hover:text-white hover:bg-white/5'
                            )}
                          >
                            <Icon className="w-4 h-4" />
                            {tab.label}
                          </button>
                        )
                      })}
                    </div>
                  </SlideUp>

                  <SlideUp delay={0.2}>
                    <GlassCard noHover className="min-h-[500px]">
                      {activeConfigSection === 'signal' && (
                        <SignalMonitorConfigSection
                          config={config.signal || {}}
                          onChange={(data) =>
                            updateConfigSection('signal', data)
                          }
                          errors={fieldErrors}
                        />
                      )}
                      {activeConfigSection === 'trader' && (
                        <TraderConfigSection
                          config={config.trader || {}}
                          onChange={(data) =>
                            updateConfigSection('trader', data)
                          }
                          errors={fieldErrors}
                        />
                      )}
                      {activeConfigSection === 'copytrade' && (
                        <CopyTradeConfigSection
                          config={config.copytrade || {}}
                          onChange={(data) =>
                            updateConfigSection('copytrade', data)
                          }
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
                    </GlassCard>
                  </SlideUp>
                </>
              ) : (
                <div className="text-center text-neutral-500 py-12">
                  加载失败
                </div>
              )}
            </motion.div>
          )}

          {activeTab === 'logs' && (
            <motion.div
              key="logs"
              {...staggerContainer}
              className="h-[calc(100vh-10rem)] flex flex-col gap-4"
            >
              <SlideUp className="flex items-center justify-between shrink-0">
                <div>
                  <h2 className="text-3xl font-bold tracking-tight">
                    运行日志
                  </h2>
                  <p className="text-neutral-400 text-sm mt-1">
                    系统实时输出监控
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <select
                    value={selectedLogService}
                    onChange={(e) =>
                      setSelectedLogService(e.target.value as any)
                    }
                    className="input-modern w-40"
                  >
                    <option value="signal">信号监控</option>
                    <option value="trader">自动交易</option>
                    <option value="proxy">代理检测</option>
                    <option value="xray">Xray</option>
                  </select>
                  <button
                    onClick={loadLogs}
                    disabled={logsLoading}
                    className="btn-modern btn-modern-ghost bg-white/5"
                  >
                    {logsLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <RefreshCw className="w-4 h-4" />
                    )}
                    刷新
                  </button>
                </div>
              </SlideUp>

              <SlideUp delay={0.1} className="flex-1 min-h-0">
                <GlassCard
                  noHover
                  className="h-full flex flex-col p-0 overflow-hidden bg-[#0c0c0c]/80"
                >
                  <div className="flex items-center gap-2 px-4 py-2 border-b border-white/5 bg-white/5">
                    <Terminal className="w-4 h-4 text-neutral-500" />
                    <span className="text-xs text-neutral-500 font-mono">
                      console output
                    </span>
                  </div>
                  <div className="flex-1 overflow-auto p-4 custom-scrollbar">
                    <pre className="font-mono text-sm leading-relaxed text-neutral-300 whitespace-pre-wrap">
                      {logsLoading ? (
                        <span className="animate-pulse">Loading logs...</span>
                      ) : (
                        logs || (
                          <span className="text-neutral-600 italic">
                            暂无日志数据
                          </span>
                        )
                      )}
                    </pre>
                  </div>
                </GlassCard>
              </SlideUp>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Export Modal */}
      <AnimatePresence>
        {showExportModal && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
              onClick={() => setShowExportModal(false)}
            />
            <FadeIn className="relative w-full max-w-md">
              <GlassCard className="bg-neutral-900 border border-white/10 shadow-2xl">
                <h3 className="text-xl font-bold mb-4">导出配置</h3>
                <div className="space-y-4">
                  <label className="flex items-center gap-4 p-4 rounded-xl border border-white/5 bg-white/5 hover:bg-white/10 cursor-pointer transition-colors">
                    <div className="flex h-5 w-5 items-center justify-center rounded-full border border-neutral-500">
                      {!exportIncludeSensitive && (
                        <div className="h-3 w-3 rounded-full bg-white" />
                      )}
                    </div>
                    <input
                      type="radio"
                      checked={!exportIncludeSensitive}
                      onChange={() => setExportIncludeSensitive(false)}
                      className="hidden"
                    />
                    <div>
                      <p className="font-medium">安全导出</p>
                      <p className="text-xs text-neutral-400">
                        自动移除 API Key、密码等敏感信息
                      </p>
                    </div>
                  </label>
                  <label className="flex items-center gap-4 p-4 rounded-xl border border-white/5 bg-white/5 hover:bg-white/10 cursor-pointer transition-colors">
                    <div className="flex h-5 w-5 items-center justify-center rounded-full border border-neutral-500">
                      {exportIncludeSensitive && (
                        <div className="h-3 w-3 rounded-full bg-white" />
                      )}
                    </div>
                    <input
                      type="radio"
                      checked={exportIncludeSensitive}
                      onChange={() => setExportIncludeSensitive(true)}
                      className="hidden"
                    />
                    <div>
                      <p className="font-medium">完整导出</p>
                      <p className="text-xs text-amber-500">
                        包含所有敏感信息，请妥善保管文件！
                      </p>
                    </div>
                  </label>
                </div>
                <div className="flex justify-end gap-3 mt-8">
                  <button
                    onClick={() => setShowExportModal(false)}
                    className="px-4 py-2 text-sm font-medium text-neutral-400 hover:text-white transition-colors"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleExportConfig}
                    className="btn-modern btn-modern-primary"
                  >
                    确认导出
                  </button>
                </div>
              </GlassCard>
            </FadeIn>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}

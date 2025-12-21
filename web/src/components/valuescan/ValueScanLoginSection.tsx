import { useState, useEffect } from 'react'
import {
  RefreshCw,
  CheckCircle,
  XCircle,
  Clock,
  Eye,
  EyeOff,
  User,
  Save,
} from 'lucide-react'
import { ConfigFieldGroup } from './ConfigFieldGroup'
import { withBasePath } from '../../lib/appBase'

interface TokenStatus {
  token_valid: boolean
  token_expiry: string | null
  has_credentials: boolean
  email: string
}

export function ValueScanLoginSection() {
  const apiBase = withBasePath('/api')
  const [showPassword, setShowPassword] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [tokenStatus, setTokenStatus] = useState<TokenStatus | null>(null)
  const [envMessage, setEnvMessage] = useState<{
    type: 'success' | 'error'
    text: string
  } | null>(null)
  const [envLoading, setEnvLoading] = useState(false)
  const [envSaving, setEnvSaving] = useState(false)
  const [envDirty, setEnvDirty] = useState(false)
  const [envConfig, setEnvConfig] = useState({
    email: '',
    password: '',
    autoRelogin: true,
  })

  // 获取 token 状态
  const fetchTokenStatus = async () => {
    try {
      const resp = await fetch(`${apiBase}/valuescan/token/status`)
      const data = await resp.json()
      if (data.success) {
        setTokenStatus(data)
      }
    } catch (e) {
      console.error('获取 token 状态失败:', e)
    }
  }

  const fetchEnvConfig = async () => {
    setEnvLoading(true)
    try {
      const resp = await fetch(`${apiBase}/valuescan/env`)
      const data = await resp.json()
      if (data.success) {
        const env = data.env || {}
        const autoRelogin =
          env.VALUESCAN_AUTO_RELOGIN === '1' ||
          env.VALUESCAN_AUTO_RELOGIN === 'true'
        setEnvConfig({
          email: env.VALUESCAN_EMAIL || '',
          password: env.VALUESCAN_PASSWORD || '',
          autoRelogin,
        })
        setEnvDirty(false)
      }
    } catch (e) {
      console.error('获取服务器环境变量失败', e)
    } finally {
      setEnvLoading(false)
    }
  }

  useEffect(() => {
    fetchTokenStatus()
    fetchEnvConfig()
    // 每 30 秒刷新状态
    const interval = setInterval(fetchTokenStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  // 刷新 token
  const handleRefresh = async () => {
    setRefreshing(true)
    setEnvMessage(null)

    try {
      const resp = await fetch(`${apiBase}/valuescan/token/refresh`, {
        method: 'POST',
      })
      const data = await resp.json()

      if (data.success) {
        setEnvMessage({ type: 'success', text: 'Token 刷新成功！' })
        fetchTokenStatus()
      } else {
        setEnvMessage({ type: 'error', text: data.error || '刷新失败' })
      }
    } catch (e) {
      setEnvMessage({ type: 'error', text: '网络错误，请重试' })
    } finally {
      setRefreshing(false)
    }
  }

  const handleEnvSave = async () => {
    setEnvSaving(true)
    setEnvMessage(null)
    try {
      const resp = await fetch(`${apiBase}/valuescan/env`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          env: {
            VALUESCAN_LOGIN_METHOD: 'browser',
            VALUESCAN_AUTO_RELOGIN: envConfig.autoRelogin ? '1' : '0',
            VALUESCAN_AUTO_RELOGIN_USE_BROWSER: '1',
            VALUESCAN_AUTO_RELOGIN_COOLDOWN: 300,
            VALUESCAN_EMAIL: envConfig.email,
            VALUESCAN_PASSWORD: envConfig.password,
          },
        }),
      })
      const data = await resp.json()
      if (data.success) {
        setEnvMessage({ type: 'success', text: '凭据已保存，服务将自动登录' })
        setEnvDirty(false)
        fetchEnvConfig()
        // 等待一会儿后刷新 token 状态
        setTimeout(fetchTokenStatus, 3000)
      } else {
        setEnvMessage({
          type: 'error',
          text: data.error || '保存失败',
        })
      }
    } catch (e) {
      setEnvMessage({ type: 'error', text: '网络错误，请重试' })
    } finally {
      setEnvSaving(false)
    }
  }

  // 格式化过期时间
  const formatExpiry = (expiry: string | null) => {
    if (!expiry) return '未知'
    const date = new Date(expiry)
    const now = new Date()
    const diff = date.getTime() - now.getTime()

    if (diff < 0) return '已过期'

    const minutes = Math.floor(diff / 60000)
    if (minutes < 60) return `${minutes} 分钟后`

    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours} 小时 ${minutes % 60} 分钟后`

    return date.toLocaleString('zh-CN')
  }

  const inputClass =
    'w-full px-3 py-2 bg-neutral-900 border border-neutral-800 rounded-lg text-sm text-white placeholder:text-neutral-600 focus:outline-none focus:border-neutral-600 transition-colors'
  const labelClass = 'block text-sm text-neutral-400 mb-1.5'

  return (
    <ConfigFieldGroup
      title="ValueScan 账号"
      description="保存账号密码后，系统会自动登录并保持 Token 有效"
      icon={<User className="w-5 h-5" />}
    >
      <div className="space-y-4">
        {/* Token 状态 */}
        {tokenStatus && (
          <div
            className={`p-3 rounded-lg border ${
              tokenStatus.token_valid
                ? 'bg-green-500/10 border-green-500/30'
                : 'bg-yellow-500/10 border-yellow-500/30'
            }`}
          >
            <div className="flex items-center gap-2">
              {tokenStatus.token_valid ? (
                <CheckCircle className="w-4 h-4 text-green-500" />
              ) : (
                <XCircle className="w-4 h-4 text-yellow-500" />
              )}
              <span
                className={`text-sm font-medium ${
                  tokenStatus.token_valid ? 'text-green-400' : 'text-yellow-400'
                }`}
              >
                {tokenStatus.token_valid ? '已登录' : '未登录'}
              </span>
            </div>
            {tokenStatus.token_valid && tokenStatus.token_expiry && (
              <div className="flex items-center gap-2 mt-2 text-xs text-neutral-400">
                <Clock className="w-3 h-3" />
                <span>Token 过期: {formatExpiry(tokenStatus.token_expiry)}</span>
              </div>
            )}
            {tokenStatus.email && (
              <div className="mt-1 text-xs text-neutral-500">
                账号: {tokenStatus.email}
              </div>
            )}
          </div>
        )}

        {/* 账号密码表单 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className={labelClass}>邮箱</label>
            <input
              type="email"
              className={inputClass}
              value={envConfig.email}
              onChange={(e) => {
                setEnvConfig((prev) => ({
                  ...prev,
                  email: e.target.value,
                }))
                setEnvDirty(true)
              }}
              placeholder="your@email.com"
            />
          </div>
          <div>
            <label className={labelClass}>密码</label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                className={`${inputClass} pr-10`}
                value={envConfig.password}
                onChange={(e) => {
                  setEnvConfig((prev) => ({
                    ...prev,
                    password: e.target.value,
                  }))
                  setEnvDirty(true)
                }}
                placeholder="••••••••"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-neutral-300"
              >
                {showPassword ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>
        </div>

        {/* 自动登录选项 */}
        <label className="flex items-center gap-2 text-sm text-neutral-300">
          <input
            type="checkbox"
            checked={envConfig.autoRelogin}
            onChange={(e) => {
              setEnvConfig((prev) => ({
                ...prev,
                autoRelogin: e.target.checked,
              }))
              setEnvDirty(true)
            }}
          />
          Token 过期时自动重新登录
        </label>

        {/* 消息提示 */}
        {envMessage && (
          <div
            className={`p-3 rounded-lg text-sm ${
              envMessage.type === 'success'
                ? 'bg-green-500/10 text-green-400 border border-green-500/30'
                : 'bg-red-500/10 text-red-400 border border-red-500/30'
            }`}
          >
            {envMessage.text}
          </div>
        )}

        {/* 按钮 */}
        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleEnvSave}
            disabled={envSaving || envLoading || !envDirty || !envConfig.email || !envConfig.password}
            className="flex items-center justify-center gap-2 px-4 py-2 bg-white text-black rounded-lg text-sm font-medium hover:bg-neutral-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {envSaving ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            保存凭据
          </button>
          {tokenStatus?.token_valid && (
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center justify-center gap-2 px-4 py-2 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {refreshing ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              刷新 Token
            </button>
          )}
        </div>

        {/* 说明 */}
        <p className="text-xs text-neutral-500">
          保存账号密码后，系统会在后台自动登录 ValueScan 并定期刷新 Token。
          无需手动点击登录按钮。
        </p>
      </div>
    </ConfigFieldGroup>
  )
}

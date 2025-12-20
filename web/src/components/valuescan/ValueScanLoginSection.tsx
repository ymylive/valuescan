import { useState, useEffect } from 'react'
import {
  LogIn,
  RefreshCw,
  CheckCircle,
  XCircle,
  Clock,
  Eye,
  EyeOff,
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
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [message, setMessage] = useState<{
    type: 'success' | 'error'
    text: string
  } | null>(null)
  const [tokenStatus, setTokenStatus] = useState<TokenStatus | null>(null)

  // 获取 token 状态
  const fetchTokenStatus = async () => {
    try {
      const resp = await fetch(`${apiBase}/valuescan/token/status`)
      const data = await resp.json()
      if (data.success) {
        setTokenStatus(data)
        if (data.email) {
          setEmail(data.email)
        }
      }
    } catch (e) {
      console.error('获取 token 状态失败:', e)
    }
  }

  useEffect(() => {
    fetchTokenStatus()
    // 每 30 秒刷新状态
    const interval = setInterval(fetchTokenStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  // 自动登录
  const handleLogin = async () => {
    if (!email || !password) {
      setMessage({ type: 'error', text: '请输入邮箱和密码' })
      return
    }

    setLoading(true)
    setMessage(null)

    try {
      const resp = await fetch(`${apiBase}/valuescan/login/auto`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      const data = await resp.json()

      if (data.success) {
        setMessage({ type: 'success', text: '登录成功！Token 已更新' })
        setPassword('') // 清空密码
        fetchTokenStatus()
      } else {
        setMessage({ type: 'error', text: data.error || '登录失败' })
      }
    } catch (e) {
      setMessage({ type: 'error', text: '网络错误，请重试' })
    } finally {
      setLoading(false)
    }
  }

  // 刷新 token
  const handleRefresh = async () => {
    setRefreshing(true)
    setMessage(null)

    try {
      const resp = await fetch(`${apiBase}/valuescan/token/refresh`, {
        method: 'POST',
      })
      const data = await resp.json()

      if (data.success) {
        setMessage({ type: 'success', text: 'Token 刷新成功！' })
        fetchTokenStatus()
      } else {
        setMessage({ type: 'error', text: data.error || '刷新失败' })
      }
    } catch (e) {
      setMessage({ type: 'error', text: '网络错误，请重试' })
    } finally {
      setRefreshing(false)
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
      title="ValueScan 登录"
      description="自动登录 ValueScan 获取信号监测 Token"
      icon={<LogIn className="w-5 h-5" />}
    >
      <div className="space-y-4">
        {/* Token 状态 */}
        {tokenStatus && (
          <div
            className={`p-3 rounded-lg border ${
              tokenStatus.token_valid
                ? 'bg-green-500/10 border-green-500/30'
                : 'bg-red-500/10 border-red-500/30'
            }`}
          >
            <div className="flex items-center gap-2">
              {tokenStatus.token_valid ? (
                <CheckCircle className="w-4 h-4 text-green-500" />
              ) : (
                <XCircle className="w-4 h-4 text-red-500" />
              )}
              <span
                className={`text-sm font-medium ${
                  tokenStatus.token_valid ? 'text-green-400' : 'text-red-400'
                }`}
              >
                {tokenStatus.token_valid ? 'Token 有效' : 'Token 无效或已过期'}
              </span>
            </div>
            {tokenStatus.token_expiry && (
              <div className="flex items-center gap-2 mt-2 text-xs text-neutral-400">
                <Clock className="w-3 h-3" />
                <span>过期时间: {formatExpiry(tokenStatus.token_expiry)}</span>
              </div>
            )}
            {tokenStatus.email && (
              <div className="mt-1 text-xs text-neutral-500">
                账号: {tokenStatus.email}
              </div>
            )}
          </div>
        )}

        {/* 登录表单 */}
        <div className="space-y-3">
          <div>
            <label className={labelClass}>邮箱</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>密码</label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className={`${inputClass} pr-10`}
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

        {/* 消息提示 */}
        {message && (
          <div
            className={`p-3 rounded-lg text-sm ${
              message.type === 'success'
                ? 'bg-green-500/10 text-green-400 border border-green-500/30'
                : 'bg-red-500/10 text-red-400 border border-red-500/30'
            }`}
          >
            {message.text}
          </div>
        )}

        {/* 按钮 */}
        <div className="flex gap-3">
          <button
            onClick={handleLogin}
            disabled={loading || !email || !password}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-white text-black rounded-lg text-sm font-medium hover:bg-neutral-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                登录中...
              </>
            ) : (
              <>
                <LogIn className="w-4 h-4" />
                登录
              </>
            )}
          </button>

          {tokenStatus?.has_credentials && (
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
          使用 Chrome 自动登录 ValueScan，获取信号监测所需的 Token。
          登录后系统会自动保存凭据并定期刷新 Token。
        </p>
      </div>
    </ConfigFieldGroup>
  )
}

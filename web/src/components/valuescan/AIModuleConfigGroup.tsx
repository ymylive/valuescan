import { useState } from 'react'
import { Loader2, CheckCircle2, XCircle } from 'lucide-react'
import { SensitiveFieldInput } from './SensitiveFieldInput'
import type { AIModuleConfig, AITestResult } from '../../types/config'

interface AIModuleConfigGroupProps {
  title: string
  description: string
  enabled: boolean
  config: AIModuleConfig
  onEnabledChange: (enabled: boolean) => void
  onConfigChange: (config: AIModuleConfig) => void
  onTestConnection: (config: AIModuleConfig) => Promise<AITestResult>
  showIntervalHours?: boolean
  intervalHours?: number
  onIntervalHoursChange?: (hours: number) => void
  showLookbackHours?: boolean
  lookbackHours?: number
  onLookbackHoursChange?: (hours: number) => void
}

export function AIModuleConfigGroup({
  title,
  description,
  enabled,
  config,
  onEnabledChange,
  onConfigChange,
  onTestConnection,
  showIntervalHours = false,
  intervalHours,
  onIntervalHoursChange,
  showLookbackHours = false,
  lookbackHours,
  onLookbackHoursChange,
}: AIModuleConfigGroupProps) {
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<AITestResult | null>(null)

  const handleTestConnection = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const result = await onTestConnection(config)
      setTestResult(result)
      // 3秒后自动清除测试结果
      setTimeout(() => setTestResult(null), 3000)
    } catch (error) {
      setTestResult({
        success: false,
        error: error instanceof Error ? error.message : '测试失败',
      })
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* 标题和描述 */}
      <div className="flex items-start justify-between">
        <div>
          <h4 className="text-sm font-medium text-white">{title}</h4>
          <p className="text-xs text-neutral-400 mt-1">{description}</p>
        </div>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => onEnabledChange(e.target.checked)}
            className="w-4 h-4 rounded border-neutral-600 bg-neutral-800 text-blue-500 focus:ring-2 focus:ring-blue-500/20"
          />
          <span className="text-sm text-neutral-300">启用</span>
        </label>
      </div>

      {/* 配置表单 */}
      <div className={`space-y-3 ${!enabled ? 'opacity-50 pointer-events-none' : ''}`}>
        {/* API URL */}
        <div className="space-y-1.5">
          <label className="block text-sm text-neutral-400">API URL</label>
          <input
            type="text"
            value={config.api_url}
            onChange={(e) =>
              onConfigChange({ ...config, api_url: e.target.value })
            }
            placeholder="https://api.example.com/v1/chat/completions"
            disabled={!enabled}
            className="input-modern"
          />
        </div>

        {/* API Key */}
        <SensitiveFieldInput
          label="API Key"
          value={config.api_key}
          onChange={(value) => onConfigChange({ ...config, api_key: value })}
          placeholder="sk-..."
          disabled={!enabled}
        />

        {/* Model */}
        <div className="space-y-1.5">
          <label className="block text-sm text-neutral-400">模型</label>
          <input
            type="text"
            value={config.model}
            onChange={(e) =>
              onConfigChange({ ...config, model: e.target.value })
            }
            placeholder="gpt-5.2"
            disabled={!enabled}
            className="input-modern"
          />
        </div>

        {/* Interval Hours (可选) */}
        {showIntervalHours && intervalHours !== undefined && onIntervalHoursChange && (
          <div className="space-y-1.5">
            <label className="block text-sm text-neutral-400">
              分析间隔（小时）
            </label>
            <input
              type="number"
              value={intervalHours}
              onChange={(e) => onIntervalHoursChange(parseFloat(e.target.value) || 1)}
              min="0.5"
              step="0.5"
              disabled={!enabled}
              className="input-modern"
            />
          </div>
        )}

        {/* Lookback Hours (可选) */}
        {showLookbackHours && lookbackHours !== undefined && onLookbackHoursChange && (
          <div className="space-y-1.5">
            <label className="block text-sm text-neutral-400">
              信号回溯时间（小时）
            </label>
            <input
              type="number"
              value={lookbackHours}
              onChange={(e) => onLookbackHoursChange(parseFloat(e.target.value) || 1)}
              min="0.5"
              step="0.5"
              disabled={!enabled}
              className="input-modern"
            />
          </div>
        )}

        {/* 测试连接按钮 */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleTestConnection}
            disabled={!enabled || testing || !config.api_key || !config.api_url || !config.model}
            className="btn-secondary text-sm px-4 py-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {testing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                测试中...
              </>
            ) : (
              '测试连接'
            )}
          </button>

          {/* 测试结果 */}
          {testResult && (
            <div
              className={`flex items-center gap-2 text-sm ${
                testResult.success ? 'text-green-400' : 'text-red-400'
              }`}
            >
              {testResult.success ? (
                <>
                  <CheckCircle2 className="w-4 h-4" />
                  <span>{testResult.message || '连接成功'}</span>
                </>
              ) : (
                <>
                  <XCircle className="w-4 h-4" />
                  <span>{testResult.error || '连接失败'}</span>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

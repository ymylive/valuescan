import { useState } from 'react'
import { api } from '../services/api'
import { useTheme } from '../hooks/useTheme'

export const Controls = () => {
  const { theme } = useTheme()
  const [status, setStatus] = useState('')

  const isDark = theme === 'day'
  const border = isDark ? 'border-white/20' : 'border-black/20'
  const hover = isDark ? 'hover:bg-white/10' : 'hover:bg-black/10'

  const trigger = async (fn: () => Promise<any>, name: string) => {
    setStatus(`Triggering ${name}...`)
    try {
      await fn()
      setStatus(`${name} triggered successfully`)
    } catch (e) {
      setStatus(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    }
  }

  const modules = [
    { name: 'Anomaly Detection', key: 'triggerAnomaly' },
    { name: 'Macro Analysis', key: 'triggerMacro' },
    { name: 'AI Brief', key: 'triggerAiBrief' },
    { name: 'News Fetch', key: 'triggerNews' },
    { name: 'Econ Data', key: 'triggerEcon' }
  ]

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl mb-4">Scheduler Control</h2>
        <div className="flex gap-4">
          <button
            onClick={() => trigger(api.control.startScheduler, 'Start Scheduler')}
            className={`border ${border} ${hover} px-6 py-3 transition-colors`}
          >
            Start Scheduler
          </button>
          <button
            onClick={() => trigger(api.control.stopScheduler, 'Stop Scheduler')}
            className={`border ${border} ${hover} px-6 py-3 transition-colors`}
          >
            Stop Scheduler
          </button>
        </div>
      </div>

      <div>
        <h2 className="text-2xl mb-4">Manual Triggers</h2>
        <div className="grid grid-cols-2 gap-4">
          {modules.map(mod => (
            <button
              key={mod.key}
              onClick={() => trigger(api.control[mod.key as keyof typeof api.control] as any, mod.name)}
              className={`border ${border} ${hover} p-6 text-left transition-colors`}
            >
              <div className="text-lg font-bold">{mod.name}</div>
              <div className="text-sm opacity-60 mt-2">Click to trigger manually</div>
            </button>
          ))}
        </div>
      </div>

      {status && (
        <div className={`border ${border} p-4 mt-4`}>
          {status}
        </div>
      )}
    </div>
  )
}

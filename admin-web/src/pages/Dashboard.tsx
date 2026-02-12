import { useState, useEffect } from 'react'
import { api } from '../services/api'
import type { HealthResponse } from '../types/api'
import { useTheme } from '../hooks/useTheme'

export const Dashboard = () => {
  const { theme } = useTheme()
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const isDark = theme === 'day'
  const border = isDark ? 'border-white/20' : 'border-black/20'
  const hover = isDark ? 'hover:bg-white/10' : 'hover:bg-black/10'

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.health()
        setHealth(data)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load')
      } finally {
        setLoading(false)
      }
    }
    load()
    const interval = setInterval(load, 15000)
    return () => clearInterval(interval)
  }, [])

  if (loading) return <div>Loading...</div>
  if (error) return <div className="text-red-500">Error: {error}</div>
  if (!health) return null

  const statusColor = (status: string) => {
    if (status === 'running') return isDark ? 'text-green-400' : 'text-green-600'
    if (status === 'error') return 'text-red-500'
    return isDark ? 'text-gray-400' : 'text-gray-600'
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl mb-4">System Health</h2>
        <div className={`border ${border} p-6 space-y-4`}>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <div className="text-sm opacity-60">Version</div>
              <div className="text-xl">{health.version}</div>
            </div>
            <div>
              <div className="text-sm opacity-60">Uptime</div>
              <div className="text-xl">{Math.floor(health.uptime_seconds / 3600)}h</div>
            </div>
            <div>
              <div className="text-sm opacity-60">Queue</div>
              <div className="text-xl">{health.queue_backlog}</div>
            </div>
          </div>
        </div>
      </div>

      <div>
        <h2 className="text-2xl mb-4">Tasks</h2>
        <div className="space-y-2">
          {Object.entries(health.tasks).map(([name, task]) => (
            <div key={name} className={`border ${border} p-4 flex justify-between items-center`}>
              <div>
                <div className="font-bold">{name.replace(/_/g, ' ').toUpperCase()}</div>
                <div className="text-sm opacity-60">
                  Last: {new Date(task.last_run).toLocaleString()}
                </div>
              </div>
              <div className={`text-lg ${statusColor(task.status)}`}>
                {task.status.toUpperCase()}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h2 className="text-2xl mb-4">Quick Actions</h2>
        <div className="grid grid-cols-3 gap-4">
          {['anomaly', 'macro', 'ai_brief', 'news', 'econ'].map(action => (
            <button
              key={action}
              onClick={() => api.control[`trigger${action.split('_').map(w => w[0].toUpperCase() + w.slice(1)).join('')}` as keyof typeof api.control]()}
              className={`border ${border} ${hover} p-4 transition-colors`}
            >
              Trigger {action.replace(/_/g, ' ').toUpperCase()}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

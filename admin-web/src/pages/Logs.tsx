import { useState, useEffect, useRef } from 'react'
import { api } from '../services/api'
import type { LogEntry } from '../types/api'
import { useTheme } from '../hooks/useTheme'

export const Logs = () => {
  const { theme } = useTheme()
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [autoScroll, setAutoScroll] = useState(true)
  const [level, setLevel] = useState('')
  const logsEndRef = useRef<HTMLDivElement>(null)

  const isDark = theme === 'day'
  const border = isDark ? 'border-white/20' : 'border-black/20'
  const hover = isDark ? 'hover:bg-white/10' : 'hover:bg-black/10'

  useEffect(() => {
    const es = api.logs.stream()
    es.onmessage = (e) => {
      const log: LogEntry = JSON.parse(e.data)
      setLogs(prev => [...prev, log].slice(-200))
    }
    return () => es.close()
  }, [])

  useEffect(() => {
    if (autoScroll) {
      logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, autoScroll])

  const levelColor = (l: string) => {
    if (l === 'error') return 'text-red-500'
    if (l === 'warning') return isDark ? 'text-yellow-400' : 'text-yellow-600'
    return isDark ? 'text-gray-400' : 'text-gray-600'
  }

  const filtered = level ? logs.filter(l => l.level === level) : logs

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl">Logs</h2>
        <div className="flex gap-4">
          <select
            value={level}
            onChange={e => setLevel(e.target.value)}
            className={`border ${border} px-4 py-2 bg-transparent`}
          >
            <option value="">All Levels</option>
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="error">Error</option>
          </select>
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`border ${border} ${hover} px-4 py-2 transition-colors ${autoScroll ? (isDark ? 'bg-white/20' : 'bg-black/20') : ''}`}
          >
            Auto-scroll
          </button>
          <button
            onClick={() => {
              const text = filtered.map(l => `[${l.timestamp}] [${l.level}] [${l.module}] ${l.message}`).join('\n')
              navigator.clipboard.writeText(text)
            }}
            className={`border ${border} ${hover} px-4 py-2 transition-colors`}
          >
            Copy
          </button>
        </div>
      </div>

      <div className={`border ${border} h-[600px] overflow-y-auto p-4 space-y-1`}>
        {filtered.map((log, i) => (
          <div key={i} className="font-mono text-sm">
            <span className="opacity-60">{new Date(log.timestamp).toLocaleTimeString()}</span>
            {' '}
            <span className={levelColor(log.level)}>[{log.level.toUpperCase()}]</span>
            {' '}
            <span className="opacity-60">[{log.module}]</span>
            {' '}
            {log.message}
          </div>
        ))}
        <div ref={logsEndRef} />
      </div>
    </div>
  )
}

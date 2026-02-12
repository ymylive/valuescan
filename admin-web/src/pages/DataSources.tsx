import { useState, useEffect } from 'react'
import { api } from '../services/api'
import type { NewsItem, EconEvent } from '../types/api'
import { useTheme } from '../hooks/useTheme'

export const DataSources = () => {
  const { theme } = useTheme()
  const [news, setNews] = useState<NewsItem[]>([])
  const [econ, setEcon] = useState<EconEvent[]>([])
  const [loading, setLoading] = useState(true)

  const isDark = theme === 'day'
  const border = isDark ? 'border-white/20' : 'border-black/20'

  useEffect(() => {
    Promise.all([
      api.fundamentals.newsLatest(50),
      api.fundamentals.econUpcoming()
    ]).then(([newsData, econData]) => {
      setNews(newsData)
      setEcon(econData)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) return <div>Loading...</div>

  const importanceColor = (imp: string) => {
    if (imp === 'high') return 'text-red-500'
    if (imp === 'medium') return isDark ? 'text-yellow-400' : 'text-yellow-600'
    return isDark ? 'text-gray-400' : 'text-gray-600'
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl mb-4">Economic Calendar</h2>
        <div className="space-y-2">
          {econ.slice(0, 10).map((event, i) => (
            <div key={i} className={`border ${border} p-4`}>
              <div className="flex justify-between items-start">
                <div>
                  <div className="font-bold">{event.name}</div>
                  <div className="text-sm opacity-60">{event.country} • {new Date(event.time).toLocaleString()}</div>
                </div>
                <div className={`text-sm ${importanceColor(event.importance)}`}>
                  {event.importance.toUpperCase()}
                </div>
              </div>
              <div className="mt-2 text-sm font-mono">
                Prev: {event.previous} | Forecast: {event.forecast} | Actual: {event.actual || '-'}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h2 className="text-2xl mb-4">Latest News (50)</h2>
        <div className="space-y-2">
          {news.map((item, i) => (
            <div key={i} className={`border ${border} p-4`}>
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="font-bold">{item.title}</div>
                  <div className="text-sm opacity-60 mt-1">{item.content}</div>
                  <div className="text-xs opacity-40 mt-2">
                    {new Date(item.time).toLocaleString()} • {item.source}
                  </div>
                </div>
                <div className={`text-sm ml-4 ${importanceColor(item.importance)}`}>
                  {item.importance.toUpperCase()}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

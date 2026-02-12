import type { HealthResponse, LogEntry, NewsItem, EconEvent, ConfigHistory } from '../types/api'

const API_BASE = '/api'

const handleResponse = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    const error = await response.text()
    throw new Error(error || `HTTP ${response.status}`)
  }
  return response.json()
}

export const api = {
  health: () => fetch(`${API_BASE}/health`).then(handleResponse<HealthResponse>),

  control: {
    startScheduler: () => fetch(`${API_BASE}/control/scheduler/start`, { method: 'POST' }).then(handleResponse),
    stopScheduler: () => fetch(`${API_BASE}/control/scheduler/stop`, { method: 'POST' }).then(handleResponse),
    triggerAnomaly: () => fetch(`${API_BASE}/control/trigger/anomaly`, { method: 'POST' }).then(handleResponse),
    triggerMacro: () => fetch(`${API_BASE}/control/trigger/macro`, { method: 'POST' }).then(handleResponse),
    triggerAiBrief: () => fetch(`${API_BASE}/control/trigger/ai_brief`, { method: 'POST' }).then(handleResponse),
    triggerNews: () => fetch(`${API_BASE}/control/trigger/news`, { method: 'POST' }).then(handleResponse),
    triggerEcon: () => fetch(`${API_BASE}/control/trigger/econ`, { method: 'POST' }).then(handleResponse)
  },

  config: {
    get: () => fetch(`${API_BASE}/config`).then(handleResponse<Record<string, any>>),
    update: (config: Record<string, any>) =>
      fetch(`${API_BASE}/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      }).then(handleResponse),
    history: () => fetch(`${API_BASE}/config/history`).then(handleResponse<ConfigHistory[]>)
  },

  logs: {
    get: (params?: { level?: string; module?: string; since?: string; limit?: number }) => {
      const query = new URLSearchParams(params as any).toString()
      return fetch(`${API_BASE}/logs?${query}`).then(handleResponse<LogEntry[]>)
    },
    stream: () => new EventSource(`${API_BASE}/logs/stream`)
  },

  fundamentals: {
    newsLatest: (limit = 50) =>
      fetch(`${API_BASE}/fundamentals/news/latest?limit=${limit}`).then(handleResponse<NewsItem[]>),
    econUpcoming: () =>
      fetch(`${API_BASE}/fundamentals/econ/upcoming`).then(handleResponse<EconEvent[]>),
    econHistory: () =>
      fetch(`${API_BASE}/fundamentals/econ/history`).then(handleResponse<EconEvent[]>)
  }
}

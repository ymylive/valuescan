export interface HealthResponse {
  version: string
  uptime_seconds: number
  tasks: {
    [key: string]: {
      status: 'running' | 'idle' | 'error'
      last_run: string
      next_run: string
    }
  }
  queue_backlog: number
}

export interface LogEntry {
  timestamp: string
  level: 'info' | 'warning' | 'error'
  module: string
  message: string
}

export interface NewsItem {
  time: string
  title: string
  content: string
  tags: string[]
  importance: 'high' | 'medium' | 'low'
  source: string
}

export interface EconEvent {
  name: string
  country: string
  importance: 'high' | 'medium' | 'low'
  time: string
  previous: number
  forecast: number
  actual: number
  description: string
}

export interface ConfigHistory {
  timestamp: string
  changes: Record<string, any>
  user: string
}

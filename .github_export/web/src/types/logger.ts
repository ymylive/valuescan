/**
 * 日志级别
 */
export enum LogLevel {
  DEBUG = 'DEBUG',
  INFO = 'INFO',
  WARN = 'WARN',
  ERROR = 'ERROR',
}

/**
 * 日志条目
 */
export interface LogEntry {
  id: string;
  timestamp: number;
  level: LogLevel;
  component: string;
  message: string;
  data?: any;
  error?: Error;
}

/**
 * 日志配置
 */
export interface LoggerConfig {
  enabled: boolean;
  level: LogLevel;
  maxEntries: number;
  persistToLocalStorage: boolean;
  sendToBackend: boolean;
  consoleOutput: boolean;
}

/**
 * 日志过滤器
 */
export interface LogFilter {
  level?: LogLevel;
  component?: string;
  startTime?: number;
  endTime?: number;
  searchText?: string;
}

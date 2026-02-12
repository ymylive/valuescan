import { LogLevel, LogEntry, LoggerConfig, LogFilter } from '../types/logger';
import api from './api';

class LoggerService {
  private readonly DEFAULT_CONFIG: LoggerConfig = {
    enabled: true,
    level: LogLevel.INFO,
    maxEntries: 2000,
    persistToLocalStorage: true,
    sendToBackend: false,
    consoleOutput: true,
  };

  private config: LoggerConfig = { ...this.DEFAULT_CONFIG };
  private logs: LogEntry[] = [];
  private readonly STORAGE_KEY = 'nofx_logs';
  private readonly CONFIG_STORAGE_KEY = 'nofx_log_config';

  private readonly LEVEL_PRIORITY = {
    [LogLevel.DEBUG]: 0,
    [LogLevel.INFO]: 1,
    [LogLevel.WARN]: 2,
    [LogLevel.ERROR]: 3,
  };

  constructor() {
    this.loadConfigFromLocalStorage();
    this.loadFromLocalStorage();
  }

  setConfig(config: Partial<LoggerConfig>): void {
    this.config = this.normalizeConfig({ ...this.config, ...config });
    this.saveConfigToLocalStorage();
  }

  resetConfig(): LoggerConfig {
    this.config = { ...this.DEFAULT_CONFIG };
    this.saveConfigToLocalStorage();
    return this.getConfig();
  }

  getConfig(): LoggerConfig {
    return { ...this.config };
  }

  debug(component: string, message: string, data?: unknown): void {
    this.log(LogLevel.DEBUG, component, message, data);
  }

  info(component: string, message: string, data?: unknown): void {
    this.log(LogLevel.INFO, component, message, data);
  }

  warn(component: string, message: string, data?: unknown): void {
    this.log(LogLevel.WARN, component, message, data);
  }

  error(component: string, message: string, error?: Error, data?: unknown): void {
    this.log(LogLevel.ERROR, component, message, data, error);
  }

  private log(level: LogLevel, component: string, message: string, data?: unknown, error?: Error): void {
    if (!this.config.enabled) {
      return;
    }

    if (this.LEVEL_PRIORITY[level] < this.LEVEL_PRIORITY[this.config.level]) {
      return;
    }

    const entry: LogEntry = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`,
      timestamp: Date.now(),
      level,
      component,
      message,
      data,
      error,
    };

    this.logs.push(entry);

    if (this.logs.length > this.config.maxEntries) {
      this.logs = this.logs.slice(-this.config.maxEntries);
    }

    if (this.config.consoleOutput) {
      this.logToConsole(entry);
    }

    if (this.config.persistToLocalStorage) {
      this.saveToLocalStorage();
    }

    if (this.config.sendToBackend && level === LogLevel.ERROR) {
      void this.sendToBackend(entry);
    }
  }

  private logToConsole(entry: LogEntry): void {
    const timestamp = new Date(entry.timestamp).toISOString();
    const prefix = `[${timestamp}] [${entry.level}] [${entry.component}]`;

    switch (entry.level) {
      case LogLevel.DEBUG:
        console.debug(prefix, entry.message, entry.data);
        break;
      case LogLevel.INFO:
        console.info(prefix, entry.message, entry.data);
        break;
      case LogLevel.WARN:
        console.warn(prefix, entry.message, entry.data);
        break;
      case LogLevel.ERROR:
        console.error(prefix, entry.message, entry.error, entry.data);
        break;
      default:
        console.info(prefix, entry.message, entry.data);
    }
  }

  private saveToLocalStorage(): void {
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.logs));
    } catch (error) {
      console.error('Failed to save logs to localStorage:', error);
    }
  }

  private loadFromLocalStorage(): void {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      if (stored) {
        this.logs = JSON.parse(stored) as LogEntry[];
      }
    } catch (error) {
      console.error('Failed to load logs from localStorage:', error);
    }
  }

  private normalizeConfig(config: LoggerConfig): LoggerConfig {
    const maxEntries = Number.isFinite(config.maxEntries)
      ? Math.max(100, Math.floor(config.maxEntries))
      : this.DEFAULT_CONFIG.maxEntries;

    return {
      ...config,
      maxEntries,
      level: this.LEVEL_PRIORITY[config.level] != null ? config.level : this.DEFAULT_CONFIG.level,
    };
  }

  private loadConfigFromLocalStorage(): void {
    try {
      const stored = localStorage.getItem(this.CONFIG_STORAGE_KEY);
      if (!stored) {
        return;
      }
      const parsed = JSON.parse(stored) as Partial<LoggerConfig>;
      this.config = this.normalizeConfig({
        ...this.DEFAULT_CONFIG,
        ...parsed,
      });
    } catch (error) {
      console.error('Failed to load logger config from localStorage:', error);
    }
  }

  private saveConfigToLocalStorage(): void {
    try {
      localStorage.setItem(this.CONFIG_STORAGE_KEY, JSON.stringify(this.config));
    } catch (error) {
      console.error('Failed to save logger config to localStorage:', error);
    }
  }

  private async sendToBackend(entry: LogEntry): Promise<void> {
    try {
      await api.post('/logs', {
        timestamp: entry.timestamp,
        level: entry.level,
        component: entry.component,
        message: entry.message,
        data: entry.data,
        error: entry.error
          ? {
              name: entry.error.name,
              message: entry.error.message,
              stack: entry.error.stack,
            }
          : undefined,
      });
    } catch (error) {
      console.error('Failed to send log to backend:', error);
    }
  }

  getLogs(filter?: LogFilter): LogEntry[] {
    let filtered = [...this.logs];

    if (filter) {
      const { level, component, startTime, endTime, searchText } = filter;

      if (level) {
        filtered = filtered.filter((log) => log.level === level);
      }

      if (component) {
        filtered = filtered.filter((log) => log.component.includes(component));
      }

      if (startTime != null) {
        filtered = filtered.filter((log) => log.timestamp >= startTime);
      }

      if (endTime != null) {
        filtered = filtered.filter((log) => log.timestamp <= endTime);
      }

      if (searchText) {
        const search = searchText.toLowerCase();
        filtered = filtered.filter(
          (log) => log.message.toLowerCase().includes(search) || log.component.toLowerCase().includes(search)
        );
      }
    }

    return filtered.sort((a, b) => b.timestamp - a.timestamp);
  }

  clearLogs(): void {
    this.logs = [];
    this.saveToLocalStorage();
  }

  exportLogs(): string {
    return JSON.stringify(this.logs, null, 2);
  }

  getStats(): { total: number; byLevel: Record<LogLevel, number>; byComponent: Record<string, number> } {
    const byLevel: Record<LogLevel, number> = {
      [LogLevel.DEBUG]: 0,
      [LogLevel.INFO]: 0,
      [LogLevel.WARN]: 0,
      [LogLevel.ERROR]: 0,
    };
    const byComponent: Record<string, number> = {};

    this.logs.forEach((log) => {
      byLevel[log.level] += 1;
      byComponent[log.component] = (byComponent[log.component] || 0) + 1;
    });

    return {
      total: this.logs.length,
      byLevel,
      byComponent,
    };
  }
}

export const logger = new LoggerService();

import { LogLevel, LogEntry, LoggerConfig, LogFilter } from '../types/logger';
import api from './api';

/**
 * 前端日志服务
 */
class LoggerService {
  private config: LoggerConfig = {
    enabled: true,
    level: LogLevel.INFO,
    maxEntries: 2000,
    persistToLocalStorage: true,
    sendToBackend: false,
    consoleOutput: true,
  };

  private logs: LogEntry[] = [];
  private readonly STORAGE_KEY = 'valuescan_logs';
  private readonly LEVEL_PRIORITY = {
    [LogLevel.DEBUG]: 0,
    [LogLevel.INFO]: 1,
    [LogLevel.WARN]: 2,
    [LogLevel.ERROR]: 3,
  };

  constructor() {
    this.loadFromLocalStorage();
  }

  /**
   * 设置日志配置
   */
  setConfig(config: Partial<LoggerConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * 获取日志配置
   */
  getConfig(): LoggerConfig {
    return { ...this.config };
  }

  /**
   * 记录 DEBUG 日志
   */
  debug(component: string, message: string, data?: any): void {
    this.log(LogLevel.DEBUG, component, message, data);
  }

  /**
   * 记录 INFO 日志
   */
  info(component: string, message: string, data?: any): void {
    this.log(LogLevel.INFO, component, message, data);
  }

  /**
   * 记录 WARN 日志
   */
  warn(component: string, message: string, data?: any): void {
    this.log(LogLevel.WARN, component, message, data);
  }

  /**
   * 记录 ERROR 日志
   */
  error(component: string, message: string, error?: Error, data?: any): void {
    this.log(LogLevel.ERROR, component, message, data, error);
  }

  /**
   * 核心日志记录方法
   */
  private log(level: LogLevel, component: string, message: string, data?: any, error?: Error): void {
    if (!this.config.enabled) return;

    // 检查日志级别
    if (this.LEVEL_PRIORITY[level] < this.LEVEL_PRIORITY[this.config.level]) {
      return;
    }

    const entry: LogEntry = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
      level,
      component,
      message,
      data,
      error,
    };

    // 添加到日志数组
    this.logs.push(entry);

    // 限制日志数量
    if (this.logs.length > this.config.maxEntries) {
      this.logs = this.logs.slice(-this.config.maxEntries);
    }

    // 输出到控制台
    if (this.config.consoleOutput) {
      this.logToConsole(entry);
    }

    // 持久化到本地存储
    if (this.config.persistToLocalStorage) {
      this.saveToLocalStorage();
    }

    // 发送到后端
    if (this.config.sendToBackend && level === LogLevel.ERROR) {
      this.sendToBackend(entry);
    }
  }

  /**
   * 输出到控制台
   */
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
    }
  }

  /**
   * 保存到本地存储
   */
  private saveToLocalStorage(): void {
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.logs));
    } catch (error) {
      console.error('Failed to save logs to localStorage:', error);
    }
  }

  /**
   * 从本地存储加载
   */
  private loadFromLocalStorage(): void {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      if (stored) {
        this.logs = JSON.parse(stored);
      }
    } catch (error) {
      console.error('Failed to load logs from localStorage:', error);
    }
  }

  /**
   * 发送到后端
   */
  private async sendToBackend(entry: LogEntry): Promise<void> {
    try {
      await api.post('/logs', {
        timestamp: entry.timestamp,
        level: entry.level,
        component: entry.component,
        message: entry.message,
        data: entry.data,
        error: entry.error ? {
          name: entry.error.name,
          message: entry.error.message,
          stack: entry.error.stack,
        } : undefined,
      });
    } catch (error) {
      console.error('Failed to send log to backend:', error);
    }
  }

  /**
   * 获取所有日志
   */
  getLogs(filter?: LogFilter): LogEntry[] {
    let filtered = [...this.logs];

    if (filter) {
      if (filter.level) {
        filtered = filtered.filter(log => log.level === filter.level);
      }
      if (filter.component) {
        filtered = filtered.filter(log => log.component.includes(filter.component!));
      }
      if (filter.startTime) {
        filtered = filtered.filter(log => log.timestamp >= filter.startTime!);
      }
      if (filter.endTime) {
        filtered = filtered.filter(log => log.timestamp <= filter.endTime!);
      }
      if (filter.searchText) {
        const search = filter.searchText.toLowerCase();
        filtered = filtered.filter(log =>
          log.message.toLowerCase().includes(search) ||
          log.component.toLowerCase().includes(search)
        );
      }
    }

    return filtered.sort((a, b) => b.timestamp - a.timestamp);
  }

  /**
   * 清除所有日志
   */
  clearLogs(): void {
    this.logs = [];
    this.saveToLocalStorage();
  }

  /**
   * 导出日志为 JSON
   */
  exportLogs(): string {
    return JSON.stringify(this.logs, null, 2);
  }

  /**
   * 获取日志统计
   */
  getStats(): { total: number; byLevel: Record<LogLevel, number>; byComponent: Record<string, number> } {
    const byLevel: Record<LogLevel, number> = {
      [LogLevel.DEBUG]: 0,
      [LogLevel.INFO]: 0,
      [LogLevel.WARN]: 0,
      [LogLevel.ERROR]: 0,
    };

    const byComponent: Record<string, number> = {};

    this.logs.forEach(log => {
      byLevel[log.level]++;
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

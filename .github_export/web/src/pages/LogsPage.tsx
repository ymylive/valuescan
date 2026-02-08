import React, { useState, useEffect } from 'react';
import { FileText, Download, Trash2, RefreshCw, Filter, Search } from 'lucide-react';
import { GlassCard } from '../components/Common/GlassCard';
import { Button } from '../components/Common/Button';
import { Input } from '../components/Common/Input';
import { logger } from '../services/loggerService';
import { LogLevel, LogEntry, LogFilter } from '../types/logger';
import api from '../services/api';

type LogSource = 'frontend' | 'backend';
type BackendService = 'signal' | 'trader' | 'api';

const LogsPage: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState<LogFilter>({});
  const [searchText, setSearchText] = useState('');
  const [selectedLevel, setSelectedLevel] = useState<LogLevel | ''>('');
  const [stats, setStats] = useState<any>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [logSource, setLogSource] = useState<LogSource>('frontend');
  const [backendService, setBackendService] = useState<BackendService>('signal');
  const [backendLogs, setBackendLogs] = useState<LogEntry[]>([]);

  useEffect(() => {
    loadLogs();
    loadStats();

    if (autoRefresh) {
      const interval = setInterval(() => {
        loadLogs();
        loadStats();
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [filter, autoRefresh, logSource, backendService]);

  const loadBackendLogs = async () => {
    try {
      const response = await api.get(`/logs/${backendService}?lines=2000`) as any;
      if (response.logs && Array.isArray(response.logs)) {
        // 转换后端日志格式为前端格式
        const convertedLogs: LogEntry[] = response.logs.map((log: any) => ({
          id: `${log.timestamp}-${Math.random()}`,
          timestamp: log.timestamp,
          level: convertPriorityToLevel(log.level),
          component: log.component,
          message: log.message,
          data: log.data
        }));
        setBackendLogs(convertedLogs);
      }
    } catch (error) {
      console.error('Failed to load backend logs:', error);
      setBackendLogs([]);
    }
  };

  const convertPriorityToLevel = (priority: string): LogLevel => {
    // syslog priority to LogLevel mapping
    const p = parseInt(priority);
    if (p <= 3) return LogLevel.ERROR;  // 0-3: emerg, alert, crit, err
    if (p === 4) return LogLevel.WARN;   // 4: warning
    if (p === 6) return LogLevel.INFO;   // 6: info
    return LogLevel.DEBUG;               // 7: debug
  };

  const loadLogs = () => {
    if (logSource === 'frontend') {
      const filtered = logger.getLogs(filter);
      setLogs(filtered);
    } else {
      loadBackendLogs();
    }
  };

  const loadStats = () => {
    if (logSource === 'frontend') {
      const statistics = logger.getStats();
      setStats(statistics);
    } else {
      // 计算后端日志统计
      const byLevel = {
        [LogLevel.DEBUG]: 0,
        [LogLevel.INFO]: 0,
        [LogLevel.WARN]: 0,
        [LogLevel.ERROR]: 0,
      };
      backendLogs.forEach(log => {
        byLevel[log.level]++;
      });
      setStats({
        total: backendLogs.length,
        byLevel,
        byComponent: {}
      });
    }
  };

  const handleSearch = () => {
    setFilter({
      ...filter,
      searchText: searchText || undefined,
      level: selectedLevel || undefined,
    });
  };

  const handleClearLogs = () => {
    if (confirm('确定要清除所有日志吗？')) {
      logger.clearLogs();
      loadLogs();
      loadStats();
    }
  };

  const handleExportLogs = () => {
    const json = logger.exportLogs();
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `valuescan-logs-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getLevelColor = (level: LogLevel) => {
    switch (level) {
      case LogLevel.DEBUG:
        return 'text-gray-500';
      case LogLevel.INFO:
        return 'text-blue-500';
      case LogLevel.WARN:
        return 'text-yellow-500';
      case LogLevel.ERROR:
        return 'text-red-500';
      default:
        return 'text-gray-500';
    }
  };

  const getLevelBgColor = (level: LogLevel) => {
    switch (level) {
      case LogLevel.DEBUG:
        return 'bg-gray-100 dark:bg-gray-800';
      case LogLevel.INFO:
        return 'bg-blue-100 dark:bg-blue-900';
      case LogLevel.WARN:
        return 'bg-yellow-100 dark:bg-yellow-900';
      case LogLevel.ERROR:
        return 'bg-red-100 dark:bg-red-900';
      default:
        return 'bg-gray-100 dark:bg-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FileText className="text-blue-500" size={32} />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">系统日志</h2>

          {/* Log Source Selector */}
          <div className="flex gap-2 ml-4">
            <button
              onClick={() => setLogSource('frontend')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                logSource === 'frontend'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
              }`}
            >
              前端日志
            </button>
            <button
              onClick={() => setLogSource('backend')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                logSource === 'backend'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
              }`}
            >
              后端日志
            </button>
          </div>

          {/* Backend Service Selector */}
          {logSource === 'backend' && (
            <select
              value={backendService}
              onChange={(e) => setBackendService(e.target.value as BackendService)}
              className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg"
            >
              <option value="signal">信号监控</option>
              <option value="trader">交易服务</option>
              <option value="api">API服务</option>
            </select>
          )}
        </div>

        <div className="flex gap-3">
          <Button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-2 ${autoRefresh ? 'bg-green-500' : 'bg-gray-500'}`}
          >
            <RefreshCw className={autoRefresh ? 'animate-spin' : ''} size={18} />
            {autoRefresh ? '自动刷新' : '手动刷新'}
          </Button>
          <Button
            onClick={handleExportLogs}
            className="flex items-center gap-2 bg-blue-500 hover:bg-blue-600"
          >
            <Download size={18} />
            导出日志
          </Button>
          <Button
            onClick={handleClearLogs}
            className="flex items-center gap-2 bg-red-500 hover:bg-red-600"
          >
            <Trash2 size={18} />
            清除日志
          </Button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <GlassCard className="p-6">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div>
              <div className="text-sm text-gray-500 dark:text-gray-400">总计</div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">{stats.total}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500 dark:text-gray-400">DEBUG</div>
              <div className="text-2xl font-bold text-gray-500">{stats.byLevel.DEBUG}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500 dark:text-gray-400">INFO</div>
              <div className="text-2xl font-bold text-blue-500">{stats.byLevel.INFO}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500 dark:text-gray-400">WARN</div>
              <div className="text-2xl font-bold text-yellow-500">{stats.byLevel.WARN}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500 dark:text-gray-400">ERROR</div>
              <div className="text-2xl font-bold text-red-500">{stats.byLevel.ERROR}</div>
            </div>
          </div>
        </GlassCard>
      )}

      {/* Filters */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-4">
          <Filter className="text-gray-500" size={20} />
          <Input
            type="text"
            placeholder="搜索日志..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="flex-1"
          />
          <select
            value={selectedLevel}
            onChange={(e) => setSelectedLevel(e.target.value as LogLevel | '')}
            className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg"
          >
            <option value="">所有级别</option>
            <option value={LogLevel.DEBUG}>DEBUG</option>
            <option value={LogLevel.INFO}>INFO</option>
            <option value={LogLevel.WARN}>WARN</option>
            <option value={LogLevel.ERROR}>ERROR</option>
          </select>
          <Button
            onClick={handleSearch}
            className="flex items-center gap-2 bg-blue-500 hover:bg-blue-600"
          >
            <Search size={18} />
            搜索
          </Button>
        </div>
      </GlassCard>

      {/* Logs List */}
      <GlassCard className="p-6">
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
          日志列表 ({logSource === 'frontend' ? logs.length : backendLogs.length})
        </h3>

        {(logSource === 'frontend' ? logs : backendLogs).length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            暂无日志
          </div>
        ) : (
          <div className="space-y-2 max-h-[600px] overflow-y-auto">
            {(logSource === 'frontend' ? logs : backendLogs).map((log) => (
              <div
                key={log.id}
                className={`p-4 rounded-lg border ${getLevelBgColor(log.level)} border-gray-200 dark:border-gray-700`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className={`font-bold ${getLevelColor(log.level)}`}>
                        [{log.level}]
                      </span>
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        {log.component}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-500">
                        {new Date(log.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <div className="text-gray-900 dark:text-white mb-2">
                      {log.message}
                    </div>
                    {log.data && (
                      <details className="text-sm text-gray-600 dark:text-gray-400">
                        <summary className="cursor-pointer">查看数据</summary>
                        <pre className="mt-2 p-2 bg-gray-100 dark:bg-gray-800 rounded overflow-x-auto">
                          {JSON.stringify(log.data, null, 2)}
                        </pre>
                      </details>
                    )}
                    {log.error && (
                      <details className="text-sm text-red-600 dark:text-red-400 mt-2">
                        <summary className="cursor-pointer">查看错误</summary>
                        <pre className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 rounded overflow-x-auto">
                          {log.error.stack || log.error.message}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </GlassCard>
    </div>
  );
};

export default LogsPage;

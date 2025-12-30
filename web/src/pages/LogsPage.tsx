import React, { useState, useEffect } from 'react';
import { FileText, Download, Trash2, RefreshCw, Filter, Search } from 'lucide-react';
import { GlassCard } from '../components/Common/GlassCard';
import { Button } from '../components/Common/Button';
import { Input } from '../components/Common/Input';
import { logger } from '../services/loggerService';
import { LogLevel, LogEntry, LogFilter } from '../types/logger';

const LogsPage: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState<LogFilter>({});
  const [searchText, setSearchText] = useState('');
  const [selectedLevel, setSelectedLevel] = useState<LogLevel | ''>('');
  const [stats, setStats] = useState<any>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

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
  }, [filter, autoRefresh]);

  const loadLogs = () => {
    const filtered = logger.getLogs(filter);
    setLogs(filtered);
  };

  const loadStats = () => {
    const statistics = logger.getStats();
    setStats(statistics);
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
          日志列表 ({logs.length})
        </h3>

        {logs.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            暂无日志
          </div>
        ) : (
          <div className="space-y-2 max-h-[600px] overflow-y-auto">
            {logs.map((log) => (
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

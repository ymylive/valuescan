import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { FileText, Download, Trash2, RefreshCw, Filter, Search, SlidersHorizontal, RotateCcw } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { PageContainer } from '../../components/layout';
import { Button, Input } from '../../components/ui';
import { GlassCard } from '../../components/shared';
import { logger } from '../../services/loggerService';
import { LogLevel, LogEntry, LogFilter, LoggerConfig } from '../../types/logger';
import api from '../../services/api';

type LogSource = 'frontend' | 'backend';
type BackendService = 'signal' | 'api' | 'token-refresher';

type BackendLogPayload = {
  timestamp?: number | string;
  level?: number | string;
  component?: string;
  message?: string;
  data?: unknown;
};

type BackendLogsResponse = {
  logs?: BackendLogPayload[];
  data?: {
    logs?: BackendLogPayload[];
  };
};

const BACKEND_LOG_LINES = 500;
const FRONTEND_POLL_INTERVAL_MS = 3000;
const BACKEND_POLL_INTERVAL_MS = 5000;

const LOG_LEVEL_COLORS: Record<LogLevel, string> = {
  [LogLevel.DEBUG]: 'text-gray-500',
  [LogLevel.INFO]: 'text-blue-500',
  [LogLevel.WARN]: 'text-yellow-500',
  [LogLevel.ERROR]: 'text-red-500',
};

const isObject = (value: unknown): value is Record<string, unknown> => {
  return typeof value === 'object' && value !== null;
};

const getBackendLogsFromResponse = (response: unknown): BackendLogPayload[] => {
  if (!isObject(response)) {
    return [];
  }

  const payload = response as BackendLogsResponse;
  if (Array.isArray(payload.logs)) {
    return payload.logs;
  }
  if (isObject(payload.data) && Array.isArray(payload.data.logs)) {
    return payload.data.logs;
  }
  return [];
};

const toTimestamp = (value: number | string | undefined): number => {
  if (typeof value === 'number') {
    return value;
  }
  if (typeof value === 'string') {
    const asNumber = Number(value);
    return Number.isNaN(asNumber) ? Date.now() : asNumber;
  }
  return Date.now();
};

export const LogsPage = () => {
  const { t } = useTranslation();
  const [frontendLogs, setFrontendLogs] = useState<LogEntry[]>([]);
  const [backendLogs, setBackendLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState<LogFilter>({});
  const [searchText, setSearchText] = useState('');
  const [selectedLevel, setSelectedLevel] = useState<LogLevel | ''>('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [logSource, setLogSource] = useState<LogSource>('frontend');
  const [backendService, setBackendService] = useState<BackendService>('signal');
  const [loggerConfig, setLoggerConfig] = useState<LoggerConfig>(() => logger.getConfig());
  const backendRequestInFlightRef = useRef(false);

  const convertPriority = (priority: number | string | undefined): LogLevel => {
    if (typeof priority === 'string') {
      const normalized = priority.trim().toUpperCase();
      if (normalized === 'ERROR' || normalized === 'CRITICAL') return LogLevel.ERROR;
      if (normalized === 'WARN' || normalized === 'WARNING') return LogLevel.WARN;
      if (normalized === 'INFO') return LogLevel.INFO;
      if (normalized === 'DEBUG') return LogLevel.DEBUG;
    }
    const n = Number(priority);
    if (Number.isNaN(n)) return LogLevel.DEBUG;
    if (n >= 50 || n <= 3) return LogLevel.ERROR;
    if (n >= 30 || n === 4) return LogLevel.WARN;
    if (n >= 20 || n === 6) return LogLevel.INFO;
    return LogLevel.DEBUG;
  };

  const applyFilter = useCallback(
    (entries: LogEntry[]) => {
      let filtered = [...entries];

      if (filter.level) {
        filtered = filtered.filter((log) => log.level === filter.level);
      }

      if (filter.searchText) {
        const keyword = filter.searchText.toLowerCase();
        filtered = filtered.filter(
          (log) => log.message.toLowerCase().includes(keyword) || log.component.toLowerCase().includes(keyword)
        );
      }

      return filtered.sort((a, b) => b.timestamp - a.timestamp);
    },
    [filter]
  );

  const loadBackendLogs = useCallback(async () => {
    if (backendRequestInFlightRef.current) {
      return;
    }

    backendRequestInFlightRef.current = true;
    try {
      const response = await api.get(`/logs/${backendService}?lines=${BACKEND_LOG_LINES}`);
      const logs = getBackendLogsFromResponse(response);
      const normalizedLogs = logs.map((log, index) => {
        const timestamp = toTimestamp(log.timestamp);
        return {
          id: `${backendService}-${timestamp}-${index}`,
          timestamp,
          level: convertPriority(log.level),
          component: log.component || backendService,
          message: log.message || '',
          data: log.data,
        } satisfies LogEntry;
      });
      setBackendLogs(applyFilter(normalizedLogs));
    } catch {
      setBackendLogs([]);
    } finally {
      backendRequestInFlightRef.current = false;
    }
  }, [applyFilter, backendService]);

  const loadFrontendLogs = useCallback(() => {
    setFrontendLogs(logger.getLogs(filter));
  }, [filter]);

  const loadLogs = useCallback(() => {
    if (logSource === 'frontend') {
      loadFrontendLogs();
    } else {
      void loadBackendLogs();
    }
  }, [loadBackendLogs, loadFrontendLogs, logSource]);

  const applyLoggerConfig = useCallback(
    (partial: Partial<LoggerConfig>) => {
      logger.setConfig(partial);
      const next = logger.getConfig();
      setLoggerConfig(next);
      if (logSource === 'frontend') {
        setFrontendLogs(logger.getLogs(filter));
      }
    },
    [filter, logSource]
  );

  const resetLoggerConfig = useCallback(() => {
    const next = logger.resetConfig();
    setLoggerConfig(next);
    setFrontendLogs(logger.getLogs(filter));
  }, [filter]);

  const pollIntervalMs = useMemo(
    () => (logSource === 'backend' ? BACKEND_POLL_INTERVAL_MS : FRONTEND_POLL_INTERVAL_MS),
    [logSource]
  );

  useEffect(() => {
    loadLogs();
    if (!autoRefresh) {
      return;
    }

    const interval = setInterval(() => {
      if (logSource === 'backend' && document.visibilityState === 'hidden') {
        return;
      }
      loadLogs();
    }, pollIntervalMs);

    return () => clearInterval(interval);
  }, [autoRefresh, loadLogs, logSource, pollIntervalMs]);

  const handleSearch = () => {
    setFilter({ ...filter, searchText: searchText || undefined, level: selectedLevel || undefined });
  };

  const handleClear = () => {
    if (window.confirm(t('logs.clearConfirm'))) {
      logger.clearLogs();
      loadLogs();
    }
  };

  const handleExport = () => {
    const logsToExport = logSource === 'frontend' ? frontendLogs : backendLogs;
    const json = JSON.stringify(logsToExport, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `valuescan-logs-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const displayLogs = useMemo(() => {
    return logSource === 'frontend' ? frontendLogs : backendLogs;
  }, [backendLogs, frontendLogs, logSource]);

  const frontendStats = useMemo(() => {
    const byLevel = {
      [LogLevel.DEBUG]: 0,
      [LogLevel.INFO]: 0,
      [LogLevel.WARN]: 0,
      [LogLevel.ERROR]: 0,
    };
    frontendLogs.forEach((log) => {
      byLevel[log.level] += 1;
    });
    return {
      total: frontendLogs.length,
      byLevel,
    };
  }, [frontendLogs]);

  return (
    <PageContainer>
      <div className="space-y-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap items-center gap-3">
            <FileText className="text-blue-500" size={32} />
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{t('logs.title')}</h2>
            <div className="ml-0 flex flex-wrap gap-2 md:ml-4">
              {(['frontend', 'backend'] as const).map((source) => (
                <button
                  key={source}
                  onClick={() => setLogSource(source)}
                  className={`rounded-lg px-4 py-2 transition-colors ${
                    logSource === source
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                  }`}
                >
                  {source === 'frontend' ? t('logs.sourceFrontend') : t('logs.sourceBackend')}
                </button>
              ))}
            </div>
            {logSource === 'backend' && (
              <select
                value={backendService}
                onChange={(event) => setBackendService(event.target.value as BackendService)}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2 dark:border-gray-600 dark:bg-gray-800"
              >
                <option value="signal">{t('logs.backendServiceSignal')}</option>
                <option value="api">{t('logs.backendServiceApi')}</option>
                <option value="token-refresher">{t('logs.backendServiceTokenRefresher')}</option>
              </select>
            )}
          </div>

          <div className="flex flex-wrap gap-3">
            <Button onClick={() => setAutoRefresh(!autoRefresh)} variant={autoRefresh ? 'primary' : 'secondary'}>
              <RefreshCw className={`mr-2 h-4 w-4 ${autoRefresh ? 'animate-spin' : ''}`} />
              {autoRefresh ? t('logs.autoRefresh') : t('logs.manualRefresh')}
            </Button>
            <Button onClick={handleExport} variant="secondary">
              <Download className="mr-2 h-4 w-4" />
              {t('logs.export')}
            </Button>
            <Button onClick={handleClear} variant="danger" disabled={logSource !== 'frontend'}>
              <Trash2 className="mr-2 h-4 w-4" />
              {t('logs.clearFrontend')}
            </Button>
          </div>
        </div>

        <GlassCard className="p-6">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-lg bg-gray-100 p-3 dark:bg-gray-800">
              <div className="text-xs uppercase text-gray-500">{t('logs.statsFrontendTotal')}</div>
              <div className="text-lg font-semibold text-gray-900 dark:text-white">{frontendStats.total}</div>
            </div>
            <div className="rounded-lg bg-gray-100 p-3 dark:bg-gray-800">
              <div className="text-xs uppercase text-gray-500">{t('logs.statsErrors')}</div>
              <div className="text-lg font-semibold text-red-500">{frontendStats.byLevel.ERROR}</div>
            </div>
            <div className="rounded-lg bg-gray-100 p-3 dark:bg-gray-800">
              <div className="text-xs uppercase text-gray-500">{t('logs.statsWarnings')}</div>
              <div className="text-lg font-semibold text-yellow-500">{frontendStats.byLevel.WARN}</div>
            </div>
            <div className="rounded-lg bg-gray-100 p-3 dark:bg-gray-800">
              <div className="text-xs uppercase text-gray-500">{t('logs.statsInfos')}</div>
              <div className="text-lg font-semibold text-blue-500">{frontendStats.byLevel.INFO}</div>
            </div>
          </div>
        </GlassCard>

        <GlassCard className="p-6">
          <div className="mb-4 flex items-center gap-2">
            <SlidersHorizontal className="h-5 w-5 text-gray-500" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{t('logs.loggerSettingsTitle')}</h3>
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            <label className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 dark:border-gray-700">
              <input
                type="checkbox"
                checked={loggerConfig.enabled}
                onChange={(event) => applyLoggerConfig({ enabled: event.target.checked })}
              />
              <span className="text-sm">{t('logs.loggerEnabled')}</span>
            </label>
            <label className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 dark:border-gray-700">
              <input
                type="checkbox"
                checked={loggerConfig.consoleOutput}
                onChange={(event) => applyLoggerConfig({ consoleOutput: event.target.checked })}
              />
              <span className="text-sm">{t('logs.consoleOutput')}</span>
            </label>
            <label className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 dark:border-gray-700">
              <input
                type="checkbox"
                checked={loggerConfig.persistToLocalStorage}
                onChange={(event) => applyLoggerConfig({ persistToLocalStorage: event.target.checked })}
              />
              <span className="text-sm">{t('logs.persistLocal')}</span>
            </label>
            <label className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 dark:border-gray-700">
              <input
                type="checkbox"
                checked={loggerConfig.sendToBackend}
                onChange={(event) => applyLoggerConfig({ sendToBackend: event.target.checked })}
              />
              <span className="text-sm">{t('logs.sendErrorsToBackend')}</span>
            </label>
            <div className="rounded-lg border border-gray-200 px-3 py-2 dark:border-gray-700">
              <div className="mb-1 text-xs text-gray-500">{t('logs.logLevel')}</div>
              <select
                value={loggerConfig.level}
                onChange={(event) => applyLoggerConfig({ level: event.target.value as LogLevel })}
                className="w-full rounded border border-gray-300 bg-white px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-800"
              >
                {Object.values(LogLevel).map((level) => (
                  <option key={level} value={level}>
                    {level}
                  </option>
                ))}
              </select>
            </div>
            <div className="rounded-lg border border-gray-200 px-3 py-2 dark:border-gray-700">
              <div className="mb-1 text-xs text-gray-500">{t('logs.maxEntries')}</div>
              <Input
                type="number"
                min={100}
                step={100}
                value={loggerConfig.maxEntries}
                onChange={(event) => applyLoggerConfig({ maxEntries: Number(event.target.value) || 100 })}
              />
            </div>
          </div>
          <div className="mt-4">
            <Button variant="secondary" onClick={resetLoggerConfig}>
              <RotateCcw className="mr-2 h-4 w-4" />
              {t('logs.resetLogger')}
            </Button>
          </div>
        </GlassCard>

        <GlassCard className="p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center">
            <Filter className="text-gray-500" size={20} />
            <Input
              placeholder={t('logs.searchPlaceholder')}
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              className="flex-1"
            />
            <select
              value={selectedLevel}
              onChange={(event) => setSelectedLevel(event.target.value as LogLevel | '')}
              className="rounded-lg border border-gray-300 bg-white px-4 py-2 dark:border-gray-600 dark:bg-gray-800"
            >
              <option value="">{t('logs.allLevels')}</option>
              {Object.values(LogLevel).map((level) => (
                <option key={level} value={level}>
                  {level}
                </option>
              ))}
            </select>
            <Button onClick={handleSearch}>
              <Search className="mr-2 h-4 w-4" />
              {t('logs.search')}
            </Button>
          </div>
        </GlassCard>

        <GlassCard className="p-6">
          <h3 className="mb-4 text-lg font-bold text-gray-900 dark:text-white">
            {t('logs.entries')} ({displayLogs.length})
          </h3>
          {displayLogs.length === 0 ? (
            <div className="py-8 text-center text-gray-500">{t('logs.noLogs')}</div>
          ) : (
            <div className="max-h-[600px] space-y-2 overflow-y-auto">
              {displayLogs.map((log) => (
                <div
                  key={log.id}
                  className="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/50"
                >
                  <div className="mb-2 flex items-center gap-3">
                    <span className={`font-bold ${LOG_LEVEL_COLORS[log.level] ?? 'text-gray-500'}`}>[{log.level}]</span>
                    <span className="text-sm text-gray-600 dark:text-gray-400">{log.component}</span>
                    <span className="text-xs text-gray-500">{new Date(log.timestamp).toLocaleString()}</span>
                  </div>
                  <div className="text-gray-900 dark:text-white">{log.message}</div>
                  {log.data != null && (
                    <details className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                      <summary className="cursor-pointer">{t('logs.showPayload')}</summary>
                      <pre className="mt-2 overflow-x-auto rounded bg-gray-100 p-2 dark:bg-gray-800">
                        {JSON.stringify(log.data, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              ))}
            </div>
          )}
        </GlassCard>
      </div>
    </PageContainer>
  );
};

export default LogsPage;

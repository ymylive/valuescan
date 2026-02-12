import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { LogLevel } from '../types/logger';

describe('loggerService', () => {
  beforeEach(() => {
    vi.resetModules();
    localStorage.clear();
    sessionStorage.clear();
    vi.spyOn(console, 'debug').mockImplementation(() => {});
    vi.spyOn(console, 'info').mockImplementation(() => {});
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('filters logs by level and search text', async () => {
    const { logger } = await import('./loggerService');

    logger.clearLogs();
    logger.setConfig({
      level: LogLevel.DEBUG,
      consoleOutput: false,
      persistToLocalStorage: true,
    });

    logger.info('AuthService', 'login success');
    logger.warn('OrderService', 'order rejected');
    logger.error('RiskEngine', 'auth token missing');

    const warnLogs = logger.getLogs({ level: LogLevel.WARN });
    expect(warnLogs).toHaveLength(1);
    expect(warnLogs[0]).toMatchObject({
      level: LogLevel.WARN,
      message: 'order rejected',
    });

    const authSearchLogs = logger.getLogs({ searchText: 'auth' });
    expect(authSearchLogs).toHaveLength(2);
    expect(authSearchLogs.map((entry) => entry.component)).toEqual(
      expect.arrayContaining(['AuthService', 'RiskEngine'])
    );
  });

  it('clears and exports logs consistently', async () => {
    const { logger } = await import('./loggerService');

    logger.clearLogs();
    logger.setConfig({
      level: LogLevel.DEBUG,
      consoleOutput: false,
      persistToLocalStorage: true,
    });

    logger.debug('TestComponent', 'debug payload', { id: 1 });

    const exportedBeforeClear = JSON.parse(logger.exportLogs());
    expect(exportedBeforeClear).toHaveLength(1);
    expect(exportedBeforeClear[0]).toMatchObject({
      level: LogLevel.DEBUG,
      component: 'TestComponent',
      message: 'debug payload',
    });

    logger.clearLogs();

    expect(logger.getLogs()).toEqual([]);
    expect(logger.exportLogs()).toBe('[]');
    expect(JSON.parse(localStorage.getItem('nofx_logs') || 'null')).toEqual([]);
  });

  it('persists logger config and restores it on next initialization', async () => {
    const { logger } = await import('./loggerService');

    logger.setConfig({
      level: LogLevel.ERROR,
      maxEntries: 350,
      consoleOutput: false,
    });

    const persisted = JSON.parse(localStorage.getItem('nofx_log_config') || '{}');
    expect(persisted.level).toBe(LogLevel.ERROR);
    expect(persisted.maxEntries).toBe(350);
    expect(persisted.consoleOutput).toBe(false);

    vi.resetModules();
    const { logger: reloadedLogger } = await import('./loggerService');
    const reloaded = reloadedLogger.getConfig();
    expect(reloaded.level).toBe(LogLevel.ERROR);
    expect(reloaded.maxEntries).toBe(350);
    expect(reloaded.consoleOutput).toBe(false);
  });

  it('resets logger config to defaults', async () => {
    const { logger } = await import('./loggerService');

    logger.setConfig({
      enabled: false,
      level: LogLevel.ERROR,
      maxEntries: 120,
      sendToBackend: true,
      consoleOutput: false,
    });

    const reset = logger.resetConfig();
    expect(reset).toMatchObject({
      enabled: true,
      level: LogLevel.INFO,
      maxEntries: 2000,
      persistToLocalStorage: true,
      sendToBackend: false,
      consoleOutput: true,
    });
  });
});

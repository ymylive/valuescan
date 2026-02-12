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
});

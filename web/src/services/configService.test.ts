import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  DEFAULT_ANOMALY_CONFIG,
  DEFAULT_US_MARKET_CONFIG,
} from '../types/config';

vi.mock('./api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
  toApiError: vi.fn((error: unknown) => ({
    message: error instanceof Error ? error.message : 'unknown',
  })),
}));

import api from './api';
import { ConfigService } from './configService';

describe('configService', () => {
  const mockedGet = vi.mocked(api.get);
  const mockedPost = vi.mocked(api.post);

  beforeEach(() => {
    mockedGet.mockReset();
    mockedPost.mockReset();
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('normalizes partial backend configuration with defaults', async () => {
    mockedGet.mockResolvedValueOnce({
      signal: {
        ai_signal_interval_minutes: 18,
        language: 'en',
      },
      anomaly: {
        scoring_weights: {
          volume_price: 0.55,
        },
      },
      us_market: {
        categories: {
          indices: ['QQQ'],
        },
      },
    });

    const service = new ConfigService();
    const config = await service.loadConfiguration();

    expect(config.signal_monitor.ai_signal_interval_minutes).toBe(18);
    expect(config.signal_monitor.language).toBe('en');
    expect(config.anomaly.scoring_weights.volume_price).toBe(0.55);
    expect(config.anomaly.scoring_weights.derivatives).toBe(
      DEFAULT_ANOMALY_CONFIG.scoring_weights.derivatives
    );
    expect(config.us_market.categories.indices).toEqual(['QQQ']);
    expect(config.us_market.categories.tech).toEqual(
      DEFAULT_US_MARKET_CONFIG.categories.tech
    );
  });

  it('falls back to normalized local storage config when backend load fails', async () => {
    mockedGet.mockRejectedValueOnce(new Error('backend offline'));
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValueOnce(
      JSON.stringify({
        signal_monitor: { ai_signal_interval_minutes: 42 },
        anomaly: { scoring_weights: { sentiment: 0.2 } },
      })
    );

    const service = new ConfigService();
    const config = await service.loadConfiguration();

    expect(config.signal_monitor.ai_signal_interval_minutes).toBe(42);
    expect(config.anomaly.scoring_weights.sentiment).toBe(0.2);
    expect(config.anomaly.scoring_weights.volume_price).toBe(
      DEFAULT_ANOMALY_CONFIG.scoring_weights.volume_price
    );
  });

  it('returns defaults when backend and local storage both fail', async () => {
    mockedGet.mockRejectedValueOnce(new Error('backend offline'));
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValueOnce(null);

    const service = new ConfigService();
    const config = await service.loadConfiguration();

    expect(config.signal_monitor.ai_signal_interval_minutes).toBe(30);
    expect(config.logging.log_level).toBe('INFO');
    expect(config.us_market).toEqual(DEFAULT_US_MARKET_CONFIG);
  });

  it('returns partial save result when backend save fails', async () => {
    mockedPost.mockRejectedValueOnce(new Error('backend write failed'));
    mockedGet.mockResolvedValueOnce({});

    const service = new ConfigService();
    const baseConfig = await service.loadConfiguration();
    const result = await service.saveConfiguration(baseConfig);

    expect(result.localSaved).toBe(true);
    expect(result.backendSaved).toBe(false);
    expect(result.backendError?.message).toContain('backend write failed');
  });

  it('returns success save result when backend save succeeds', async () => {
    mockedPost.mockResolvedValueOnce({ success: true });
    mockedGet.mockResolvedValueOnce({});

    const service = new ConfigService();
    const baseConfig = await service.loadConfiguration();
    const result = await service.saveConfiguration(baseConfig);

    expect(result).toEqual({
      localSaved: true,
      backendSaved: true,
    });
  });
});

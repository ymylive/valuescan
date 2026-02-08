import api from './api';
import {
  TraderConfig,
  AccountInfo,
  Position,
  Decision,
  Statistics,
  EquityPoint,
} from '../types/trading';

/**
 * Trading API Service
 * Centralized API calls for AI trading functionality
 */
export const tradingApi = {
  // ==================== Trader Management ====================

  /**
   * Get all traders for the current user
   */
  getTraders: () => api.get<TraderConfig[]>('/my-traders'),

  /**
   * Get detailed configuration for a specific trader
   */
  getTraderConfig: (id: string) => api.get(`/traders/${id}/config`),

  /**
   * Get a single trader by ID
   */
  getTrader: (id: string) => api.get<TraderConfig>(`/traders/${id}`),

  /**
   * Start a trader
   */
  startTrader: (id: string) => api.post(`/traders/${id}/start`, {}),

  /**
   * Stop a trader
   */
  stopTrader: (id: string) => api.post(`/traders/${id}/stop`, {}),

  // ==================== Account & Positions ====================

  /**
   * Get account information for a trader
   * Returns total equity, available balance, PnL, etc.
   */
  getAccount: (traderId: string) =>
    api.get<AccountInfo>(`/account?trader_id=${traderId}`),

  /**
   * Get current open positions for a trader
   */
  getPositions: (traderId: string) =>
    api.get<Position[]>(`/positions?trader_id=${traderId}`),

  // ==================== Trading Decisions ====================

  /**
   * Get all trading decisions for a trader
   */
  getDecisions: (traderId: string) =>
    api.get<Decision[]>(`/decisions?trader_id=${traderId}`),

  /**
   * Get latest N trading decisions for a trader
   */
  getLatestDecisions: (traderId: string, limit: number) =>
    api.get<Decision[]>(`/decisions/latest?trader_id=${traderId}&limit=${limit}`),

  // ==================== Statistics & Performance ====================

  /**
   * Get performance statistics for a trader
   * Returns win rate, profit factor, Sharpe ratio, etc.
   */
  getStatistics: (traderId: string) =>
    api.get<Statistics>(`/statistics?trader_id=${traderId}`),

  /**
   * Get equity history for a trader
   * Returns time series of equity snapshots
   */
  getEquityHistory: (traderId: string) =>
    api.get<EquityPoint[]>(`/equity-history?trader_id=${traderId}`),

  // ==================== Trading Actions ====================

  /**
   * Close a specific position
   */
  closePosition: (traderId: string, symbol: string, side: string) =>
    api.post(`/traders/${traderId}/close-position`, { symbol, side }),
};

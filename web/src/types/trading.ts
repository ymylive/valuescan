// AI Trading Module Type Definitions

export interface TraderConfig {
  trader_id: string;
  trader_name: string;
  ai_model: string;
  exchange_id: string;
  is_running: boolean;
  initial_balance: number;
  strategy_id: string;
  strategy_name?: string;
}

export interface AccountInfo {
  total_equity: number;
  available_balance: number;
  total_pnl: number;
  total_pnl_pct: number;
  wallet_balance?: number;
  position_count?: number;
  margin_used_pct?: number;
}

export interface Position {
  symbol: string;
  side: string;
  size: number;
  entry_price: number;
  mark_price: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  leverage: number;
  margin: number;
  liquidation_price?: number;
  duration?: string;
}

export interface Decision {
  id: number;
  trader_id: string;
  timestamp: string;
  action: string;
  symbol: string;
  reason: string;
  price?: number;
  size?: number;
  pnl?: number;
  pnl_pct?: number;
}

export interface Statistics {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  total_pnl_pct: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
  best_trade?: TradeInfo;
  worst_trade?: TradeInfo;
}

export interface TradeInfo {
  symbol: string;
  pnl: number;
  pnl_pct: number;
}

export interface EquityPoint {
  timestamp: string;
  total_equity: number;
  available_balance: number;
  total_pnl: number;
  total_pnl_pct: number;
  position_count: number;
  margin_used_pct: number;
}

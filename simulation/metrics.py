"""
Simulation Metrics Module

Calculates performance metrics for virtual traders including:
- Total PnL, win rate, trade count
- Average duration, max drawdown, profit factor
- Trader rankings
"""

import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .models import VirtualTrader, PaperTrade

logger = logging.getLogger(__name__)


@dataclass
class TraderMetrics:
    """Performance metrics for a trader."""
    trader_id: str
    total_pnl: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_duration_ms: float
    max_drawdown: float
    profit_factor: float
    avg_win: float
    avg_loss: float


@dataclass
class TraderRanking:
    """Trader ranking entry."""
    rank: int
    trader_id: str
    trader_name: str
    total_pnl: float
    win_rate: float
    total_trades: int


class SimulationMetricsCalculator:
    """
    Calculator for trader performance metrics.
    
    Provides methods to calculate individual trader metrics,
    rankings, and time-filtered statistics.
    """
    
    def calculate_trader_metrics(self, trades: List[PaperTrade]) -> TraderMetrics:
        """
        Calculate performance metrics from a list of trades.
        
        Args:
            trades: List of PaperTrade records
            
        Returns:
            TraderMetrics with calculated values
        """
        if not trades:
            return TraderMetrics(
                trader_id=trades[0].trader_id if trades else '',
                total_pnl=0.0,
                win_rate=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                avg_duration_ms=0.0,
                max_drawdown=0.0,
                profit_factor=0.0,
                avg_win=0.0,
                avg_loss=0.0,
            )
        
        trader_id = trades[0].trader_id
        total_trades = len(trades)

        # Calculate wins/losses
        winning_trades = [t for t in trades if t.realized_pnl > 0]
        losing_trades = [t for t in trades if t.realized_pnl <= 0]
        
        # Total PnL
        total_pnl = sum(t.realized_pnl for t in trades)
        
        # Win rate
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
        
        # Average duration
        avg_duration_ms = sum(t.duration_ms for t in trades) / total_trades
        
        # Average win/loss
        avg_win = sum(t.realized_pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0.0
        avg_loss = sum(t.realized_pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0.0
        
        # Profit factor (gross profit / gross loss)
        gross_profit = sum(t.realized_pnl for t in winning_trades)
        gross_loss = abs(sum(t.realized_pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0.0
        
        # Max drawdown (peak to trough)
        max_drawdown = self._calculate_max_drawdown(trades)
        
        return TraderMetrics(
            trader_id=trader_id,
            total_pnl=total_pnl,
            win_rate=win_rate,
            total_trades=total_trades,
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            avg_duration_ms=avg_duration_ms,
            max_drawdown=max_drawdown,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
        )
    
    def _calculate_max_drawdown(self, trades: List[PaperTrade]) -> float:
        """
        Calculate maximum drawdown from trade history.
        
        Args:
            trades: List of trades sorted by close time
            
        Returns:
            Maximum drawdown as positive value
        """
        if not trades:
            return 0.0
        
        # Sort by close time
        sorted_trades = sorted(trades, key=lambda t: t.closed_at)
        
        # Calculate cumulative PnL
        cumulative = 0.0
        peak = 0.0
        max_drawdown = 0.0
        
        for trade in sorted_trades:
            cumulative += trade.realized_pnl
            if cumulative > peak:
                peak = cumulative
            drawdown = peak - cumulative
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return max_drawdown
    
    def calculate_rankings(
        self,
        traders: List[VirtualTrader],
        trades_by_trader: Dict[str, List[PaperTrade]]
    ) -> List[TraderRanking]:
        """
        Calculate trader rankings sorted by total PnL.
        
        Args:
            traders: List of VirtualTraders
            trades_by_trader: Dict mapping trader_id to their trades
            
        Returns:
            List of TraderRanking sorted by PnL descending
        """
        rankings = []
        
        for trader in traders:
            trades = trades_by_trader.get(trader.id, [])
            metrics = self.calculate_trader_metrics(trades) if trades else None
            
            total_pnl = metrics.total_pnl if metrics else 0.0
            win_rate = metrics.win_rate if metrics else 0.0
            total_trades = metrics.total_trades if metrics else 0
            
            rankings.append(TraderRanking(
                rank=0,  # Will be set after sorting
                trader_id=trader.id,
                trader_name=trader.name,
                total_pnl=total_pnl,
                win_rate=win_rate,
                total_trades=total_trades,
            ))
        
        # Sort by total PnL descending
        rankings.sort(key=lambda r: r.total_pnl, reverse=True)
        
        # Assign ranks
        for i, ranking in enumerate(rankings):
            ranking.rank = i + 1
        
        return rankings

    def filter_by_time_range(
        self,
        trades: List[PaperTrade],
        time_range: str
    ) -> List[PaperTrade]:
        """
        Filter trades by time range.
        
        Args:
            trades: List of trades to filter
            time_range: One of '24h', '7d', '30d', 'all'
            
        Returns:
            Filtered list of trades
        """
        if time_range == 'all':
            return trades
        
        now = int(time.time() * 1000)
        
        # Calculate cutoff time
        if time_range == '24h':
            cutoff = now - (24 * 60 * 60 * 1000)
        elif time_range == '7d':
            cutoff = now - (7 * 24 * 60 * 60 * 1000)
        elif time_range == '30d':
            cutoff = now - (30 * 24 * 60 * 60 * 1000)
        else:
            # Default to all if invalid range
            logger.warning(f"Invalid time range '{time_range}', defaulting to 'all'")
            return trades
        
        return [t for t in trades if t.closed_at >= cutoff]
    
    def filter_by_time_range_explicit(
        self,
        trades: List[PaperTrade],
        start_time: int,
        end_time: int
    ) -> List[PaperTrade]:
        """
        Filter trades by explicit time range.
        
        Args:
            trades: List of trades to filter
            start_time: Start timestamp (ms)
            end_time: End timestamp (ms)
            
        Returns:
            Filtered list of trades where start_time <= closed_at <= end_time
        """
        return [t for t in trades if start_time <= t.closed_at <= end_time]

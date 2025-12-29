"""
Metrics Calculator for Trader Performance.

This module provides calculation logic for:
- Summary metrics (total PnL, win rate, etc.)
- Cumulative PnL time series
- Time range filtering

Requirements: 5.1, 5.2, 2.2
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import time

try:
    from performance_db import TradeRecord
except ImportError:
    from api.performance_db import TradeRecord


@dataclass
class PerformanceSummary:
    """
    Aggregated performance metrics for a trader.
    
    Attributes:
        total_pnl: Total realized profit/loss
        win_rate: Percentage of winning trades (0-100)
        total_trades: Total number of trades
        avg_trade_size: Average trade size (quantity * price)
        winning_trades: Number of profitable trades
        losing_trades: Number of losing trades
    """
    total_pnl: float
    win_rate: float
    total_trades: int
    avg_trade_size: float
    winning_trades: int
    losing_trades: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'total_pnl': self.total_pnl,
            'win_rate': self.win_rate,
            'total_trades': self.total_trades,
            'avg_trade_size': self.avg_trade_size,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PerformanceSummary':
        """Create from dictionary."""
        return cls(
            total_pnl=float(data['total_pnl']),
            win_rate=float(data['win_rate']),
            total_trades=int(data['total_trades']),
            avg_trade_size=float(data['avg_trade_size']),
            winning_trades=int(data['winning_trades']),
            losing_trades=int(data['losing_trades'])
        )


@dataclass
class CumulativePnLPoint:
    """
    A single data point in the cumulative PnL time series.
    
    Attributes:
        timestamp: Unix timestamp in milliseconds
        cumulative_pnl: Cumulative PnL up to this point
        trader_id: Trader identifier
    """
    timestamp: int
    cumulative_pnl: float
    trader_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp,
            'cumulative_pnl': self.cumulative_pnl,
            'trader_id': self.trader_id
        }


@dataclass
class TraderRanking:
    """
    Ranking entry for a trader in the leaderboard.
    
    Attributes:
        trader_id: Unique identifier
        name: Display name
        total_pnl: Total realized PnL
        win_rate: Win rate percentage (0-100)
        total_trades: Total number of trades
        avg_trade_size: Average trade size
    """
    trader_id: str
    name: str
    total_pnl: float
    win_rate: float
    total_trades: int
    avg_trade_size: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'trader_id': self.trader_id,
            'name': self.name,
            'total_pnl': self.total_pnl,
            'win_rate': self.win_rate,
            'total_trades': self.total_trades,
            'avg_trade_size': self.avg_trade_size
        }


# Time range constants in milliseconds
TIME_RANGES = {
    '24h': 24 * 60 * 60 * 1000,
    '7d': 7 * 24 * 60 * 60 * 1000,
    '30d': 30 * 24 * 60 * 60 * 1000,
    'all': None  # No limit
}


class MetricsCalculator:
    """
    Calculator for trader performance metrics.
    
    Provides methods for:
    - Calculating summary metrics from trade records
    - Computing cumulative PnL time series
    - Filtering trades by time range
    
    Requirements: 5.1, 5.2, 2.2
    """
    
    @staticmethod
    def calculate_summary(trades: List[TradeRecord]) -> PerformanceSummary:
        """
        Calculate summary metrics from trade records.
        
        Args:
            trades: List of TradeRecord objects
            
        Returns:
            PerformanceSummary with aggregated metrics
            
        Requirements: 5.1, 5.2
        """
        if not trades:
            return PerformanceSummary(
                total_pnl=0.0,
                win_rate=0.0,
                total_trades=0,
                avg_trade_size=0.0,
                winning_trades=0,
                losing_trades=0
            )
        
        total_pnl = sum(t.realized_pnl for t in trades)
        total_trades = len(trades)
        
        # Count winning and losing trades
        # A trade is winning if realized_pnl > 0
        winning_trades = sum(1 for t in trades if t.realized_pnl > 0)
        losing_trades = sum(1 for t in trades if t.realized_pnl < 0)
        
        # Calculate win rate: (winning trades / total trades) × 100
        # Requirements: 5.2
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0.0
        
        # Calculate average trade size (quantity * price)
        total_size = sum(t.quantity * t.price for t in trades)
        avg_trade_size = total_size / total_trades if total_trades > 0 else 0.0
        
        return PerformanceSummary(
            total_pnl=total_pnl,
            win_rate=win_rate,
            total_trades=total_trades,
            avg_trade_size=avg_trade_size,
            winning_trades=winning_trades,
            losing_trades=losing_trades
        )
    
    @staticmethod
    def calculate_cumulative_pnl(
        trades: List[TradeRecord],
        trader_id: str = 'default'
    ) -> List[CumulativePnLPoint]:
        """
        Calculate cumulative PnL time series from trade records.
        
        Args:
            trades: List of TradeRecord objects (should be sorted by timestamp)
            trader_id: Trader identifier for the data points
            
        Returns:
            List of CumulativePnLPoint objects representing the time series
        """
        if not trades:
            return []
        
        # Sort trades by timestamp to ensure correct cumulative calculation
        sorted_trades = sorted(trades, key=lambda t: t.timestamp)
        
        cumulative_pnl = 0.0
        points = []
        
        for trade in sorted_trades:
            cumulative_pnl += trade.realized_pnl
            points.append(CumulativePnLPoint(
                timestamp=trade.timestamp,
                cumulative_pnl=cumulative_pnl,
                trader_id=trader_id
            ))
        
        return points
    
    @staticmethod
    def filter_by_time_range(
        trades: List[TradeRecord],
        time_range: str
    ) -> List[TradeRecord]:
        """
        Filter trades by time range.
        
        Args:
            trades: List of TradeRecord objects
            time_range: One of '24h', '7d', '30d', 'all'
            
        Returns:
            Filtered list of TradeRecord objects within the time range
            
        Requirements: 2.2
        """
        if time_range == 'all' or time_range not in TIME_RANGES:
            return trades
        
        range_ms = TIME_RANGES.get(time_range)
        if range_ms is None:
            return trades
        
        # Calculate the cutoff timestamp
        now_ms = int(time.time() * 1000)
        cutoff_ms = now_ms - range_ms
        
        # Filter trades with timestamp >= cutoff
        return [t for t in trades if t.timestamp >= cutoff_ms]
    
    @staticmethod
    def get_time_range_bounds(time_range: str) -> tuple:
        """
        Get the start and end timestamps for a time range.
        
        Args:
            time_range: One of '24h', '7d', '30d', 'all'
            
        Returns:
            Tuple of (start_timestamp, end_timestamp) in milliseconds
        """
        now_ms = int(time.time() * 1000)
        
        if time_range == 'all' or time_range not in TIME_RANGES:
            return (0, now_ms)
        
        range_ms = TIME_RANGES.get(time_range)
        if range_ms is None:
            return (0, now_ms)
        
        return (now_ms - range_ms, now_ms)


def get_pnl_color_class(pnl: float) -> str:
    """
    Get the CSS color class for a PnL value.
    
    Args:
        pnl: The PnL value
        
    Returns:
        'text-green-500' for positive/zero, 'text-red-500' for negative
        
    Requirements: 3.3, 3.4
    """
    if pnl >= 0:
        return 'text-green-500'
    else:
        return 'text-red-500'


def sort_rankings_by_pnl(rankings: List[TraderRanking]) -> List[TraderRanking]:
    """
    Sort trader rankings by total PnL in descending order.
    
    Args:
        rankings: List of TraderRanking objects
        
    Returns:
        Sorted list with highest PnL first
        
    Requirements: 3.1
    """
    return sorted(rankings, key=lambda r: r.total_pnl, reverse=True)

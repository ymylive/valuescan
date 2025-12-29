"""
Performance Recorder for FuturesTrader.

This module provides trade recording functionality for performance tracking.
It integrates with the performance database to persist trade data.

Requirements: 4.1
"""

import sys
import time
import logging
from pathlib import Path
from typing import Optional

# Add api directory to path for imports
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR / 'api'))

try:
    from performance_db import TradeRecord, get_performance_db, reset_db_instance
    PERFORMANCE_DB_AVAILABLE = True
except ImportError as e:
    PERFORMANCE_DB_AVAILABLE = False
    print(f"Performance DB not available: {e}")


class PerformanceRecorder:
    """
    Records trade executions for performance tracking.
    
    Integrates with the performance database to persist:
    - Trade timestamp
    - Symbol
    - Side (BUY/SELL)
    - Quantity
    - Price
    - Realized PnL
    
    Requirements: 4.1
    """
    
    def __init__(self, trader_id: str = 'default', db_path: Optional[str] = None):
        """
        Initialize the performance recorder.
        
        Args:
            trader_id: Identifier for this trader/bot
            db_path: Optional custom database path
        """
        self.trader_id = trader_id
        self.logger = logging.getLogger(__name__)
        self._db = None
        self._db_path = db_path
        
        if PERFORMANCE_DB_AVAILABLE:
            try:
                if db_path:
                    reset_db_instance()
                    from performance_db import PerformanceDatabase
                    self._db = PerformanceDatabase(db_path)
                else:
                    self._db = get_performance_db()
                self.logger.info(f"✅ Performance recorder initialized for trader: {trader_id}")
            except Exception as e:
                self.logger.warning(f"Failed to initialize performance DB: {e}")
        else:
            self.logger.warning("Performance recording disabled - module not available")
    
    def record_trade(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        realized_pnl: float,
        order_id: Optional[str] = None,
        timestamp: Optional[int] = None
    ) -> bool:
        """
        Record a trade execution.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            side: Trade direction ('BUY' or 'SELL')
            quantity: Trade quantity
            price: Execution price
            realized_pnl: Realized profit/loss from this trade
            order_id: Optional exchange order ID
            timestamp: Optional timestamp in milliseconds (defaults to now)
            
        Returns:
            True if recorded successfully, False otherwise
            
        Requirements: 4.1
        """
        if not self._db:
            self.logger.debug("Performance DB not available, skipping trade recording")
            return False
        
        try:
            trade = TradeRecord(
                id=None,
                trader_id=self.trader_id,
                timestamp=timestamp or int(time.time() * 1000),
                symbol=symbol,
                side=side.upper(),
                quantity=float(quantity),
                price=float(price),
                realized_pnl=float(realized_pnl),
                order_id=str(order_id) if order_id else None
            )
            
            trade_id = self._db.save_trade(trade)
            self.logger.info(
                f"📊 Trade recorded: {symbol} {side} {quantity} @ {price}, "
                f"PnL: {realized_pnl:.2f}, ID: {trade_id}"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to record trade: {e}")
            return False
    
    def record_open_position(
        self,
        symbol: str,
        quantity: float,
        entry_price: float,
        order_id: Optional[str] = None
    ) -> bool:
        """
        Record an open position trade (BUY).
        
        For open positions, realized_pnl is 0 since no profit/loss is realized yet.
        
        Args:
            symbol: Trading pair symbol
            quantity: Position quantity
            entry_price: Entry price
            order_id: Optional exchange order ID
            
        Returns:
            True if recorded successfully
        """
        return self.record_trade(
            symbol=symbol,
            side='BUY',
            quantity=quantity,
            price=entry_price,
            realized_pnl=0.0,  # No realized PnL on open
            order_id=order_id
        )
    
    def record_close_position(
        self,
        symbol: str,
        quantity: float,
        exit_price: float,
        realized_pnl: float,
        order_id: Optional[str] = None
    ) -> bool:
        """
        Record a close position trade (SELL).
        
        Args:
            symbol: Trading pair symbol
            quantity: Position quantity closed
            exit_price: Exit price
            realized_pnl: Realized profit/loss
            order_id: Optional exchange order ID
            
        Returns:
            True if recorded successfully
        """
        return self.record_trade(
            symbol=symbol,
            side='SELL',
            quantity=quantity,
            price=exit_price,
            realized_pnl=realized_pnl,
            order_id=order_id
        )
    
    @property
    def is_available(self) -> bool:
        """Check if performance recording is available."""
        return self._db is not None

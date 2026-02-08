"""
Simulation Price Updater Service

Background service that periodically updates all simulation positions with current prices.
This triggers stop-loss, take-profit, pyramiding exits, and trailing stops.
"""

import time
import logging
import threading
from typing import Optional

from .signal_bridge import get_simulation_engine

logger = logging.getLogger(__name__)


class SimulationPriceUpdater:
    """
    Background service for updating simulation positions with real-time prices.
    
    Runs in a separate thread and periodically calls update_all_positions()
    to check exit conditions and update unrealized PnL.
    """
    
    def __init__(self, update_interval: int = 10):
        """
        Initialize price updater.
        
        Args:
            update_interval: Update interval in seconds (default: 10s, matching real system)
        """
        self.update_interval = update_interval
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
    def start(self):
        """Start the background price updater."""
        if self.running:
            logger.warning("Price updater already running")
            return
        
        self.running = True
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
        logger.info(f"✅ Simulation price updater started (interval: {self.update_interval}s)")
    
    def stop(self):
        """Stop the background price updater."""
        if not self.running:
            return
        
        self.running = False
        self._stop_event.set()
        
        if self.thread:
            self.thread.join(timeout=5)
        
        logger.info("Simulation price updater stopped")
    
    def _update_loop(self):
        """Main update loop - runs in background thread."""
        logger.info("Price updater loop started")
        
        while self.running and not self._stop_event.is_set():
            try:
                self._update_prices()
            except Exception as e:
                logger.error(f"Error in price update loop: {e}", exc_info=True)
            
            # Sleep with interrupt check
            self._stop_event.wait(self.update_interval)
    
    def _update_prices(self):
        """Update all positions with current prices."""
        try:
            engine = get_simulation_engine()
            closed_by_symbol = engine.update_all_positions()
            
            # Log closed trades
            total_closed = sum(len(trades) for trades in closed_by_symbol.values())
            if total_closed > 0:
                logger.info(f"💰 Price update closed {total_closed} positions:")
                for symbol, trades in closed_by_symbol.items():
                    for trade in trades:
                        reason_emoji = {
                            'TP': '🎯',
                            'SL': '🛑',
                            'TRAILING_STOP': '📉',
                        }
                        emoji = reason_emoji.get(trade.exit_reason, '✅')
                        pnl_sign = '+' if trade.realized_pnl >= 0 else ''
                        logger.info(
                            f"  {emoji} {symbol} {trade.side}: "
                            f"{pnl_sign}{trade.realized_pnl:.2f} USDT ({trade.exit_reason})"
                        )
        except Exception as e:
            logger.error(f"Failed to update prices: {e}")


# Global updater instance
_price_updater: Optional[SimulationPriceUpdater] = None


def get_price_updater(update_interval: int = 10) -> SimulationPriceUpdater:
    """
    Get global price updater instance (singleton).
    
    Args:
        update_interval: Update interval in seconds
        
    Returns:
        SimulationPriceUpdater instance
    """
    global _price_updater
    if _price_updater is None:
        _price_updater = SimulationPriceUpdater(update_interval)
    return _price_updater


def start_price_updater(update_interval: int = 10):
    """
    Start the background price updater service.
    
    Args:
        update_interval: Update interval in seconds (default: 10s)
    """
    updater = get_price_updater(update_interval)
    updater.start()


def stop_price_updater():
    """Stop the background price updater service."""
    if _price_updater:
        _price_updater.stop()

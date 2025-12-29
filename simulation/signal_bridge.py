"""
Signal Bridge Module

Connects the simulation engine to the existing signal monitor.
Uses SignalAggregator to match FOMO + Alpha signals, exactly like the real trading system.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Callable

# Import SignalAggregator from binance_trader
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "binance_trader"))
from signal_aggregator import SignalAggregator, ConfluenceSignal

from .database import get_simulation_database
from .engine import SimulationEngine, Signal

logger = logging.getLogger(__name__)

# Global instances
_simulation_engine: Optional[SimulationEngine] = None
_signal_aggregator: Optional[SignalAggregator] = None


def get_simulation_engine() -> SimulationEngine:
    """Get or create the global simulation engine instance."""
    global _simulation_engine
    if _simulation_engine is None:
        db = get_simulation_database()
        _simulation_engine = SimulationEngine(db)
    return _simulation_engine


def get_signal_aggregator() -> SignalAggregator:
    """Get or create the global signal aggregator instance."""
    global _signal_aggregator
    if _signal_aggregator is None:
        # Use same config as real trading system
        _signal_aggregator = SignalAggregator(
            time_window=300,  # 5 minutes
            min_score=0.6,
            state_file=None,  # No persistence for simulation
            enable_persistence=False
        )
    return _signal_aggregator


def forward_signal_to_simulation(
    message_type: int,
    message_id: str,
    symbol: str,
    price: float,
    data: dict = None
) -> int:
    """
    Forward a ValueScan signal to simulation (with aggregation logic).
    
    This function matches the real trading system's signal processing:
    - Type 113 (FOMO) + Type 110 (Alpha) = BUY signal
    - Type 112 (FOMO Intensify) = Risk signal (trigger partial profit-taking)
    
    Args:
        message_type: ValueScan message type (110=Alpha, 113=FOMO, 112=FOMO Intensify)
        message_id: Message unique ID
        symbol: Trading pair base (e.g., "BTC")
        price: Current price
        data: Original message data
        
    Returns:
        Number of positions created
    """
    engine = get_simulation_engine()
    aggregator = get_signal_aggregator()

    try:
        engine.price_tracker.update_cache(f"{symbol}USDT", float(price))
    except Exception:
        pass
    
    # Add signal to aggregator
    confluence = aggregator.add_signal(
        message_type=message_type,
        message_id=message_id,
        symbol=symbol,
        data=data or {}
    )
    
    # Handle risk signal (FOMO Intensify)
    if message_type == 112:
        logger.warning(f"⚠️  Simulation: Risk signal detected for {symbol}, triggering partial profit-taking")
        closed_count = engine.handle_risk_signal(symbol)
        logger.info(f"Simulation: Closed {closed_count} positions due to risk signal")
        return 0
    
    # If confluence matched, create positions
    if confluence:
        positions = _handle_confluence_signal(confluence, price)
        logger.info(f"Simulation: Confluence signal processed for {confluence.symbol}, created {len(positions)} positions")
        return len(positions)
    
    return 0


def _handle_confluence_signal(confluence: ConfluenceSignal, price: float):
    """Handle confluence signal - create positions for all enabled traders."""
    engine = get_simulation_engine()
    
    # Create signal for simulation engine
    # Use confluence score as both confidence and indicator score
    signal = Signal(
        symbol=confluence.symbol + "USDT",  # Add USDT suffix
        side="LONG",  # Confluence signals are always LONG
        price=price,
        confidence=confluence.score,  # Use aggregator score as confidence
        indicator_scores={'confluence': confluence.score},  # Pass score as indicator
        timestamp=int(confluence.confluence_time.timestamp() * 1000),
    )
    
    return engine.process_signal(signal)


def update_simulation_prices():
    """
    Update all simulation positions with current prices.
    
    This function should be called periodically to update
    unrealized PnL and check exit conditions.
    
    Returns:
        Dict mapping symbol to list of closed trades
    """
    engine = get_simulation_engine()
    return engine.update_all_positions()


# Callback registration for integration with signal monitor
_signal_callback: Optional[Callable] = None


def register_signal_callback(callback: Callable):
    """
    Register a callback to be called when simulation processes a signal.
    
    Args:
        callback: Function(symbol, side, positions_created)
    """
    global _signal_callback
    _signal_callback = callback


def on_signal_processed(symbol: str, side: str, positions_created: int):
    """Notify registered callback of processed signal."""
    if _signal_callback:
        try:
            _signal_callback(symbol, side, positions_created)
        except Exception as e:
            logger.error(f"Signal callback error: {e}")

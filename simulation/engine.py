"""
Simulation Engine Module

Core engine that coordinates all simulation components:
- Processes trading signals
- Manages positions across all traders
- Integrates with AI trading engine for decision making
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from .database import SimulationDatabase
from .models import VirtualTrader, SimulatedPosition, PaperTrade
from .trader_repository import TraderRepository
from .position_manager import PositionManager
from .price_tracker import PriceTracker

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """Trading signal data."""
    symbol: str
    side: str  # LONG or SHORT
    price: float
    confidence: float
    indicator_scores: Dict[str, float]  # Indicator name -> score
    timestamp: int


class SimulationEngine:
    """
    Core simulation engine that coordinates all components.
    
    Processes trading signals, creates positions for enabled traders,
    and manages the simulation lifecycle.
    """
    
    def __init__(self, db: SimulationDatabase, ai_engine: Optional[Any] = None):
        """
        Initialize simulation engine.
        
        Args:
            db: SimulationDatabase instance
            ai_engine: Optional AI trading engine for decision making
        """
        self.db = db
        self.ai_engine = ai_engine
        self.trader_repo = TraderRepository(db)
        self.position_manager = PositionManager(db)
        self.price_tracker = PriceTracker()

    def process_signal(self, signal: Signal) -> List[SimulatedPosition]:
        """
        Process a trading signal for all enabled traders.
        
        Creates positions for traders that:
        1. Are enabled
        2. Pass the AI decision evaluation
        3. Have sufficient balance
        
        Args:
            signal: Trading signal to process
            
        Returns:
            List of created positions
        """
        created_positions = []
        enabled_traders = self.trader_repo.get_enabled_traders()
        
        for trader in enabled_traders:
            # Evaluate if trader should take this signal
            if not self.evaluate_decision(trader, signal):
                logger.debug(f"Trader {trader.name} rejected signal for {signal.symbol}")
                continue
            
            # Calculate position size based on trader config
            position_size = self._calculate_position_size(trader, signal.price)
            
            # Try to open position
            position, error = self.position_manager.open_position(
                trader=trader,
                symbol=signal.symbol,
                side=signal.side,
                entry_price=signal.price,
                quantity=position_size,
            )
            
            if position:
                created_positions.append(position)
                logger.info(f"Created position for {trader.name}: {signal.symbol} {signal.side}")
            else:
                logger.warning(f"Failed to create position for {trader.name}: {error}")
        
        return created_positions
    
    def evaluate_decision(self, trader: VirtualTrader, signal: Signal) -> bool:
        """
        Evaluate if a trader should take a signal based on AI parameters.
        
        Checks:
        1. Signal confidence >= trader's confidence_threshold
        2. For LONG: weighted score >= buy_threshold
        3. For SHORT: weighted score >= sell_threshold
        
        Args:
            trader: VirtualTrader to evaluate for
            signal: Signal to evaluate
            
        Returns:
            True if trader should take the signal
        """
        # Check confidence threshold
        if signal.confidence < trader.confidence_threshold:
            return False
        
        # Calculate weighted score using trader's indicator weights
        weighted_score = self._calculate_weighted_score(
            signal.indicator_scores,
            trader.indicator_weights
        )
        
        # Check buy/sell threshold
        if signal.side == 'LONG':
            return weighted_score >= trader.buy_threshold
        else:  # SHORT
            return weighted_score >= trader.sell_threshold
    
    def _calculate_weighted_score(
        self,
        indicator_scores: Dict[str, float],
        weights: Dict[str, float]
    ) -> float:
        """
        Calculate weighted average of indicator scores.
        
        Args:
            indicator_scores: Dict of indicator name to score
            weights: Dict of indicator name to weight
            
        Returns:
            Weighted average score (0-1)
        """
        if not indicator_scores or not weights:
            # If no weights configured, use simple average
            if indicator_scores:
                return sum(indicator_scores.values()) / len(indicator_scores)
            return 0.5  # Default neutral score
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for indicator, score in indicator_scores.items():
            weight = weights.get(indicator, 1.0)  # Default weight of 1
            weighted_sum += score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.5
        
        return weighted_sum / total_weight

    def _calculate_position_size(self, trader: VirtualTrader, price: float) -> float:
        """
        Calculate position size based on trader config.
        
        Uses max_position_pct to determine how much of balance to use.
        
        Args:
            trader: VirtualTrader
            price: Entry price
            
        Returns:
            Position quantity
        """
        # Calculate max position value based on percentage
        max_position_value = trader.current_balance * (trader.max_position_pct / 100)
        
        # Apply leverage
        position_value = max_position_value * trader.leverage
        
        # Calculate quantity
        quantity = position_value / price
        
        return quantity
    
    def update_positions(self, symbol: str, price: float) -> List[PaperTrade]:
        """
        Update all open positions for a symbol with new price.
        
        Checks exit conditions and closes positions if triggered.
        
        Args:
            symbol: Trading pair
            price: Current price
            
        Returns:
            List of closed trades (if any)
        """
        closed_trades = []
        positions = self.position_manager.get_positions_by_symbol(symbol)
        
        for position in positions:
            # Get trader for fee rate
            trader = self.trader_repo.get_trader(position.trader_id)
            fee_rate = trader.fee_rate if trader else 0.0004
            
            # Check exit conditions
            exit_reason = self.position_manager.check_exit_conditions(position, price)
            
            if exit_reason:
                # Close position
                trade = self.position_manager.close_position(position, price, exit_reason)
                closed_trades.append(trade)
                logger.info(f"Position {position.id} closed: {exit_reason} at {price}")
            else:
                # Update unrealized PnL
                self.position_manager.update_position_price(position, price, fee_rate)
        
        return closed_trades
    
    def update_all_positions(self) -> Dict[str, List[PaperTrade]]:
        """
        Update all open positions with current prices.
        
        Fetches prices for all symbols with open positions and updates them.
        
        Returns:
            Dict mapping symbol to list of closed trades
        """
        # Get all unique symbols with open positions
        all_positions = self.position_manager.get_open_positions()
        symbols = list(set(p.symbol for p in all_positions))
        
        if not symbols:
            return {}
        
        # Fetch prices
        prices = self.price_tracker.get_prices(symbols)
        
        # Update positions for each symbol
        closed_by_symbol = {}
        for symbol, price in prices.items():
            closed = self.update_positions(symbol, price)
            if closed:
                closed_by_symbol[symbol] = closed
        
        return closed_by_symbol
    
    def handle_risk_signal(self, symbol: str) -> int:
        """
        Handle risk signal (FOMO Intensify) - partial profit-taking.
        
        Matches real trading system behavior:
        - Close 50% of profitable positions for the symbol
        - Only applies to positions with positive unrealized PnL
        
        Args:
            symbol: Symbol base (e.g., "BTC")
            
        Returns:
            Number of positions partially closed
        """
        binance_symbol = f"{symbol}USDT"
        positions = self.position_manager.get_positions_by_symbol(binance_symbol)
        
        closed_count = 0
        for position in positions:
            # Only close profitable positions
            if position.unrealized_pnl > 0:
                trader = self.trader_repo.get_trader(position.trader_id)
                if not trader:
                    continue
                
                # Get current price
                current_price = position.current_price or position.entry_price
                
                # Close 50% of position
                partial_close = self.position_manager.partial_close_position(
                    position=position,
                    close_ratio=0.5,
                    exit_price=current_price,
                    exit_reason="FOMO_INTENSIFY_RISK"
                )
                
                if partial_close:
                    closed_count += 1
                    logger.info(
                        f"Risk signal: Closed 50% of {trader.name}'s {binance_symbol} position, "
                        f"PnL: {position.unrealized_pnl:.2f}"
                    )
        
        return closed_count
    
    def get_trader_summary(self, trader_id: str) -> Dict[str, Any]:
        """
        Get summary of trader's current state.
        
        Args:
            trader_id: Trader ID
            
        Returns:
            Summary dict with trader info, positions, and trades
        """
        trader = self.trader_repo.get_trader(trader_id)
        if not trader:
            return {}
        
        positions = self.position_manager.get_open_positions(trader_id)
        trades = self.position_manager.get_trades(trader_id)
        
        return {
            'trader': trader.to_dict(),
            'open_positions': [p.to_dict() for p in positions],
            'recent_trades': [t.to_dict() for t in trades[:10]],
            'total_trades': len(trades),
        }

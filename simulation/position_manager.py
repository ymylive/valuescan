"""
Position Manager Module

Handles opening, closing, and managing simulated trading positions.
Includes PnL calculation and exit condition checking.
"""

import uuid
import time
import logging
from typing import Optional, List, Tuple

from .database import SimulationDatabase
from .models import VirtualTrader, SimulatedPosition, PaperTrade

logger = logging.getLogger(__name__)


class PositionManager:
    """
    Manager for simulated trading positions.
    
    Handles position lifecycle: open, update, close.
    Calculates PnL and checks exit conditions (TP/SL).
    """
    
    def __init__(self, db: SimulationDatabase):
        """
        Initialize position manager.
        
        Args:
            db: SimulationDatabase instance
        """
        self.db = db
    
    def open_position(
        self,
        trader: VirtualTrader,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        take_profit: Optional[float] = None,
        stop_loss: Optional[float] = None,
        enable_trailing_stop: bool = True,
        enable_pyramiding: bool = True
    ) -> Tuple[Optional[SimulatedPosition], Optional[str]]:
        """
        Open a new simulated position with balance validation.
        
        Args:
            trader: VirtualTrader opening the position
            symbol: Trading pair (e.g., BTCUSDT)
            side: Position direction (LONG/SHORT)
            entry_price: Entry price
            quantity: Position size
            take_profit: Optional take profit price
            stop_loss: Optional stop loss price
            enable_trailing_stop: Enable trailing stop (default True)
            enable_pyramiding: Enable pyramiding exit (default True)
            
        Returns:
            Tuple of (SimulatedPosition, None) on success,
            or (None, error_message) on failure
        """
        # Calculate required margin
        position_value = entry_price * quantity
        required_margin = position_value / trader.leverage
        
        # Validate balance
        if required_margin > trader.current_balance:
            error = f"Insufficient balance: need {required_margin:.2f}, have {trader.current_balance:.2f}"
            logger.warning(f"Position rejected for {trader.name}: {error}")
            return None, error

        # Calculate default TP/SL if not provided
        if take_profit is None:
            if side == 'LONG':
                take_profit = entry_price * (1 + trader.default_tp_pct / 100)
            else:
                take_profit = entry_price * (1 - trader.default_tp_pct / 100)
        
        if stop_loss is None:
            if side == 'LONG':
                stop_loss = entry_price * (1 - trader.default_sl_pct / 100)
            else:
                stop_loss = entry_price * (1 + trader.default_sl_pct / 100)
        
        # Setup pyramiding levels (matching real system)
        pyramiding_levels = []
        if enable_pyramiding:
            pyramiding_levels = [
                {'price': 3.0, 'ratio': 0.5, 'executed': False},  # 3% profit -> close 50%
                {'price': 5.0, 'ratio': 0.5, 'executed': False},  # 5% profit -> close 50% of remaining
                {'price': 8.0, 'ratio': 1.0, 'executed': False},  # 8% profit -> close all
            ]
        
        # Create position
        position = SimulatedPosition(
            id=str(uuid.uuid4()),
            trader_id=trader.id,
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            quantity=quantity,
            leverage=trader.leverage,
            take_profit=take_profit,
            stop_loss=stop_loss,
            opened_at=int(time.time() * 1000),
            status='OPEN',
            unrealized_pnl=0.0,
            current_price=entry_price,
            last_updated=int(time.time() * 1000),
            pyramiding_levels=pyramiding_levels,
            trailing_stop_enabled=enable_trailing_stop,
            trailing_callback_pct=1.5,  # 1.5% callback (matching real system)
            highest_price=entry_price,
        )
        
        # Save to database
        self._save_position(position)
        
        logger.info(
            f"Opened {side} position for {trader.name}: {symbol} @ {entry_price}, "
            f"TP={take_profit:.2f}, SL={stop_loss:.2f}, "
            f"Pyramiding={'ON' if pyramiding_levels else 'OFF'}, "
            f"Trailing={'ON' if enable_trailing_stop else 'OFF'}"
        )
        return position, None
    
    def close_position(
        self,
        position: SimulatedPosition,
        exit_price: float,
        exit_reason: str
    ) -> PaperTrade:
        """
        Close a position and create trade record.
        
        Args:
            position: Position to close
            exit_price: Exit price
            exit_reason: Reason for exit (TP/SL/MANUAL)
            
        Returns:
            PaperTrade record
        """
        # Get trader for fee calculation
        trader = self._get_trader(position.trader_id)
        fee_rate = trader.fee_rate if trader else 0.0004
        
        # Calculate realized PnL
        realized_pnl, fees = self.calculate_pnl(
            position, exit_price, fee_rate
        )
        
        # Create trade record
        closed_at = int(time.time() * 1000)
        trade = PaperTrade(
            id=str(uuid.uuid4()),
            trader_id=position.trader_id,
            position_id=position.id,
            symbol=position.symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=position.quantity,
            leverage=position.leverage,
            realized_pnl=realized_pnl,
            fees=fees,
            duration_ms=closed_at - position.opened_at,
            exit_reason=exit_reason,
            opened_at=position.opened_at,
            closed_at=closed_at,
        )
        
        # Update position status
        position.status = 'CLOSED'
        position.current_price = exit_price
        position.unrealized_pnl = realized_pnl
        position.last_updated = closed_at
        self._update_position(position)
        
        # Save trade record
        self._save_trade(trade)
        
        # Update trader balance
        if trader:
            new_balance = trader.current_balance + realized_pnl
            self._update_trader_balance(trader.id, new_balance)
        
        logger.info(f"Closed position {position.id}: PnL={realized_pnl:.2f}, reason={exit_reason}")
        return trade
    
    def partial_close_position(
        self,
        position: SimulatedPosition,
        close_ratio: float,
        exit_price: float,
        exit_reason: str
    ) -> Optional[PaperTrade]:
        """
        Partially close a position (for pyramiding exit or risk management).
        
        Creates a new trade record for the closed portion and reduces position size.
        
        Args:
            position: Position to partially close
            close_ratio: Ratio to close (0-1), e.g., 0.5 for 50%
            exit_price: Exit price
            exit_reason: Reason for partial close
            
        Returns:
            PaperTrade record for the closed portion, or None if failed
        """
        if close_ratio <= 0 or close_ratio >= 1:
            logger.error(f"Invalid close_ratio: {close_ratio}, must be between 0 and 1")
            return None
        
        if position.status != 'OPEN':
            logger.warning(f"Cannot partially close position {position.id}: status is {position.status}")
            return None
        
        # Get trader for fee calculation
        trader = self._get_trader(position.trader_id)
        fee_rate = trader.fee_rate if trader else 0.0004
        
        # Calculate PnL for the portion being closed
        closed_quantity = position.quantity * close_ratio
        
        # Create a temporary position for PnL calculation
        temp_position = SimulatedPosition(
            id=position.id,
            trader_id=position.trader_id,
            symbol=position.symbol,
            side=position.side,
            entry_price=position.entry_price,
            quantity=closed_quantity,
            leverage=position.leverage,
            take_profit=position.take_profit,
            stop_loss=position.stop_loss,
            opened_at=position.opened_at,
            status='OPEN',
            unrealized_pnl=0,
            current_price=exit_price,
            last_updated=int(time.time() * 1000)
        )
        
        realized_pnl, fees = self.calculate_pnl(temp_position, exit_price, fee_rate)
        
        # Create trade record for closed portion
        closed_at = int(time.time() * 1000)
        trade = PaperTrade(
            id=str(uuid.uuid4()),
            trader_id=position.trader_id,
            position_id=position.id,
            symbol=position.symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=closed_quantity,
            leverage=position.leverage,
            realized_pnl=realized_pnl,
            fees=fees,
            duration_ms=closed_at - position.opened_at,
            exit_reason=f"PARTIAL_{exit_reason}_{int(close_ratio*100)}PCT",
            opened_at=position.opened_at,
            closed_at=closed_at,
        )
        
        # Save trade record
        self._save_trade(trade)
        
        # Update position: reduce quantity
        remaining_quantity = position.quantity * (1 - close_ratio)
        position.quantity = remaining_quantity
        position.last_updated = closed_at
        
        # Update database
        self.db.execute(
            'UPDATE simulated_positions SET quantity = ?, last_updated = ? WHERE id = ?',
            (position.quantity, position.last_updated, position.id)
        )
        
        # Update trader balance
        if trader:
            new_balance = trader.current_balance + realized_pnl
            self._update_trader_balance(trader.id, new_balance)
        
        logger.info(
            f"Partially closed position {position.id}: "
            f"{close_ratio*100:.0f}% closed, PnL={realized_pnl:.2f}, "
            f"remaining quantity={remaining_quantity:.4f}"
        )
        
        return trade

    def calculate_pnl(
        self,
        position: SimulatedPosition,
        current_price: float,
        fee_rate: float = 0.0004
    ) -> Tuple[float, float]:
        """
        Calculate PnL for a position.
        
        Formula: (current_price - entry_price) * quantity * direction * leverage - fees
        Fees: entry_fee + exit_fee = (entry_price * quantity * fee_rate) + (current_price * quantity * fee_rate)
        
        Args:
            position: Position to calculate PnL for
            current_price: Current market price
            fee_rate: Trading fee rate (default 0.04%)
            
        Returns:
            Tuple of (pnl, total_fees)
        """
        direction = 1 if position.side == 'LONG' else -1
        
        # Calculate raw PnL
        price_diff = current_price - position.entry_price
        raw_pnl = price_diff * position.quantity * direction * position.leverage
        
        # Calculate fees
        entry_fee = position.entry_price * position.quantity * fee_rate
        exit_fee = current_price * position.quantity * fee_rate
        total_fees = entry_fee + exit_fee
        
        # Net PnL
        net_pnl = raw_pnl - total_fees
        
        return net_pnl, total_fees
    
    def check_exit_conditions(
        self,
        position: SimulatedPosition,
        current_price: float
    ) -> Optional[str]:
        """
        Check if position should be closed based on TP/SL, pyramiding, or trailing stop.
        
        Priority:
        1. Stop loss
        2. Trailing stop
        3. Pyramiding take profit levels
        4. Primary take profit
        
        Args:
            position: Position to check
            current_price: Current market price
            
        Returns:
            Exit reason if triggered, None otherwise
        """
        if position.status != 'OPEN':
            return None
        
        # Check stop loss first (highest priority)
        if position.side == 'LONG':
            if position.stop_loss and current_price <= position.stop_loss:
                return 'SL'
        else:  # SHORT
            if position.stop_loss and current_price >= position.stop_loss:
                return 'SL'
        
        # Check trailing stop
        if position.trailing_stop_enabled and position.highest_price:
            trailing_stop_triggered = self._check_trailing_stop(position, current_price)
            if trailing_stop_triggered:
                return 'TRAILING_STOP'
        
        # Check pyramiding levels (partial closes handled separately)
        # This returns None to let update_positions handle pyramiding
        
        # Check primary take profit
        if position.side == 'LONG':
            if position.take_profit and current_price >= position.take_profit:
                return 'TP'
        else:  # SHORT
            if position.take_profit and current_price <= position.take_profit:
                return 'TP'
        
        return None
    
    def _check_trailing_stop(self, position: SimulatedPosition, current_price: float) -> bool:
        """
        Check if trailing stop should trigger.
        
        Returns True if price has pulled back enough from highest price.
        """
        if not position.highest_price or not position.trailing_callback_pct:
            return False
        
        if position.side == 'LONG':
            # For LONG: trigger if price drops from highest by callback %
            pullback_threshold = position.highest_price * (1 - position.trailing_callback_pct / 100)
            return current_price <= pullback_threshold
        else:  # SHORT
            # For SHORT: trigger if price rises from lowest by callback %
            pullback_threshold = position.highest_price * (1 + position.trailing_callback_pct / 100)
            return current_price >= pullback_threshold
    
    def check_pyramiding_levels(
        self,
        position: SimulatedPosition,
        current_price: float
    ) -> Optional[Tuple[float, float]]:
        """
        Check if any pyramiding TP level should trigger.
        
        Returns:
            Tuple of (price, ratio) if a level triggered, None otherwise
        """
        if not position.pyramiding_levels:
            return None
        
        profit_pct = ((current_price - position.entry_price) / position.entry_price) * 100
        if position.side == 'SHORT':
            profit_pct = -profit_pct
        
        # Find the first unexecuted level that's been reached
        for level in position.pyramiding_levels:
            if not level.get('executed', False) and profit_pct >= level['price']:
                return (level['price'], level['ratio'])
        
        return None
    
    def update_position_price(
        self,
        position: SimulatedPosition,
        current_price: float,
        fee_rate: float = 0.0004
    ) -> SimulatedPosition:
        """
        Update position with current price and recalculate unrealized PnL.
        Also updates trailing stop highest price and checks pyramiding levels.
        
        Args:
            position: Position to update
            current_price: Current market price
            fee_rate: Fee rate for PnL calculation
            
        Returns:
            Updated position
        """
        pnl, _ = self.calculate_pnl(position, current_price, fee_rate)
        position.current_price = current_price
        position.unrealized_pnl = pnl
        position.last_updated = int(time.time() * 1000)
        
        # Update trailing stop highest price
        if position.trailing_stop_enabled:
            if position.side == 'LONG':
                if position.highest_price is None or current_price > position.highest_price:
                    position.highest_price = current_price
            else:  # SHORT
                if position.highest_price is None or current_price < position.highest_price:
                    position.highest_price = current_price
        
        # Check and execute pyramiding levels
        pyramiding_trigger = self.check_pyramiding_levels(position, current_price)
        if pyramiding_trigger:
            tp_price, close_ratio = pyramiding_trigger
            logger.info(f"Pyramiding TP triggered: {tp_price}% profit, closing {close_ratio*100}% of position")
            
            # Mark level as executed
            for level in position.pyramiding_levels:
                if level['price'] == tp_price and not level.get('executed'):
                    level['executed'] = True
                    break
            
            # Execute partial close
            self.partial_close_position(
                position=position,
                close_ratio=close_ratio,
                exit_price=current_price,
                exit_reason=f"PYRAMIDING_TP_{int(tp_price)}PCT"
            )
        
        self._update_position(position)
        return position

    def get_open_positions(self, trader_id: Optional[str] = None) -> List[SimulatedPosition]:
        """
        Get all open positions, optionally filtered by trader.
        
        Args:
            trader_id: Optional trader ID to filter by
            
        Returns:
            List of open positions
        """
        if trader_id:
            rows = self.db.fetchall(
                'SELECT * FROM simulated_positions WHERE trader_id = ? AND status = ?',
                (trader_id, 'OPEN')
            )
        else:
            rows = self.db.fetchall(
                'SELECT * FROM simulated_positions WHERE status = ?',
                ('OPEN',)
            )
        return [self._row_to_position(row) for row in rows]
    
    def get_positions_by_symbol(self, symbol: str) -> List[SimulatedPosition]:
        """
        Get all open positions for a symbol.
        
        Args:
            symbol: Trading pair
            
        Returns:
            List of open positions for the symbol
        """
        rows = self.db.fetchall(
            'SELECT * FROM simulated_positions WHERE symbol = ? AND status = ?',
            (symbol, 'OPEN')
        )
        return [self._row_to_position(row) for row in rows]
    
    def get_trades(self, trader_id: str) -> List[PaperTrade]:
        """
        Get all trades for a trader.
        
        Args:
            trader_id: Trader ID
            
        Returns:
            List of paper trades
        """
        rows = self.db.fetchall(
            'SELECT * FROM paper_trades WHERE trader_id = ? ORDER BY closed_at DESC',
            (trader_id,)
        )
        return [self._row_to_trade(row) for row in rows]
    
    # Database helper methods
    
    def _save_position(self, position: SimulatedPosition) -> None:
        """Save position to database."""
        import json
        
        pyramiding_json = json.dumps(position.pyramiding_levels) if position.pyramiding_levels else None
        
        self.db.execute('''
            INSERT INTO simulated_positions (
                id, trader_id, symbol, side, entry_price, quantity, leverage,
                take_profit, stop_loss, opened_at, status, unrealized_pnl,
                current_price, last_updated, pyramiding_levels, 
                trailing_stop_enabled, trailing_callback_pct, highest_price
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            position.id, position.trader_id, position.symbol, position.side,
            position.entry_price, position.quantity, position.leverage,
            position.take_profit, position.stop_loss, position.opened_at,
            position.status, position.unrealized_pnl, position.current_price,
            position.last_updated, pyramiding_json,
            int(position.trailing_stop_enabled), position.trailing_callback_pct,
            position.highest_price
        ))
    
    def _update_position(self, position: SimulatedPosition) -> None:
        """Update position in database."""
        import json
        
        pyramiding_json = json.dumps(position.pyramiding_levels) if position.pyramiding_levels else None
        
        self.db.execute('''
            UPDATE simulated_positions SET
                status = ?, unrealized_pnl = ?, current_price = ?, last_updated = ?,
                quantity = ?, pyramiding_levels = ?, highest_price = ?
            WHERE id = ?
        ''', (
            position.status, position.unrealized_pnl, position.current_price,
            position.last_updated, position.quantity, pyramiding_json, 
            position.highest_price, position.id
        ))
    
    def _save_trade(self, trade: PaperTrade) -> None:
        """Save trade to database."""
        self.db.execute('''
            INSERT INTO paper_trades (
                id, trader_id, position_id, symbol, side, entry_price, exit_price,
                quantity, leverage, realized_pnl, fees, duration_ms, exit_reason,
                opened_at, closed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade.id, trade.trader_id, trade.position_id, trade.symbol, trade.side,
            trade.entry_price, trade.exit_price, trade.quantity, trade.leverage,
            trade.realized_pnl, trade.fees, trade.duration_ms, trade.exit_reason,
            trade.opened_at, trade.closed_at
        ))

    def _get_trader(self, trader_id: str) -> Optional[VirtualTrader]:
        """Get trader from database."""
        import json
        row = self.db.fetchone(
            'SELECT * FROM virtual_traders WHERE id = ?',
            (trader_id,)
        )
        if row is None:
            return None
        
        indicator_weights = {}
        if row['indicator_weights']:
            try:
                indicator_weights = json.loads(row['indicator_weights'])
            except json.JSONDecodeError:
                pass
        
        return VirtualTrader(
            id=row['id'],
            name=row['name'],
            initial_balance=row['initial_balance'],
            current_balance=row['current_balance'],
            leverage=row['leverage'],
            enabled=bool(row['enabled']),
            created_at=row['created_at'],
            confidence_threshold=row['confidence_threshold'],
            buy_threshold=row['buy_threshold'],
            sell_threshold=row['sell_threshold'],
            max_position_pct=row['max_position_pct'],
            default_sl_pct=row['default_sl_pct'],
            default_tp_pct=row['default_tp_pct'],
            fee_rate=row['fee_rate'],
            indicator_weights=indicator_weights,
        )
    
    def _update_trader_balance(self, trader_id: str, new_balance: float) -> None:
        """Update trader balance in database."""
        self.db.execute(
            'UPDATE virtual_traders SET current_balance = ? WHERE id = ?',
            (new_balance, trader_id)
        )
    
    def _row_to_position(self, row) -> SimulatedPosition:
        """Convert database row to SimulatedPosition."""
        import json
        
        pyramiding_levels = []
        pyramiding_json = row['pyramiding_levels'] if 'pyramiding_levels' in row.keys() else None
        if pyramiding_json:
            try:
                pyramiding_levels = json.loads(pyramiding_json)
            except json.JSONDecodeError:
                pass
        
        return SimulatedPosition(
            id=row['id'],
            trader_id=row['trader_id'],
            symbol=row['symbol'],
            side=row['side'],
            entry_price=row['entry_price'],
            quantity=row['quantity'],
            leverage=row['leverage'],
            take_profit=row['take_profit'],
            stop_loss=row['stop_loss'],
            opened_at=row['opened_at'],
            status=row['status'],
            unrealized_pnl=row['unrealized_pnl'],
            current_price=row['current_price'],
            last_updated=row['last_updated'],
            pyramiding_levels=pyramiding_levels,
            trailing_stop_enabled=bool(row['trailing_stop_enabled']) if 'trailing_stop_enabled' in row.keys() else False,
            trailing_callback_pct=row['trailing_callback_pct'] if 'trailing_callback_pct' in row.keys() else 0.0,
            highest_price=row['highest_price'] if 'highest_price' in row.keys() else None,
        )
    
    def _row_to_trade(self, row) -> PaperTrade:
        """Convert database row to PaperTrade."""
        return PaperTrade(
            id=row['id'],
            trader_id=row['trader_id'],
            position_id=row['position_id'],
            symbol=row['symbol'],
            side=row['side'],
            entry_price=row['entry_price'],
            exit_price=row['exit_price'],
            quantity=row['quantity'],
            leverage=row['leverage'],
            realized_pnl=row['realized_pnl'],
            fees=row['fees'],
            duration_ms=row['duration_ms'],
            exit_reason=row['exit_reason'],
            opened_at=row['opened_at'],
            closed_at=row['closed_at'],
        )

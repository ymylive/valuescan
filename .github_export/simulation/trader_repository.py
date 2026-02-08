"""
Trader Repository Module

CRUD operations for VirtualTrader management with database persistence.
"""

import json
import uuid
import time
import logging
from typing import Optional, List, Dict, Any

from .database import SimulationDatabase
from .models import VirtualTrader, SimulatedPosition, PaperTrade

logger = logging.getLogger(__name__)


class TraderRepository:
    """
    Repository for VirtualTrader CRUD operations.
    
    Handles persistence of trader configurations and provides
    methods for creating, reading, updating, and deleting traders.
    """
    
    def __init__(self, db: SimulationDatabase):
        """
        Initialize repository with database connection.
        
        Args:
            db: SimulationDatabase instance
        """
        self.db = db
    
    def save_trader(self, trader: VirtualTrader) -> VirtualTrader:
        """
        Save a new trader to the database.
        
        Args:
            trader: VirtualTrader to save
            
        Returns:
            Saved VirtualTrader with ID
        """
        indicator_weights_json = json.dumps(trader.indicator_weights)
        
        self.db.execute('''
            INSERT INTO virtual_traders (
                id, name, initial_balance, current_balance, leverage, enabled, created_at,
                confidence_threshold, buy_threshold, sell_threshold,
                max_position_pct, default_sl_pct, default_tp_pct, fee_rate,
                indicator_weights
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trader.id, trader.name, trader.initial_balance, trader.current_balance,
            trader.leverage, 1 if trader.enabled else 0, trader.created_at,
            trader.confidence_threshold, trader.buy_threshold, trader.sell_threshold,
            trader.max_position_pct, trader.default_sl_pct, trader.default_tp_pct,
            trader.fee_rate, indicator_weights_json
        ))
        
        logger.info(f"Saved trader: {trader.name} ({trader.id})")
        return trader

    def get_trader(self, trader_id: str) -> Optional[VirtualTrader]:
        """
        Get a trader by ID.
        
        Args:
            trader_id: Trader ID to look up
            
        Returns:
            VirtualTrader if found, None otherwise
        """
        row = self.db.fetchone(
            'SELECT * FROM virtual_traders WHERE id = ?',
            (trader_id,)
        )
        
        if row is None:
            return None
        
        return self._row_to_trader(row)
    
    def get_all_traders(self) -> List[VirtualTrader]:
        """
        Get all traders.
        
        Returns:
            List of all VirtualTraders
        """
        rows = self.db.fetchall('SELECT * FROM virtual_traders ORDER BY created_at DESC')
        return [self._row_to_trader(row) for row in rows]
    
    def get_enabled_traders(self) -> List[VirtualTrader]:
        """
        Get all enabled traders.
        
        Returns:
            List of enabled VirtualTraders
        """
        rows = self.db.fetchall(
            'SELECT * FROM virtual_traders WHERE enabled = 1 ORDER BY created_at DESC'
        )
        return [self._row_to_trader(row) for row in rows]
    
    def update_trader(self, trader: VirtualTrader) -> VirtualTrader:
        """
        Update an existing trader.
        
        Args:
            trader: VirtualTrader with updated values
            
        Returns:
            Updated VirtualTrader
        """
        indicator_weights_json = json.dumps(trader.indicator_weights)
        
        self.db.execute('''
            UPDATE virtual_traders SET
                name = ?, initial_balance = ?, current_balance = ?, leverage = ?,
                enabled = ?, confidence_threshold = ?, buy_threshold = ?, sell_threshold = ?,
                max_position_pct = ?, default_sl_pct = ?, default_tp_pct = ?, fee_rate = ?,
                indicator_weights = ?
            WHERE id = ?
        ''', (
            trader.name, trader.initial_balance, trader.current_balance, trader.leverage,
            1 if trader.enabled else 0, trader.confidence_threshold, trader.buy_threshold,
            trader.sell_threshold, trader.max_position_pct, trader.default_sl_pct,
            trader.default_tp_pct, trader.fee_rate, indicator_weights_json, trader.id
        ))
        
        logger.info(f"Updated trader: {trader.name} ({trader.id})")
        return trader
    
    def update_balance(self, trader_id: str, new_balance: float) -> None:
        """
        Update trader's current balance.
        
        Args:
            trader_id: Trader ID
            new_balance: New balance value
        """
        self.db.execute(
            'UPDATE virtual_traders SET current_balance = ? WHERE id = ?',
            (new_balance, trader_id)
        )
    
    def delete_trader(self, trader_id: str) -> bool:
        """
        Delete a trader and all associated positions and trades (cascade).
        
        Args:
            trader_id: Trader ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        # Check if trader exists
        existing = self.get_trader(trader_id)
        if existing is None:
            return False
        
        # Delete associated positions first (cascade handled by FK, but explicit for safety)
        self.db.execute('DELETE FROM paper_trades WHERE trader_id = ?', (trader_id,))
        self.db.execute('DELETE FROM simulated_positions WHERE trader_id = ?', (trader_id,))
        self.db.execute('DELETE FROM virtual_traders WHERE id = ?', (trader_id,))
        
        logger.info(f"Deleted trader: {trader_id}")
        return True

    def clone_trader(self, trader_id: str, new_name: Optional[str] = None) -> Optional[VirtualTrader]:
        """
        Clone an existing trader with reset metrics.
        
        Creates a new trader with identical configuration but:
        - New unique ID
        - Modified name with "(Copy)" suffix (or custom name)
        - current_balance reset to initial_balance
        - New created_at timestamp
        
        Args:
            trader_id: ID of trader to clone
            new_name: Optional custom name for clone
            
        Returns:
            New VirtualTrader if source found, None otherwise
        """
        source = self.get_trader(trader_id)
        if source is None:
            return None
        
        # Create clone with reset metrics
        clone = VirtualTrader(
            id=str(uuid.uuid4()),
            name=new_name or f"{source.name} (Copy)",
            initial_balance=source.initial_balance,
            current_balance=source.initial_balance,  # Reset to initial
            leverage=source.leverage,
            enabled=source.enabled,
            created_at=int(time.time() * 1000),  # New timestamp
            confidence_threshold=source.confidence_threshold,
            buy_threshold=source.buy_threshold,
            sell_threshold=source.sell_threshold,
            max_position_pct=source.max_position_pct,
            default_sl_pct=source.default_sl_pct,
            default_tp_pct=source.default_tp_pct,
            fee_rate=source.fee_rate,
            indicator_weights=source.indicator_weights.copy(),
        )
        
        return self.save_trader(clone)
    
    def _row_to_trader(self, row) -> VirtualTrader:
        """
        Convert database row to VirtualTrader.
        
        Args:
            row: Database row (sqlite3.Row)
            
        Returns:
            VirtualTrader instance
        """
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
    
    def get_trader_count(self) -> int:
        """
        Get total number of traders.
        
        Returns:
            Number of traders
        """
        row = self.db.fetchone('SELECT COUNT(*) as count FROM virtual_traders')
        return row['count'] if row else 0

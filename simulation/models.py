"""
Simulation Data Models

Dataclasses for VirtualTrader, SimulatedPosition, and PaperTrade
with JSON serialization support for persistence.
"""

import json
import uuid
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, Any, List


@dataclass
class VirtualTrader:
    """
    Virtual trader configuration with AI parameters and risk settings.
    
    Attributes:
        id: Unique identifier
        name: Display name
        initial_balance: Starting balance in USDT
        current_balance: Current balance after trades
        leverage: Leverage multiplier (1-125)
        enabled: Whether trader is active
        created_at: Creation timestamp (ms)
        confidence_threshold: AI confidence threshold (0-1)
        buy_threshold: Buy signal threshold (0-1)
        sell_threshold: Sell signal threshold (0-1)
        max_position_pct: Max position size as % of balance
        default_sl_pct: Default stop-loss percentage
        default_tp_pct: Default take-profit percentage
        fee_rate: Trading fee rate
        indicator_weights: Dict of indicator name to weight
    """
    name: str
    initial_balance: float
    current_balance: float
    leverage: int = 1
    enabled: bool = True
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # AI Parameters
    confidence_threshold: float = 0.6
    buy_threshold: float = 0.7
    sell_threshold: float = 0.7
    
    # Risk Parameters
    max_position_pct: float = 10.0
    default_sl_pct: float = 2.0
    default_tp_pct: float = 5.0
    fee_rate: float = 0.0004
    
    # Indicator Weights
    indicator_weights: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for storage.
        
        Returns:
            Dict representation of trader
        """
        return {
            'id': self.id,
            'name': self.name,
            'initial_balance': self.initial_balance,
            'current_balance': self.current_balance,
            'leverage': self.leverage,
            'enabled': self.enabled,
            'created_at': self.created_at,
            'confidence_threshold': self.confidence_threshold,
            'buy_threshold': self.buy_threshold,
            'sell_threshold': self.sell_threshold,
            'max_position_pct': self.max_position_pct,
            'default_sl_pct': self.default_sl_pct,
            'default_tp_pct': self.default_tp_pct,
            'fee_rate': self.fee_rate,
            'indicator_weights': self.indicator_weights,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VirtualTrader':
        """
        Create VirtualTrader from dictionary.
        
        Args:
            data: Dictionary with trader fields
            
        Returns:
            VirtualTrader instance
        """
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data['name'],
            initial_balance=data['initial_balance'],
            current_balance=data['current_balance'],
            leverage=data.get('leverage', 1),
            enabled=data.get('enabled', True),
            created_at=data.get('created_at', int(time.time() * 1000)),
            confidence_threshold=data.get('confidence_threshold', 0.6),
            buy_threshold=data.get('buy_threshold', 0.7),
            sell_threshold=data.get('sell_threshold', 0.7),
            max_position_pct=data.get('max_position_pct', 10.0),
            default_sl_pct=data.get('default_sl_pct', 2.0),
            default_tp_pct=data.get('default_tp_pct', 5.0),
            fee_rate=data.get('fee_rate', 0.0004),
            indicator_weights=data.get('indicator_weights', {}),
        )
    
    def to_json(self) -> str:
        """
        Serialize to JSON string.
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'VirtualTrader':
        """
        Deserialize from JSON string.
        
        Args:
            json_str: JSON string
            
        Returns:
            VirtualTrader instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class SimulatedPosition:
    """
    Simulated trading position.
    
    Attributes:
        id: Unique identifier
        trader_id: Associated virtual trader ID
        symbol: Trading pair (e.g., BTCUSDT)
        side: Position direction (LONG/SHORT)
        entry_price: Entry price
        quantity: Position size
        leverage: Leverage used
        take_profit: Take profit price (primary, or list for pyramiding)
        pyramiding_tp_levels: List of (price, ratio) tuples for multi-level TP
        trailing_stop_active: Whether trailing stop is active
        trailing_stop_callback: Trailing stop callback percentage
        highest_price_since_entry: Highest price since position opened
        stop_loss: Stop loss price
        opened_at: Open timestamp (ms)
        status: Position status (OPEN/CLOSED)
        unrealized_pnl: Current unrealized PnL
        current_price: Latest price
        last_updated: Last update timestamp (ms)
    """
    trader_id: str
    symbol: str
    side: str
    entry_price: float
    quantity: float
    leverage: int
    opened_at: int = field(default_factory=lambda: int(time.time() * 1000))
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    status: str = 'OPEN'
    unrealized_pnl: float = 0.0
    current_price: Optional[float] = None
    last_updated: Optional[int] = None
    
    # Pyramiding TP tracking
    pyramiding_levels: List[Dict[str, Any]] = field(default_factory=list)  # [{"price": float, "ratio": float, "executed": bool}]
    
    # Trailing stop tracking
    trailing_stop_enabled: bool = False
    trailing_callback_pct: float = 0.0
    highest_price: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for storage.
        
        Returns:
            Dict representation of position
        """
        return {
            'id': self.id,
            'trader_id': self.trader_id,
            'symbol': self.symbol,
            'side': self.side,
            'entry_price': self.entry_price,
            'quantity': self.quantity,
            'leverage': self.leverage,
            'take_profit': self.take_profit,
            'stop_loss': self.stop_loss,
            'opened_at': self.opened_at,
            'status': self.status,
            'unrealized_pnl': self.unrealized_pnl,
            'current_price': self.current_price,
            'last_updated': self.last_updated,
            'pyramiding_levels': self.pyramiding_levels,
            'trailing_stop_enabled': self.trailing_stop_enabled,
            'trailing_callback_pct': self.trailing_callback_pct,
            'highest_price': self.highest_price,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimulatedPosition':
        """
        Create SimulatedPosition from dictionary.
        
        Args:
            data: Dictionary with position fields
            
        Returns:
            SimulatedPosition instance
        """
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            trader_id=data['trader_id'],
            symbol=data['symbol'],
            side=data['side'],
            entry_price=data['entry_price'],
            quantity=data['quantity'],
            leverage=data['leverage'],
            take_profit=data.get('take_profit'),
            stop_loss=data.get('stop_loss'),
            opened_at=data.get('opened_at', int(time.time() * 1000)),
            status=data.get('status', 'OPEN'),
            unrealized_pnl=data.get('unrealized_pnl', 0.0),
            current_price=data.get('current_price'),
            last_updated=data.get('last_updated'),
        )
    
    def to_json(self) -> str:
        """
        Serialize to JSON string.
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'SimulatedPosition':
        """
        Deserialize from JSON string.
        
        Args:
            json_str: JSON string
            
        Returns:
            SimulatedPosition instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)



@dataclass
class PaperTrade:
    """
    Paper trade record for closed positions.
    
    Attributes:
        id: Unique identifier
        trader_id: Associated virtual trader ID
        position_id: Associated position ID
        symbol: Trading pair
        side: Trade direction (LONG/SHORT)
        entry_price: Entry price
        exit_price: Exit price
        quantity: Trade size
        leverage: Leverage used
        realized_pnl: Realized profit/loss
        fees: Total fees paid
        duration_ms: Position duration in milliseconds
        exit_reason: Reason for exit (TP/SL/MANUAL)
        opened_at: Open timestamp (ms)
        closed_at: Close timestamp (ms)
    """
    trader_id: str
    position_id: str
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    quantity: float
    leverage: int
    realized_pnl: float
    fees: float
    duration_ms: int
    exit_reason: str
    opened_at: int
    closed_at: int
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for storage.
        
        Returns:
            Dict representation of trade
        """
        return {
            'id': self.id,
            'trader_id': self.trader_id,
            'position_id': self.position_id,
            'symbol': self.symbol,
            'side': self.side,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'quantity': self.quantity,
            'leverage': self.leverage,
            'realized_pnl': self.realized_pnl,
            'fees': self.fees,
            'duration_ms': self.duration_ms,
            'exit_reason': self.exit_reason,
            'opened_at': self.opened_at,
            'closed_at': self.closed_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PaperTrade':
        """
        Create PaperTrade from dictionary.
        
        Args:
            data: Dictionary with trade fields
            
        Returns:
            PaperTrade instance
        """
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            trader_id=data['trader_id'],
            position_id=data['position_id'],
            symbol=data['symbol'],
            side=data['side'],
            entry_price=data['entry_price'],
            exit_price=data['exit_price'],
            quantity=data['quantity'],
            leverage=data['leverage'],
            realized_pnl=data['realized_pnl'],
            fees=data['fees'],
            duration_ms=data['duration_ms'],
            exit_reason=data['exit_reason'],
            opened_at=data['opened_at'],
            closed_at=data['closed_at'],
        )

"""
Simulation Database Module

SQLite database for storing virtual traders, simulated positions, and paper trades.
Implements connection management with context manager support.
"""

import sqlite3
import os
import logging
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class SimulationDatabase:
    """
    Database manager for the multi-trader simulation system.
    
    Manages virtual_traders, simulated_positions, and paper_trades tables
    with proper indexing for efficient querying.
    """
    
    def __init__(self, db_path: str = 'simulation.db'):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._init_database()
    
    def init_schema(self):
        """Initialize database schema and indexes (public method for testing)."""
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema and indexes."""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            cursor = self.conn.cursor()
            
            # Enable foreign keys
            cursor.execute('PRAGMA foreign_keys = ON')
            
            # Create virtual_traders table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS virtual_traders (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    initial_balance REAL NOT NULL,
                    current_balance REAL NOT NULL,
                    leverage INTEGER NOT NULL DEFAULT 1,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at INTEGER NOT NULL,
                    
                    -- AI Parameters
                    confidence_threshold REAL DEFAULT 0.6,
                    buy_threshold REAL DEFAULT 0.7,
                    sell_threshold REAL DEFAULT 0.7,
                    
                    -- Risk Parameters
                    max_position_pct REAL DEFAULT 10.0,
                    default_sl_pct REAL DEFAULT 2.0,
                    default_tp_pct REAL DEFAULT 5.0,
                    fee_rate REAL DEFAULT 0.0004,
                    
                    -- Indicator Weights (JSON)
                    indicator_weights TEXT
                )
            ''')
            
            # Create simulated_positions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS simulated_positions (
                    id TEXT PRIMARY KEY,
                    trader_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    leverage INTEGER NOT NULL,
                    take_profit REAL,
                    stop_loss REAL,
                    opened_at INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'OPEN',
                    unrealized_pnl REAL DEFAULT 0,
                    current_price REAL,
                    last_updated INTEGER,
                    
                    -- Pyramiding TP levels (JSON array)
                    pyramiding_levels TEXT,
                    
                    -- Trailing stop settings
                    trailing_stop_enabled INTEGER DEFAULT 0,
                    trailing_callback_pct REAL DEFAULT 0,
                    highest_price REAL,
                    
                    FOREIGN KEY (trader_id) REFERENCES virtual_traders(id) ON DELETE CASCADE
                )
            ''')

            # Create paper_trades table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS paper_trades (
                    id TEXT PRIMARY KEY,
                    trader_id TEXT NOT NULL,
                    position_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    leverage INTEGER NOT NULL,
                    realized_pnl REAL NOT NULL,
                    fees REAL NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    exit_reason TEXT NOT NULL,
                    opened_at INTEGER NOT NULL,
                    closed_at INTEGER NOT NULL,
                    FOREIGN KEY (trader_id) REFERENCES virtual_traders(id) ON DELETE CASCADE
                )
            ''')
            
            # Create indexes for efficient querying
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_positions_trader 
                ON simulated_positions(trader_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_positions_symbol 
                ON simulated_positions(symbol)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_positions_status 
                ON simulated_positions(status)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_trades_trader 
                ON paper_trades(trader_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_trades_closed_at 
                ON paper_trades(closed_at)
            ''')
            
            self.conn.commit()
            logger.info(f"✅ Simulation database initialized: {self.db_path}")
            
        except sqlite3.Error as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    @contextmanager
    def get_cursor(self):
        """
        Context manager for database cursor operations.
        
        Yields:
            sqlite3.Cursor: Database cursor
        """
        cursor = self.conn.cursor()
        try:
            yield cursor
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute a SQL query.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Cursor with query results
        """
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()
        return cursor
    
    def fetchone(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """
        Execute query and fetch one result.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Single row or None
        """
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()
    
    def fetchall(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """
        Execute query and fetch all results.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of rows
        """
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Simulation database connection closed")
    
    def __enter__(self):
        """Support with statement."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support with statement."""
        self.close()


# Global database instance
_db_instance: Optional[SimulationDatabase] = None


def get_simulation_database(db_path: str = 'simulation.db') -> SimulationDatabase:
    """
    Get global database instance (singleton pattern).
    
    Args:
        db_path: Path to database file
        
    Returns:
        SimulationDatabase instance
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = SimulationDatabase(db_path)
    return _db_instance

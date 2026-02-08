"""
Multi-Trader Simulation System

模拟交易系统，允许创建多个虚拟交易员测试不同策略
"""

from .models import VirtualTrader, SimulatedPosition, PaperTrade
from .database import SimulationDatabase
from .trader_repository import TraderRepository
from .position_manager import PositionManager
from .price_tracker import PriceTracker
from .engine import SimulationEngine, Signal
from .metrics import SimulationMetricsCalculator, TraderMetrics, TraderRanking
from .api_routes import simulation_bp
from .signal_bridge import (
    forward_signal_to_simulation,
    update_simulation_prices,
    get_simulation_engine,
)
from .price_updater import (
    start_price_updater,
    stop_price_updater,
    get_price_updater,
)

__all__ = [
    'SimulationDatabase',
    'get_simulation_database',
    'VirtualTrader',
    'SimulatedPosition',
    'PaperTrade',
    'SimulationEngine',
    'PositionManager',
    'PriceTracker',
    'TraderRepository',
    'SimulationMetricsCalculator',
    'TraderRanking',
    'simulation_bp',
    'forward_signal_to_simulation',
    'update_simulation_prices',
    'get_simulation_engine',
    'start_price_updater',
    'stop_price_updater',
    'get_price_updater',
]

"""
Simulation API Routes

Flask blueprint for simulation management endpoints.
"""

from flask import Blueprint, request, jsonify
import logging

from .database import SimulationDatabase, get_simulation_database
from .models import VirtualTrader
from .trader_repository import TraderRepository
from .position_manager import PositionManager
from .metrics import SimulationMetricsCalculator
from .signal_bridge import forward_signal_to_simulation, get_simulation_engine, update_simulation_prices

logger = logging.getLogger(__name__)

# Create blueprint
simulation_bp = Blueprint('simulation', __name__, url_prefix='/api/simulation')

# Initialize components (will be set up on first request)
_db = None
_trader_repo = None
_position_manager = None
_metrics_calc = None


def _get_components():
    """Get or initialize simulation components."""
    global _db, _trader_repo, _position_manager, _metrics_calc
    if _db is None:
        _db = get_simulation_database()
        _trader_repo = TraderRepository(_db)
        _position_manager = PositionManager(_db)
        _metrics_calc = SimulationMetricsCalculator()
    return _db, _trader_repo, _position_manager, _metrics_calc


# ============ Trader CRUD Endpoints ============

@simulation_bp.route('/traders', methods=['GET'])
def get_traders():
    """Get all virtual traders."""
    _, trader_repo, _, _ = _get_components()
    traders = trader_repo.get_all_traders()
    return jsonify({
        'success': True,
        'data': [t.to_dict() for t in traders]
    })


@simulation_bp.route('/traders/<trader_id>', methods=['GET'])
def get_trader(trader_id):
    """Get a specific trader by ID."""
    _, trader_repo, _, _ = _get_components()
    trader = trader_repo.get_trader(trader_id)
    if not trader:
        return jsonify({'success': False, 'error': 'Trader not found'}), 404
    return jsonify({'success': True, 'data': trader.to_dict()})


@simulation_bp.route('/traders', methods=['POST'])
def create_trader():
    """Create a new virtual trader."""
    _, trader_repo, _, _ = _get_components()
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    # Validate required fields
    required = ['name', 'initial_balance']
    for field in required:
        if field not in data:
            return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400
    
    try:
        trader = VirtualTrader(
            name=data['name'],
            initial_balance=float(data['initial_balance']),
            current_balance=float(data['initial_balance']),
            leverage=int(data.get('leverage', 1)),
            enabled=data.get('enabled', True),
            confidence_threshold=float(data.get('confidence_threshold', 0.6)),
            buy_threshold=float(data.get('buy_threshold', 0.7)),
            sell_threshold=float(data.get('sell_threshold', 0.7)),
            max_position_pct=float(data.get('max_position_pct', 10.0)),
            default_sl_pct=float(data.get('default_sl_pct', 2.0)),
            default_tp_pct=float(data.get('default_tp_pct', 5.0)),
            fee_rate=float(data.get('fee_rate', 0.0004)),
            indicator_weights=data.get('indicator_weights', {}),
        )
        saved = trader_repo.save_trader(trader)
        return jsonify({'success': True, 'data': saved.to_dict()}), 201
    except Exception as e:
        logger.error(f"Error creating trader: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@simulation_bp.route('/traders/<trader_id>', methods=['PUT'])
def update_trader(trader_id):
    """Update an existing trader."""
    _, trader_repo, _, _ = _get_components()
    
    trader = trader_repo.get_trader(trader_id)
    if not trader:
        return jsonify({'success': False, 'error': 'Trader not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    try:
        # Update fields
        if 'name' in data:
            trader.name = data['name']
        if 'initial_balance' in data:
            trader.initial_balance = float(data['initial_balance'])
        if 'current_balance' in data:
            trader.current_balance = float(data['current_balance'])
        if 'leverage' in data:
            trader.leverage = int(data['leverage'])
        if 'enabled' in data:
            trader.enabled = bool(data['enabled'])
        if 'confidence_threshold' in data:
            trader.confidence_threshold = float(data['confidence_threshold'])
        if 'buy_threshold' in data:
            trader.buy_threshold = float(data['buy_threshold'])
        if 'sell_threshold' in data:
            trader.sell_threshold = float(data['sell_threshold'])
        if 'max_position_pct' in data:
            trader.max_position_pct = float(data['max_position_pct'])
        if 'default_sl_pct' in data:
            trader.default_sl_pct = float(data['default_sl_pct'])
        if 'default_tp_pct' in data:
            trader.default_tp_pct = float(data['default_tp_pct'])
        if 'fee_rate' in data:
            trader.fee_rate = float(data['fee_rate'])
        if 'indicator_weights' in data:
            trader.indicator_weights = data['indicator_weights']
        
        updated = trader_repo.update_trader(trader)
        return jsonify({'success': True, 'data': updated.to_dict()})
    except Exception as e:
        logger.error(f"Error updating trader: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@simulation_bp.route('/traders/<trader_id>', methods=['DELETE'])
def delete_trader(trader_id):
    """Delete a trader and all associated data."""
    _, trader_repo, _, _ = _get_components()
    
    deleted = trader_repo.delete_trader(trader_id)
    if not deleted:
        return jsonify({'success': False, 'error': 'Trader not found'}), 404
    return jsonify({'success': True, 'message': 'Trader deleted'})


@simulation_bp.route('/traders/<trader_id>/clone', methods=['POST'])
def clone_trader(trader_id):
    """Clone an existing trader."""
    _, trader_repo, _, _ = _get_components()
    
    data = request.get_json() or {}
    new_name = data.get('name')
    
    clone = trader_repo.clone_trader(trader_id, new_name)
    if not clone:
        return jsonify({'success': False, 'error': 'Source trader not found'}), 404
    return jsonify({'success': True, 'data': clone.to_dict()}), 201


# ============ Position Endpoints ============

@simulation_bp.route('/traders/<trader_id>/positions', methods=['GET'])
def get_trader_positions(trader_id):
    """Get open positions for a trader."""
    _, trader_repo, position_manager, _ = _get_components()
    
    trader = trader_repo.get_trader(trader_id)
    if not trader:
        return jsonify({'success': False, 'error': 'Trader not found'}), 404
    
    positions = position_manager.get_open_positions(trader_id)
    return jsonify({
        'success': True,
        'data': [p.to_dict() for p in positions]
    })


@simulation_bp.route('/traders/<trader_id>/trades', methods=['GET'])
def get_trader_trades(trader_id):
    """Get trade history for a trader."""
    _, trader_repo, position_manager, _ = _get_components()
    
    trader = trader_repo.get_trader(trader_id)
    if not trader:
        return jsonify({'success': False, 'error': 'Trader not found'}), 404
    
    trades = position_manager.get_trades(trader_id)
    return jsonify({
        'success': True,
        'data': [t.to_dict() for t in trades]
    })


# ============ Metrics Endpoints ============

@simulation_bp.route('/traders/<trader_id>/metrics', methods=['GET'])
def get_trader_metrics(trader_id):
    """Get performance metrics for a trader."""
    _, trader_repo, position_manager, metrics_calc = _get_components()
    
    trader = trader_repo.get_trader(trader_id)
    if not trader:
        return jsonify({'success': False, 'error': 'Trader not found'}), 404
    
    # Get time range from query params
    time_range = request.args.get('range', 'all')
    
    trades = position_manager.get_trades(trader_id)
    filtered_trades = metrics_calc.filter_by_time_range(trades, time_range)
    metrics = metrics_calc.calculate_trader_metrics(filtered_trades)
    
    # Calculate avg_pnl
    avg_pnl = metrics.total_pnl / metrics.total_trades if metrics.total_trades > 0 else 0.0
    
    # Calculate Sharpe ratio (simplified: avg_pnl / std_dev of pnl)
    sharpe_ratio = 0.0
    if filtered_trades and len(filtered_trades) > 1:
        pnl_values = [t.realized_pnl for t in filtered_trades]
        avg = sum(pnl_values) / len(pnl_values)
        variance = sum((x - avg) ** 2 for x in pnl_values) / len(pnl_values)
        std_dev = variance ** 0.5
        if std_dev > 0:
            sharpe_ratio = avg / std_dev
    
    return jsonify({
        'success': True,
        'data': {
            'trader_id': metrics.trader_id,
            'total_pnl': metrics.total_pnl,
            'win_rate': metrics.win_rate,
            'total_trades': metrics.total_trades,
            'winning_trades': metrics.winning_trades,
            'losing_trades': metrics.losing_trades,
            'avg_duration_ms': metrics.avg_duration_ms,
            'max_drawdown': metrics.max_drawdown,
            'profit_factor': metrics.profit_factor,
            'avg_win': metrics.avg_win,
            'avg_loss': metrics.avg_loss,
            'avg_pnl': avg_pnl,
            'sharpe_ratio': sharpe_ratio,
        }
    })


@simulation_bp.route('/rankings', methods=['GET'])
def get_rankings():
    """Get trader rankings sorted by PnL."""
    _, trader_repo, position_manager, metrics_calc = _get_components()
    
    # Get time range from query params
    time_range = request.args.get('range', 'all')
    
    traders = trader_repo.get_all_traders()
    
    # Get trades for each trader
    trades_by_trader = {}
    for trader in traders:
        trades = position_manager.get_trades(trader.id)
        filtered = metrics_calc.filter_by_time_range(trades, time_range)
        trades_by_trader[trader.id] = filtered
    
    rankings = metrics_calc.calculate_rankings(traders, trades_by_trader)
    
    return jsonify({
        'success': True,
        'data': [{
            'rank': r.rank,
            'trader_id': r.trader_id,
            'trader_name': r.trader_name,
            'total_pnl': r.total_pnl,
            'win_rate': r.win_rate,
            'total_trades': r.total_trades,
        } for r in rankings]
    })


# ============ Signal/Tick Endpoints ============

@simulation_bp.route('/signal', methods=['POST'])
def process_signal():
    """
    Process a trading signal through the simulation engine.

    Body:
        symbol (str): e.g. "BTCUSDT" or "BTC"
        side (str): "LONG" or "SHORT" (default: "LONG")
        price (float, optional): If omitted, fetched from Binance public API
        confidence (float, optional): 0-1 (default: 0.7)
        indicator_scores (dict, optional): indicator -> score (0-1)

    Returns:
        { success: bool, data: { positions_created, symbol, side, price, confidence } }
    """
    data = request.get_json(silent=True) or {}

    symbol = (data.get('symbol') or '').strip().upper()
    if not symbol:
        return jsonify({'success': False, 'error': 'Missing field: symbol'}), 400
    if not symbol.endswith('USDT'):
        symbol = f'{symbol}USDT'

    side = (data.get('side') or 'LONG').strip().upper()
    if side in {'BUY', 'LONG'}:
        side = 'LONG'
    elif side in {'SELL', 'SHORT'}:
        side = 'SHORT'
    else:
        return jsonify({'success': False, 'error': 'Invalid side (use LONG/SHORT)'}), 400

    confidence = data.get('confidence', 0.7)
    try:
        confidence = float(confidence)
    except Exception:
        return jsonify({'success': False, 'error': 'Invalid confidence'}), 400
    if not (0.0 <= confidence <= 1.0):
        return jsonify({'success': False, 'error': 'Confidence must be between 0 and 1'}), 400

    indicator_scores = data.get('indicator_scores') or {}
    if indicator_scores is not None and not isinstance(indicator_scores, dict):
        return jsonify({'success': False, 'error': 'indicator_scores must be an object'}), 400

    price = data.get('price')
    if price is None:
        try:
            engine = get_simulation_engine()
            fetched = engine.price_tracker.get_price(symbol)
            if fetched is None:
                return jsonify({'success': False, 'error': f'Unable to fetch price for {symbol}'}), 502
            price = fetched
        except Exception as e:
            logger.exception("Failed to fetch price for signal")
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        try:
            price = float(price)
        except Exception:
            return jsonify({'success': False, 'error': 'Invalid price'}), 400

    try:
        positions_created = forward_signal_to_simulation(
            symbol=symbol,
            side=side,
            price=price,
            confidence=confidence,
            indicator_scores=indicator_scores,
        )
        return jsonify({
            'success': True,
            'data': {
                'positions_created': positions_created,
                'symbol': symbol,
                'side': side,
                'price': price,
                'confidence': confidence,
            }
        })
    except Exception as e:
        logger.exception("Simulation signal processing failed")
        return jsonify({'success': False, 'error': str(e)}), 500


@simulation_bp.route('/tick', methods=['POST'])
def tick():
    """
    Run one simulation "tick" to update open positions with current prices.

    Returns:
        { success: bool, data: { closed_trades_total, closed_trades_by_symbol } }
    """
    try:
        closed_by_symbol = update_simulation_prices() or {}
        payload = {}
        total = 0
        for symbol, trades in closed_by_symbol.items():
            payload[symbol] = [t.to_dict() for t in trades]
            total += len(trades)

        return jsonify({
            'success': True,
            'data': {
                'closed_trades_total': total,
                'closed_trades_by_symbol': payload,
            }
        })
    except Exception as e:
        logger.exception("Simulation tick failed")
        return jsonify({'success': False, 'error': str(e)}), 500

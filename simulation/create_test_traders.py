#!/usr/bin/env python3
"""
Create Test Traders Script

Creates 10 virtual traders with slightly different parameters based on
the current valuescan trading configuration.

Each trader will have variations in:
- Confidence threshold
- Buy/Sell thresholds
- Stop loss %
- Take profit %
- Max position %
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulation import SimulationDatabase, VirtualTrader
from simulation.trader_repository import TraderRepository


def create_test_traders():
    """
    Create 10 test traders with varying parameters.
    
    Base parameters from valuescan config.py:
    - Leverage: 10x
    - Stop loss: 2%
    - Take profit: 3%/5%/8% (pyramiding)
    - Max position: 5% (changed to 10% for simulation)
    - Fee rate: 0.04%
    - Signal score threshold: 0.6
    """
    
    db = SimulationDatabase('simulation.db')
    repo = TraderRepository(db)
    
    # Base configuration
    base_config = {
        'initial_balance': 10000.0,  # 10,000 USDT per trader
        'leverage': 10,
        'enabled': True,
        'confidence_threshold': 0.6,
        'buy_threshold': 0.65,
        'sell_threshold': 0.65,
        'max_position_pct': 10.0,  # 10% of balance per position
        'default_sl_pct': 2.0,
        'default_tp_pct': 8.0,  # Primary TP at 8%
        'fee_rate': 0.0004,
        'indicator_weights': {}
    }
    
    # Create 10 traders with slight variations
    traders_config = [
        {
            'name': '保守型-低风险',
            'confidence_threshold': 0.65,  # Higher confidence
            'buy_threshold': 0.70,
            'default_sl_pct': 1.5,  # Tighter SL
            'max_position_pct': 8.0,  # Smaller position
        },
        {
            'name': '保守型-标准',
            'confidence_threshold': 0.60,
            'buy_threshold': 0.68,
            'default_sl_pct': 2.0,
            'max_position_pct': 10.0,
        },
        {
            'name': '平衡型-标准A',
            'confidence_threshold': 0.58,
            'buy_threshold': 0.65,
            'default_sl_pct': 2.0,
            'max_position_pct': 10.0,
        },
        {
            'name': '平衡型-标准B',
            'confidence_threshold': 0.60,
            'buy_threshold': 0.63,
            'default_sl_pct': 2.2,
            'max_position_pct': 10.0,
        },
        {
            'name': '平衡型-宽松',
            'confidence_threshold': 0.55,
            'buy_threshold': 0.60,
            'default_sl_pct': 2.5,
            'max_position_pct': 12.0,
        },
        {
            'name': '激进型-标准',
            'confidence_threshold': 0.55,
            'buy_threshold': 0.60,
            'default_sl_pct': 2.5,
            'max_position_pct': 12.0,
        },
        {
            'name': '激进型-高仓位',
            'confidence_threshold': 0.52,
            'buy_threshold': 0.58,
            'default_sl_pct': 3.0,
            'max_position_pct': 15.0,
        },
        {
            'name': '激进型-宽松SL',
            'confidence_threshold': 0.55,
            'buy_threshold': 0.60,
            'default_sl_pct': 3.5,  # Wider SL
            'max_position_pct': 12.0,
        },
        {
            'name': '实验型-低阈值',
            'confidence_threshold': 0.50,  # Very low threshold
            'buy_threshold': 0.55,
            'default_sl_pct': 2.5,
            'max_position_pct': 10.0,
        },
        {
            'name': '实验型-高阈值',
            'confidence_threshold': 0.70,  # Very high threshold
            'buy_threshold': 0.75,
            'default_sl_pct': 2.0,
            'max_position_pct': 10.0,
        },
    ]
    
    created_traders = []
    
    print("🤖 Creating 10 test traders with varying parameters...\n")
    
    for config in traders_config:
        # Merge with base config
        trader_config = {**base_config, **config}
        
        trader = VirtualTrader(
            name=trader_config['name'],
            initial_balance=trader_config['initial_balance'],
            current_balance=trader_config['initial_balance'],
            leverage=trader_config['leverage'],
            enabled=trader_config['enabled'],
            confidence_threshold=trader_config['confidence_threshold'],
            buy_threshold=trader_config['buy_threshold'],
            sell_threshold=trader_config.get('sell_threshold', 0.65),
            max_position_pct=trader_config['max_position_pct'],
            default_sl_pct=trader_config['default_sl_pct'],
            default_tp_pct=trader_config['default_tp_pct'],
            fee_rate=trader_config['fee_rate'],
            indicator_weights=trader_config['indicator_weights']
        )
        
        repo.save_trader(trader)
        created_traders.append(trader)
        
        print(f"✅ {trader.name}")
        print(f"   Balance: ${trader.initial_balance:,.0f}")
        print(f"   Confidence: {trader.confidence_threshold:.2f} | Buy: {trader.buy_threshold:.2f}")
        print(f"   SL: {trader.default_sl_pct:.1f}% | TP: {trader.default_tp_pct:.1f}%")
        print(f"   Max Position: {trader.max_position_pct:.1f}% | Leverage: {trader.leverage}x")
        print()
    
    db.close()
    
    print(f"\n✅ Successfully created {len(created_traders)} traders")
    print(f"💰 Total capital: ${sum(t.initial_balance for t in created_traders):,.0f} USDT")
    print(f"\n📊 Strategy Distribution:")
    print(f"   - 保守型: 2 traders (低风险/标准)")
    print(f"   - 平衡型: 3 traders (标准A/B/宽松)")
    print(f"   - 激进型: 3 traders (标准/高仓位/宽松SL)")
    print(f"   - 实验型: 2 traders (低阈值/高阈值)")
    print(f"\n🎯 All traders are ENABLED and ready for signal processing")
    
    return created_traders


if __name__ == "__main__":
    create_test_traders()

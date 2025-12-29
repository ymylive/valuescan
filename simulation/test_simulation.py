#!/usr/bin/env python3
"""
Simulation Test Script

Tests the virtual trading system by:
1. Starting price updater service
2. Simulating FOMO + Alpha signal aggregation
3. Opening positions for enabled traders
4. Monitoring position updates and exits
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulation import (
    get_simulation_engine,
    start_price_updater,
    stop_price_updater,
    forward_signal_to_simulation,
)
from simulation.trader_repository import TraderRepository
from simulation.database import SimulationDatabase


def test_simulation():
    """Run simulation test with mock signals."""
    
    print("=" * 80)
    print("🚀 VALUESCAN SIMULATION TEST")
    print("=" * 80)
    
    # Initialize
    db = SimulationDatabase('simulation.db')
    repo = TraderRepository(db)
    engine = get_simulation_engine()
    
    # Check traders
    traders = repo.get_enabled_traders()
    print(f"\n📊 Found {len(traders)} enabled traders:")
    for trader in traders:
        print(f"   • {trader.name}: ${trader.current_balance:,.0f}")
    
    if not traders:
        print("❌ No enabled traders found. Run create_test_traders.py first.")
        return
    
    # Start price updater
    print(f"\n⏱️  Starting price updater service (10s interval)...")
    start_price_updater(update_interval=10)
    time.sleep(2)
    
    print("\n" + "=" * 80)
    print("🎯 TEST 1: FOMO + Alpha Signal Aggregation")
    print("=" * 80)
    
    # Simulate FOMO signal for BTC
    print("\n📢 Sending FOMO signal (Type 113) for BTC...")
    forward_signal_to_simulation(
        message_type=113,  # FOMO
        message_id="test_fomo_001",
        symbol="BTC",
        price=50000.0,
        data={'test': True}
    )
    
    time.sleep(2)
    
    # Simulate Alpha signal for BTC (should trigger confluence)
    print("🎯 Sending Alpha signal (Type 110) for BTC...")
    positions_created = forward_signal_to_simulation(
        message_type=110,  # Alpha
        message_id="test_alpha_001",
        symbol="BTC",
        price=50000.0,
        data={'test': True}
    )
    
    print(f"\n✅ Confluence matched! Created {positions_created} positions")
    
    # Check positions
    print("\n📊 Current Open Positions:")
    all_positions = engine.position_manager.get_open_positions()
    
    if all_positions:
        for pos in all_positions:
            trader = repo.get_trader(pos.trader_id)
            print(f"\n   {trader.name}:")
            print(f"   • Symbol: {pos.symbol}")
            print(f"   • Side: {pos.side}")
            print(f"   • Entry: ${pos.entry_price:,.2f}")
            print(f"   • Quantity: {pos.quantity:.4f}")
            print(f"   • TP: ${pos.take_profit:,.2f} | SL: ${pos.stop_loss:,.2f}")
            print(f"   • Pyramiding: {len(pos.pyramiding_levels)} levels")
            print(f"   • Trailing Stop: {'ON' if pos.trailing_stop_enabled else 'OFF'}")
    else:
        print("   No open positions")
    
    print("\n" + "=" * 80)
    print("⏳ Monitoring for 30 seconds...")
    print("   (Price updates every 10s, checking TP/SL/Trailing Stop)")
    print("=" * 80)
    
    # Monitor for 30 seconds
    for i in range(6):
        time.sleep(5)
        
        open_positions = engine.position_manager.get_open_positions()
        total_unrealized_pnl = sum(p.unrealized_pnl for p in open_positions)
        
        print(f"\n⏱️  T+{(i+1)*5}s: {len(open_positions)} open positions, "
              f"Total Unrealized PnL: ${total_unrealized_pnl:.2f}")
        
        # Check for closed trades
        for pos in open_positions:
            if pos.unrealized_pnl != 0:
                trader = repo.get_trader(pos.trader_id)
                print(f"   • {trader.name}: ${pos.unrealized_pnl:+.2f} "
                      f"({pos.symbol} @ ${pos.current_price:,.2f})")
    
    print("\n" + "=" * 80)
    print("🎯 TEST 2: Risk Signal (FOMO Intensify)")
    print("=" * 80)
    
    # Simulate FOMO Intensify signal (should trigger 50% profit taking)
    print("\n⚠️  Sending FOMO Intensify signal (Type 112) for BTC...")
    forward_signal_to_simulation(
        message_type=112,  # FOMO Intensify
        message_id="test_risk_001",
        symbol="BTC",
        price=50000.0,
        data={'test': True}
    )
    
    time.sleep(2)
    
    # Check positions again
    remaining_positions = engine.position_manager.get_open_positions()
    print(f"\n📊 After risk signal: {len(remaining_positions)} positions remaining")
    
    print("\n" + "=" * 80)
    print("📈 FINAL SUMMARY")
    print("=" * 80)
    
    # Get final stats
    for trader in traders:
        # Refresh trader from DB
        trader = repo.get_trader(trader.id)
        trades = engine.position_manager.get_trades(trader.id)
        open_pos = [p for p in engine.position_manager.get_open_positions() if p.trader_id == trader.id]
        
        pnl = trader.current_balance - trader.initial_balance
        pnl_pct = (pnl / trader.initial_balance) * 100
        
        print(f"\n{trader.name}:")
        print(f"   Balance: ${trader.current_balance:,.2f} ({pnl:+.2f}, {pnl_pct:+.2f}%)")
        print(f"   Trades: {len(trades)} | Open Positions: {len(open_pos)}")
        
        if trades:
            total_pnl = sum(t.realized_pnl for t in trades)
            winning = len([t for t in trades if t.realized_pnl > 0])
            print(f"   Realized PnL: ${total_pnl:+.2f} | Win Rate: {winning}/{len(trades)}")
    
    # Stop price updater
    print(f"\n⏹️  Stopping price updater...")
    stop_price_updater()
    
    print("\n✅ Test complete!")
    print("\n💡 To view detailed results, check:")
    print("   - Frontend: http://localhost:3000/simulation")
    print("   - API: http://localhost:5000/api/simulation/traders")
    
    db.close()


if __name__ == "__main__":
    try:
        test_simulation()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        stop_price_updater()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        stop_price_updater()

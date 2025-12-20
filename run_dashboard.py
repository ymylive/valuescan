"""
ValueScan Dashboard Launcher

Starts the Flask API server with:
- Configuration management endpoints
- AI Trading API routes (analysis, learning, strategies, trades, backtest)
- WebSocket support for real-time updates
- Static frontend serving

Requirements: 4.1 - Display real-time AI analysis
"""
import subprocess
import sys
import os
import webbrowser
import time


def check_ai_trading_available():
    """Check if AI trading module is available."""
    try:
        from ai_trading.api.routes import register_blueprints
        return True
    except ImportError:
        return False


def check_frontend_built():
    """Check if frontend is built."""
    dist_path = os.path.join('web', 'dist', 'index.html')
    return os.path.exists(dist_path)


def main():
    """
    Start the ValueScan Dashboard Server.
    
    Includes:
    - REST API for configuration and trading
    - AI Trading API routes for analysis, learning, strategies
    - WebSocket support for real-time updates (Requirements: 4.2)
    - Static frontend serving
    """
    print("🚀 Starting ValueScan Dashboard...")
    print("=" * 50)
    
    # Check AI trading module
    ai_available = check_ai_trading_available()
    if ai_available:
        print("✅ AI Trading module: Available")
        print("   - AI Analysis endpoints: /api/ai/*")
        print("   - Learning endpoints: /api/learning/*")
        print("   - Strategy endpoints: /api/strategies/*")
        print("   - Trade endpoints: /api/trades/*")
        print("   - Backtest endpoints: /api/backtest/*")
    else:
        print("⚠️  AI Trading module: Not available")
        print("   (Core dashboard features still work)")
    
    # Check frontend
    if check_frontend_built():
        print("✅ Frontend: Built and ready")
    else:
        print("⚠️  Frontend: Not built (run 'npm run build' in web/)")
    
    print("=" * 50)
    
    # Path to server.py
    server_path = os.path.join('api', 'server.py')
    
    if not os.path.exists(server_path):
        print(f"❌ Error: {server_path} not found!")
        return
    
    # Start the Flask server with SocketIO support
    try:
        process = subprocess.Popen([sys.executable, server_path])
        
        print("✅ Server started on http://localhost:5000")
        print("   WebSocket enabled for real-time updates")
        print("⏳ Waiting for server to initialize...")
        time.sleep(2)
        
        # Open browser
        webbrowser.open('http://localhost:5000')
        
        print("\n📊 Dashboard is ready!")
        print("Press Ctrl+C to stop the server")
        process.wait()
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping server...")
        process.terminate()
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == '__main__':
    main()

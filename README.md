<p align="center">
  <img src="screenshots/logo.png" alt="ValueScan Logo" width="120" />
</p>

<h1 align="center">ValueScan</h1>

<p align="center">
  <strong>🚀 AI-Powered Crypto Signal Monitor & Autonomous Trading System</strong>
</p>

<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/lang-English-blue?style=for-the-badge" alt="English" /></a>
  <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/lang-简体中文-red?style=for-the-badge" alt="简体中文" /></a>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#ai-trading-system">AI Trading</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#deployment">Deployment</a> •
  <a href="#documentation">Documentation</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Go-1.21+-00ADD8?style=flat-square&logo=go" alt="Go Version" />
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python" alt="Python Version" />
  <img src="https://img.shields.io/badge/React-18+-61DAFB?style=flat-square&logo=react" alt="React" />
  <img src="https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=flat-square&logo=typescript" alt="TypeScript" />
  <img src="https://img.shields.io/badge/License-AGPL--3.0-blue?style=flat-square" alt="License" />
</p>

---

## 📖 Overview

**ValueScan** is a comprehensive cryptocurrency trading platform that combines real-time signal monitoring, AI-powered market analysis, and **fully autonomous AI trading**. Built with a microservices architecture using Go for high-performance backend, Python for AI integrations, and React for a modern web interface.

### 🎯 Key Capabilities

| Module | Description |
|--------|-------------|
| **🤖 AI Trading System** | **NEW!** Autonomous AI-powered trading with self-learning and strategy evolution |
| **📡 Signal Monitor** | Real-time monitoring of trading signals from ValueScan API with Telegram notifications |
| **🧠 AI Market Summary** | Automated market analysis using GPT/Claude with 6-dimension quantitative analysis |
| **💹 Auto Trader** | Binance Futures trading bot with pyramiding, trailing stop, and risk management |
| **📋 Telegram Copytrade** | Copy trades from Telegram signal channels to your exchange account |
| **🔄 Keepalive System** | Health monitoring and auto-restart for all services |
| **📊 Simulation Mode** | Paper trading with virtual balance for strategy testing |

---

## ✨ Features

### 🤖 AI Trading System (NEW!)

**Complete autonomous trading powered by AI with self-learning capabilities**

#### Core Features:
- **AI Mode**: Full AI control with manual strategies disabled
- **Coin Blacklist**: Exclude specific coins from trading
- **AI Position Agent**: Autonomous position management
  - Analyzes positions every 5 minutes
  - AI decides: hold / add / reduce / close
  - Considers entry price, current price, PnL, stop-loss, take-profit
- **Performance Tracking**: SQLite database tracking all AI trades
  - Complete trade history with AI analysis
  - Position action logs
  - Learning session records
- **AI Evolution Engine**: Self-learning system that optimizes strategies
  - Analyzes trading patterns automatically
  - Generates optimization suggestions via AI
  - A/B testing for new strategies
  - Configurable evolution interval (default: 24 hours)

#### Strategy Profiles (6 Options):

| Strategy | Risk | Profit Potential | Frequency | Holding Time | Best For |
|----------|------|------------------|-----------|--------------|----------|
| **Conservative Scalping** | ⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | 1-5 min | Conservative short-term |
| **Conservative Swing** | ⭐ | ⭐⭐⭐ | ⭐⭐ | 2-10 days | Conservative mid-term |
| **Balanced Day** ⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | 1-8 hours | **Recommended** |
| **Balanced Swing** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | 2-10 days | Working professionals |
| **Aggressive Scalping** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 1-5 min | Professional traders |
| **Aggressive Day** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 1-8 hours | Aggressive traders |

**Quick Start**:
```python
# binance_trader/config.py
ENABLE_AI_MODE = True
ENABLE_AI_POSITION_AGENT = True
ENABLE_AI_EVOLUTION = True
AI_EVOLUTION_PROFILE = "balanced_day"  # Recommended
```

📚 **Documentation**: [AI Trading System Guide](AI_TRADING_SYSTEM.md)

---

### 📡 Signal Monitoring
- Real-time polling of ValueScan trading signals
- Multi-channel Telegram notifications with TradingView charts
- Signal filtering by type (Bullish, Bearish, Arbitrage, Whale)
- Duplicate detection and smart message formatting
- Movement list tracking (Alpha & FOMO coins)
- **AI Signal Forwarding**: Automatically forwards AI analysis to trading system

### 🧠 AI Market Summary
- Hourly AI-generated market analysis sent to Telegram
- **6-Dimension Analysis**:
  1. Market Sentiment
  2. Capital Flow
  3. Technical Signals
  4. Whale Activity
  5. News Impact
  6. Risk Assessment
- Integration with multiple data sources:
  - **ValueScan Signals** - Trading signal statistics
  - **NOFX Quantitative API** - Netflow, Open Interest, Price data
  - **CryptoCompare** - Crypto news headlines
  - **CoinGecko** - Trending coins and market data
- Support for OpenAI, Claude, DeepSeek, and compatible APIs

### 💹 Automated Trading
- **Binance Futures** support with USDT-M perpetual contracts
- Pyramiding entry with configurable position levels
- Dynamic trailing stop with activation thresholds
- Take profit levels (TP1, TP2, TP3) with partial close
- Stop loss with margin ratio monitoring
- Position size management based on account balance
- **AI Mode Integration**: Seamless integration with AI trading system

### 🔄 Telegram Copytrade
- Monitor Telegram groups/channels for trading signals
- Automatic signal parsing and trade execution
- Position management with configurable leverage
- Blacklist/whitelist symbol filtering

### 📊 Web Dashboard
- Real-time signal display and statistics
- Service status monitoring (Start/Stop/Restart)
- Configuration management with visual editor
- **AI Trading Configuration**: Dedicated "AI 交易" tab
  - AI Mode settings
  - Position Agent configuration
  - Evolution System settings
  - Strategy Profile selector
  - Learning parameters
  - A/B Testing options
- Log viewer with filtering capabilities
- Multi-language support (EN/中文/日本語)

---

## 🏗 Architecture

```
valuescan/
├── api/                    # REST API server (Python Flask)
│   ├── server.py           # Main API endpoints
│   └── metrics_calculator.py
│
├── signal_monitor/         # Signal monitoring module (Python)
│   ├── polling_monitor.py  # Main polling loop
│   ├── message_handler.py  # Signal processing
│   ├── telegram.py         # Telegram integration
│   ├── ai_market_summary.py # AI summary generation
│   ├── ai_signal_forwarder.py # NEW: AI signal forwarding
│   └── database.py         # SQLite storage
│
├── binance_trader/         # Trading bot (Python)
│   ├── futures_main.py     # Main trading loop with AI integration
│   ├── futures_trader.py   # Order execution
│   ├── signal_aggregator.py # Signal fusion
│   ├── trailing_stop.py    # Trailing stop logic
│   ├── risk_manager.py     # Risk management
│   │
│   └── AI Trading System (NEW):
│       ├── ai_mode_handler.py        # AI mode signal processing
│       ├── ai_position_agent.py      # AI position management
│       ├── ai_performance_tracker.py # Performance tracking
│       ├── ai_evolution_engine.py    # Self-learning engine
│       └── ai_evolution_profiles.py  # Strategy profiles
│
├── keepalive/              # Health monitoring (Python)
│   ├── health.py           # Service health checks
│   └── alerter.py          # Alert notifications
│
├── simulation/             # Paper trading (Python)
│   ├── simulator.py        # Trade simulation
│   └── api_routes.py       # Simulation API
│
├── telegram_copytrade/     # Copytrade module (Python)
│   └── copytrade_main.py   # Telegram listener
│
├── web/                    # Frontend (React + TypeScript)
│   ├── src/
│   │   ├── components/     # UI components
│   │   │   └── valuescan/
│   │   │       └── AITradingConfigSection.tsx # NEW: AI config UI
│   │   ├── pages/          # Page views
│   │   │   └── SettingsPage.tsx # Updated with AI tab
│   │   └── lib/            # API client & utilities
│   └── dist/               # Production build
│
├── provider/               # Data providers (Go)
│   └── coinank/            # CoinAnk API client
│
├── trader/                 # Go trading modules
├── backtest/               # Backtesting engine
├── mcp/                    # MCP (Model Context Protocol)
└── scripts/                # Utility scripts
    └── deploy_ai_trading_system.py # NEW: AI system deployment
```

### Data Flow

```
1. Signal Flow:
   ValueScan API → polling_monitor → message_handler → Telegram + Database + IPC

2. AI Trading Flow:
   AI Signal Analysis → ai_signal_forwarder → IPC → ai_mode_handler → futures_trader → Binance

3. AI Evolution Flow:
   Trading Data → ai_performance_tracker → ai_evolution_engine → Strategy Optimization → A/B Testing

4. AI Summary Flow:
   Multiple APIs → ai_market_summary → Telegram

5. Web Dashboard:
   React Frontend → Flask API → Python Services
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** with pip
- **Node.js 18+** with npm
- **Go 1.21+** (optional, for Go modules)
- **Telegram Bot Token** (for notifications)
- **Binance API Keys** (for trading)
- **AI API Key** (OpenAI/Claude/DeepSeek for AI features)

### Installation

```bash
# Clone the repository
git clone https://github.com/ymylive/valuescan.git
cd valuescan

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd web && npm install && cd ..

# Copy environment configuration
cp .env.example .env
```

### Configuration

Edit `.env` and configure:

```bash
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# ValueScan API (required for signal monitoring)
VALUESCAN_API_URL=https://api.valuescan.io

# Binance API (required for trading)
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret

# AI API (required for AI features)
AI_API_KEY=your_openai_or_claude_key
AI_API_URL=https://api.openai.com/v1/chat/completions
AI_MODEL=gpt-4o-mini
```

### Configure AI Trading System

```bash
# Copy example config
cd binance_trader
cp config.example.py config.py

# Edit config.py and enable AI features
nano config.py
```

**Essential AI Configuration**:
```python
# AI Mode
ENABLE_AI_MODE = True
COIN_BLACKLIST = ["DOGE", "SHIB"]  # Optional

# AI Position Agent
ENABLE_AI_POSITION_AGENT = True
AI_POSITION_CHECK_INTERVAL = 300  # 5 minutes

# AI Evolution
ENABLE_AI_EVOLUTION = True
AI_EVOLUTION_PROFILE = "balanced_day"  # Recommended
AI_EVOLUTION_MIN_TRADES = 50
AI_EVOLUTION_LEARNING_PERIOD_DAYS = 30
AI_EVOLUTION_INTERVAL_HOURS = 24
ENABLE_AI_AB_TESTING = True
AI_AB_TEST_RATIO = 0.2  # 20% test ratio
```

### Start Services

```bash
# Start API server
python -m api.server

# Start signal monitor (with AI signal forwarding)
python -m signal_monitor.polling_monitor

# Start AI trading bot
python -m binance_trader.futures_main

# Start web frontend
cd web && npm run dev
```

Access the dashboard at **http://localhost:3000**

### Verify AI System

```bash
# Check logs for AI system initialization
tail -f logs/trader.log | grep -E "AI|🤖|🧬"

# Expected output:
# 🤖 AI 模式已启用
# 🤖 AI 仓位代理已启用
# 🧬 AI 进化系统已启用
# 🧬 进化策略: balanced_day
```

---

## ⚙️ Configuration

### AI Trading System Config

| Option | Description | Default |
|--------|-------------|---------|
| `ENABLE_AI_MODE` | Enable full AI control | `False` |
| `COIN_BLACKLIST` | Coins to exclude from trading | `[]` |
| `ENABLE_AI_POSITION_AGENT` | Enable AI position management | `False` |
| `AI_POSITION_CHECK_INTERVAL` | Position check interval (seconds) | `300` |
| `ENABLE_AI_EVOLUTION` | Enable self-learning system | `False` |
| `AI_EVOLUTION_PROFILE` | Strategy profile | `"balanced_day"` |
| `AI_EVOLUTION_MIN_TRADES` | Min trades before learning | `50` |
| `AI_EVOLUTION_LEARNING_PERIOD_DAYS` | Learning period | `30` |
| `AI_EVOLUTION_INTERVAL_HOURS` | Evolution interval | `24` |
| `ENABLE_AI_AB_TESTING` | Enable A/B testing | `True` |
| `AI_AB_TEST_RATIO` | Test ratio (0-1) | `0.2` |

### Signal Monitor Config

| Option | Description | Default |
|--------|-------------|---------|
| `telegram_bot_token` | Telegram Bot API token | Required |
| `telegram_chat_id` | Target chat/channel ID | Required |
| `enable_telegram` | Enable Telegram notifications | `true` |
| `chrome_debug_port` | Chrome DevTools port for screenshots | `9222` |
| `enable_tradingview_chart` | Include TradingView charts | `true` |

### AI Summary Config

| Option | Description | Default |
|--------|-------------|---------|
| `enabled` | Enable AI market summaries | `false` |
| `api_key` | OpenAI/Claude API key | Required |
| `api_url` | API endpoint URL | OpenAI |
| `model` | Model name | `gpt-4o-mini` |
| `interval_hours` | Summary interval | `1` |
| `lookback_hours` | Data lookback period | `1` |

### Trader Config

| Option | Description | Default |
|--------|-------------|---------|
| `leverage` | Trading leverage | `10` |
| `max_position_percent` | Max position as % of balance | `10` |
| `stop_loss_percent` | Stop loss percentage | `5` |
| `take_profit_1_percent` | First take profit level | `3` |
| `trailing_stop_activation` | Trailing stop activation % | `2` |
| `trailing_stop_callback` | Trailing stop callback % | `1` |

---

## 📡 API Reference

### AI Trading API

```http
GET  /api/ai/performance?days=7        # Get AI performance stats
GET  /api/ai/evolution/history         # Get evolution history
GET  /api/ai/evolution/config          # Get evolution config
POST /api/ai/evolution/trigger         # Manually trigger evolution
```

### Signal Monitor API

```http
GET  /api/config                      # Get all configuration
POST /api/config                      # Save configuration

GET  /api/signals?limit=10            # Get recent signals
GET  /api/alerts?limit=10             # Get recent alerts

GET  /api/valuescan/status            # Service status
POST /api/valuescan/signal/start      # Start signal monitor
POST /api/valuescan/signal/stop       # Stop signal monitor
```

### AI Summary API

```http
GET  /api/valuescan/ai-summary/config     # Get AI summary config
POST /api/valuescan/ai-summary/config     # Save AI summary config
POST /api/valuescan/ai-summary/trigger    # Manually trigger summary
```

### Trader API

```http
GET  /api/trader/positions            # Get open positions
GET  /api/trader/balance              # Get account balance
POST /api/trader/start                # Start trading bot
POST /api/trader/stop                 # Stop trading bot
```

---

## 🚢 Deployment

### Quick Deployment (VPS)

```bash
# Deploy AI trading system to VPS
python scripts/deploy_ai_trading_system.py

# Configure on VPS
ssh root@your-vps.com
cd /root/valuescan/binance_trader
cp config.example.py config.py
nano config.py  # Set ENABLE_AI_MODE=True, etc.

# Restart services
systemctl restart valuescan-signal
systemctl restart valuescan-trader
systemctl restart valuescan-api

# Verify
journalctl -u valuescan-trader -f | grep -E "AI|🤖|🧬"
```

### Systemd Services

```bash
# Copy service files
sudo cp valuescan-*.service /etc/systemd/system/

# Enable and start services
sudo systemctl enable valuescan-api valuescan-signal valuescan-trader
sudo systemctl start valuescan-api valuescan-signal valuescan-trader

# Check status
sudo systemctl status valuescan-trader
```

### Docker Deployment

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Nginx Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    root /var/www/valuescan;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

---

## 📚 Documentation

### AI Trading System
- [AI Trading System Overview](AI_TRADING_SYSTEM.md) - Complete system architecture
- [AI Evolution System](AI_EVOLUTION_SYSTEM.md) - Self-learning engine details
- [AI Evolution Strategies](AI_EVOLUTION_STRATEGIES.md) - Strategy configuration guide
- [VPS Deployment Guide](AI_TRADING_VPS_DEPLOYMENT.md) - Complete deployment instructions
- [Deployment Checklist](AI_TRADING_DEPLOYMENT_CHECKLIST.md) - Step-by-step checklist
- [Quick Start Guide](AI_TRADING_QUICK_START.md) - Fast setup guide
- [Implementation Summary](AI_TRADING_IMPLEMENTATION_SUMMARY.md) - Technical details

### General
- [CLAUDE.md](CLAUDE.md) - Project overview and development guide
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines

---

## 📁 Project Structure

| Directory | Language | Description |
|-----------|----------|-------------|
| `api/` | Python | REST API server with Flask |
| `signal_monitor/` | Python | Signal polling and processing |
| `binance_trader/` | Python | Binance Futures trading bot with AI |
| `keepalive/` | Python | Service health monitoring |
| `simulation/` | Python | Paper trading simulator |
| `telegram_copytrade/` | Python | Telegram signal copier |
| `web/` | TypeScript/React | Web dashboard frontend |
| `provider/` | Go | External data providers |
| `trader/` | Go | High-performance trading |
| `backtest/` | Go | Strategy backtesting |
| `mcp/` | Go | Model Context Protocol |
| `scripts/` | Python | Utility and deployment scripts |

---

## 🗄️ Database Schema

### AI Performance Database (`ai_performance.db`)

**ai_trades** - Complete AI trade history
```sql
trade_id, symbol, direction, entry_time, entry_price, entry_quantity,
ai_analysis, ai_confidence, ai_stop_loss, ai_take_profit, ai_risk_level,
exit_time, exit_price, exit_quantity, exit_reason,
realized_pnl, realized_pnl_percent, market_conditions, status
```

**ai_position_actions** - Position management actions
```sql
action_id, trade_id, action_time, action_type, ai_reason, ai_confidence,
quantity_before, quantity_after, price, market_conditions
```

**ai_learning_sessions** - Evolution history
```sql
session_id, start_time, end_time, trades_analyzed, patterns_discovered,
insights, old_parameters, new_parameters, expected_improvement,
actual_improvement, validation_period_days, status
```

---

## 🔐 Security

- **API Keys**: Store in environment variables or `.env` file (never commit)
- **Telegram**: Use bot tokens with restricted permissions
- **Exchange**: Enable IP whitelist and withdrawal restrictions
- **Proxy**: Support for SOCKS5/HTTP proxy for restricted regions
- **AI Data**: Performance database is stored locally with restricted permissions

---

## 📊 Data Sources

| Source | Data Type | Usage |
|--------|-----------|-------|
| **ValueScan API** | Trading signals | Signal monitoring |
| **NOFX API** | Netflow, OI, Price | AI market summary |
| **CryptoCompare** | News headlines | AI market summary |
| **CoinGecko** | Trending coins | AI market summary |
| **Binance API** | Market data, trading | Auto trading |
| **OpenAI/Claude** | AI analysis | AI trading & summaries |

---

## 🎯 Use Cases

### 1. Autonomous AI Trading
```python
# Set and forget - AI handles everything
ENABLE_AI_MODE = True
ENABLE_AI_POSITION_AGENT = True
ENABLE_AI_EVOLUTION = True
AI_EVOLUTION_PROFILE = "balanced_day"
```

### 2. Signal Monitoring Only
```python
# Just monitor signals, no trading
ENABLE_AI_MODE = False
# Configure signal_monitor only
```

### 3. Manual Trading with AI Assistance
```python
# AI provides analysis, you decide
ENABLE_AI_MODE = False
# Use AI signals as reference
```

### 4. Paper Trading with AI
```python
# Test AI strategies without risk
# Use simulation mode
```

---

## 📈 Performance Monitoring

### View AI Performance

```bash
# Via logs
journalctl -u valuescan-trader -f | grep "AI 性能"

# Via Python
cd binance_trader
python3 -c "
from ai_performance_tracker import AIPerformanceTracker
tracker = AIPerformanceTracker()
stats = tracker.get_performance_stats(days=7)
print(f'Win Rate: {stats[\"win_rate\"]:.2f}%')
print(f'Total PnL: {stats[\"total_pnl\"]:.2f}')
"
```

### View Evolution History

```bash
cd binance_trader
cat data/ai_evolution_config.json | python3 -m json.tool
```

### Database Queries

```bash
# Check trade count
sqlite3 data/ai_performance.db "SELECT COUNT(*) FROM ai_trades;"

# View recent trades
sqlite3 data/ai_performance.db "SELECT * FROM ai_trades ORDER BY entry_time DESC LIMIT 10;"
```

---

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details on:

- Code style and conventions
- Pull request process
- Issue reporting
- AI system development guidelines

---

## 📄 License

This project is licensed under **GNU AGPL-3.0** - see the [LICENSE](LICENSE) file for details.

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/ymylive/valuescan/issues)
- **Telegram**: [Developer Community](https://t.me/valuescan_dev)
- **Documentation**: See [Documentation](#documentation) section above

---

## 🙏 Acknowledgments

- **OpenAI/Anthropic** - AI model providers
- **Binance** - Exchange API
- **ValueScan** - Signal data provider
- **NOFX** - Quantitative data provider
- **Community Contributors** - Thank you for your support!

---

## 🗺️ Roadmap

- [x] Real-time signal monitoring
- [x] AI market summary
- [x] Automated trading
- [x] **AI autonomous trading system**
- [x] **AI self-learning and evolution**
- [x] **6 strategy profiles**
- [ ] Multi-exchange support
- [ ] Advanced backtesting
- [ ] Mobile app
- [ ] Strategy marketplace
- [ ] Social trading features

---

<p align="center">
  <strong>Made with ❤️ by the ValueScan Team</strong>
</p>

<p align="center">
  <sub>⭐ Star us on GitHub if you find this project useful!</sub>
</p>

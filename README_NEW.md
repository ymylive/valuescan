<p align="center">
  <img src="screenshots/logo.png" alt="ValueScan Logo" width="120" />
</p>

<h1 align="center">ValueScan</h1>

<p align="center">
  <strong>🚀 AI-Powered Crypto Signal Monitor & Automated Trading System</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#api-reference">API</a> •
  <a href="#deployment">Deployment</a>
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

**ValueScan** is a comprehensive cryptocurrency trading platform that combines real-time signal monitoring, AI-powered market analysis, and automated trading execution. Built with a microservices architecture using Go for high-performance backend, Python for AI integrations, and React for a modern web interface.

### 🎯 Key Capabilities

| Module | Description |
|--------|-------------|
| **Signal Monitor** | Real-time monitoring of trading signals from ValueScan API with Telegram notifications |
| **AI Market Summary** | Automated market analysis using GPT/Claude with quantitative data from NOFX API |
| **Auto Trader** | Binance Futures trading bot with pyramiding, trailing stop, and risk management |
| **Telegram Copytrade** | Copy trades from Telegram signal channels to your exchange account |
| **Keepalive System** | Health monitoring and auto-restart for all services |
| **Simulation Mode** | Paper trading with virtual balance for strategy testing |

---

## ✨ Features

### 📡 Signal Monitoring
- Real-time polling of ValueScan trading signals
- Multi-channel Telegram notifications with TradingView charts
- Signal filtering by type (Bullish, Bearish, Arbitrage, Whale)
- Duplicate detection and smart message formatting
- Movement list tracking (Alpha & FOMO coins)

### 🤖 AI Market Summary
- Hourly AI-generated market analysis sent to Telegram
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

### 🔄 Telegram Copytrade
- Monitor Telegram groups/channels for trading signals
- Automatic signal parsing and trade execution
- Position management with configurable leverage
- Blacklist/whitelist symbol filtering

### 📊 Web Dashboard
- Real-time signal display and statistics
- Service status monitoring (Start/Stop/Restart)
- Configuration management with visual editor
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
│   └── database.py         # SQLite storage
│
├── binance_trader/         # Trading bot (Python)
│   ├── trade_executor.py   # Order execution
│   ├── position_manager.py # Position tracking
│   └── signal_processor.py # Signal handling
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
│   │   ├── pages/          # Page views
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
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** with pip
- **Node.js 18+** with npm
- **Go 1.21+** (optional, for Go modules)
- **Telegram Bot Token** (for notifications)

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

# AI Summary (optional)
AI_SUMMARY_API_KEY=your_openai_key
AI_SUMMARY_API_URL=https://api.openai.com/v1/chat/completions
```

### Start Services

```bash
# Start API server
python -m api.server

# Start signal monitor
python -m signal_monitor.polling_monitor

# Start web frontend
cd web && npm run dev

# Start trader (optional)
python -m binance_trader.trade_executor
```

Access the dashboard at **http://localhost:3000**

---

## ⚙️ Configuration

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

### Systemd Services

```bash
# Copy service files
sudo cp valuescan-*.service /etc/systemd/system/

# Enable and start services
sudo systemctl enable valuescan-api valuescan-signal
sudo systemctl start valuescan-api valuescan-signal

# Check status
sudo systemctl status valuescan-api
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

## 📁 Project Structure

| Directory | Language | Description |
|-----------|----------|-------------|
| `api/` | Python | REST API server with Flask |
| `signal_monitor/` | Python | Signal polling and processing |
| `binance_trader/` | Python | Binance Futures trading bot |
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

## 🔐 Security

- **API Keys**: Store in environment variables or `.env` file
- **Telegram**: Use bot tokens with restricted permissions
- **Exchange**: Enable IP whitelist and withdrawal restrictions
- **Proxy**: Support for SOCKS5/HTTP proxy for restricted regions

---

## 📊 Data Sources

| Source | Data Type | Usage |
|--------|-----------|-------|
| **ValueScan API** | Trading signals | Signal monitoring |
| **NOFX API** | Netflow, OI, Price | AI market summary |
| **CryptoCompare** | News headlines | AI market summary |
| **CoinGecko** | Trending coins | AI market summary |
| **Binance API** | Market data, trading | Auto trading |

---

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details on:

- Code style and conventions
- Pull request process
- Issue reporting

---

## 📄 License

This project is licensed under **GNU AGPL-3.0** - see the [LICENSE](LICENSE) file for details.

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/ymylive/valuescan/issues)
- **Telegram**: [Developer Community](https://t.me/valuescan_dev)

---

<p align="center">
  Made with ❤️ by the ValueScan Team
</p>

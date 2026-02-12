# ValuScan QuantRefactorV3 - Baseline Architecture

## Project Overview

ValuScan is a market monitoring system for crypto and metals (BTC, ETH, XAU, XAG) with:
- Anomaly detection (异动监测)
- AI-powered market analysis
- Multi-source data aggregation
- Telegram bot integration
- Web frontend for configuration

---

## Current Directory Structure

```
E:/project/valuescan/
├── signal_monitor/          # Core monitoring logic (Python)
│   ├── anomaly_detector/    # Anomaly detection engine
│   │   ├── engine.py        # Main detection engine
│   │   ├── detector.py      # Signal detector with scoring
│   │   ├── config.py        # Configuration
│   │   └── features/        # Feature extraction modules
│   │       ├── technical_indicators.py
│   │       ├── volume_price.py
│   │       ├── correlation.py
│   │       └── ...
│   ├── ai_signal_analysis.py    # AI prompt builder for signals
│   ├── ai_market_analysis.py    # AI market analysis
│   ├── ai_market_summary.py     # AI market summary
│   ├── btc_forecast.py          # BTC forecast (TO BE REMOVED)
│   ├── stock_forecast.py        # Stock forecast (TO BE REMOVED)
│   ├── fundamentals_sources.py  # Data sources (needs Jin10)
│   ├── market_data_sources.py   # Market data aggregation
│   ├── macro_data.py            # Macro economic data
│   └── ...
├── web/                     # Frontend (React + TypeScript + Vite)
│   ├── src/
│   │   ├── features/
│   │   │   └── configuration/
│   │   ├── services/
│   │   ├── types/
│   │   └── utils/
│   └── ...                  # TO BE REMOVED (old frontend)
├── api/                     # API server (Python + Go)
│   └── server.py
├── docs/                    # Documentation
├── docker/                  # Docker configs
└── ...
```

---

## Critical Files Identified

### Anomaly Detection
- `signal_monitor/anomaly_detector/engine.py` - Main detection engine
- `signal_monitor/anomaly_detector/detector.py` - Signal detector with scoring
- `signal_monitor/anomaly_detector/features/` - Feature extraction modules

### AI Integration
- `signal_monitor/ai_signal_analysis.py` - Main AI prompt builder
- `signal_monitor/ai_market_analysis.py` - AI market analysis
- `signal_monitor/ai_api_utils.py` - AI API utilities
- `signal_monitor/ai_request_queue.py` - AI request queue

### Data Sources
- `signal_monitor/fundamentals_sources.py` - Fundamental data (needs Jin10 integration)
- `signal_monitor/market_data_sources.py` - Market data aggregation
- `signal_monitor/macro_data.py` - Macro economic data

### Forecast Modules (TO BE REMOVED)
- `signal_monitor/btc_forecast.py` - BTC forecast
- `signal_monitor/stock_forecast.py` - Stock forecast

### Frontend (TO BE REMOVED)
- `web/` - Entire frontend directory

---

## Current Data Flow

1. **Data Collection**
   - Market data: Binance, CoinGecko, CryptoCompare
   - Fundamentals: Forex Factory, FRED, CoinGecko
   - Macro: Economic calendars, news sources

2. **Anomaly Detection**
   - Engine fetches OHLCV data (1h, 50 candles)
   - Detector calculates features (volume, price, derivatives)
   - Signals generated based on thresholds
   - Signals sent to Telegram bot

3. **AI Analysis**
   - AI prompt builder constructs context
   - LLM generates market analysis
   - Output sent to Telegram

4. **Forecast (TO BE REMOVED)**
   - BTC/stock forecast using AI
   - Prediction outputs

---

## Current Issues & Refactoring Needs

### 1. Bloat
- Old frontend (`web/`) no longer needed
- Prediction/forecast features (`btc_forecast.py`, `stock_forecast.py`) no longer needed

### 2. Naming Inconsistency
- Terminology is now consistent: "异动监测" everywhere
- Variable names, API paths, function names need global rename

### 3. Anomaly Detection Accuracy
- Current detector uses simple z-score (std dev based)
- Needs upgrade to robust z-score (MAD based)
- Only 15m and 1h timeframes should be supported
- Need better anomaly classification (PUMP/DUMP/VOLUME_SPIKE/etc.)

### 4. Missing Fundamentals
- No Jin10 news integration
- Economic data interpretation needs improvement
- News summarization not structured

### 5. AI Output Issues
- Contains unreliable "confidence scores"
- Lacks structure (no dual-track futures/spot plans)
- No disclaimer
- Prompt templates not externalized

### 6. Missing Management UI
- No admin console to control system
- No way to trigger tasks manually
- No real-time log viewing
- No config management UI

---

## Refactoring Strategy

### Phase 1: Baseline & Architecture ✓
- Document current state
- Define SCHEMAS_V3
- Identify critical files

### Phase 2: Removal & Cleanup
- Remove old frontend (`web/`)
- Remove forecast features
- Terminology standardized to "异动监测"
- Remove confidence/probability fields

### Phase 3: Anomaly Detection v2
- Implement robust z-score (MAD based)
- Add amplitude/ATR normalization
- Improve anomaly classification
- Support 15m and 1h only

### Phase 4: Fundamentals Integration
- Add Jin10 news integration
- Implement news summarization
- Enhance economic data interpretation

### Phase 5: Macro Features & Levels
- Multi-timeframe feature engineering (200K validation)
- Support/resistance level detection
- Multi-timeframe merge

### Phase 6: AI Module Refactor
- Externalize prompt templates
- Implement strict JSON parser with schema validation
- Remove confidence fields
- Add dual-track (futures + spot) outputs
- Add disclaimer

### Phase 7: Admin Backend API
- Control API (start/stop/trigger)
- Config API (get/update with validation)
- Logs API (query/stream)
- Health API (system status)

### Phase 8: New Admin Frontend
- Black/white theme with Asia/Singapore auto-switching
- Dashboard, Controls, Params, Logs, Data Sources pages
- Connect to Phase 7 backend APIs

### Phase 9: End-to-End QA
- Regression testing
- Snapshot testing
- Sample outputs generation
- Build/run verification

---

## Technology Stack

### Backend
- **Language**: Python 3.x
- **Data Sources**: Binance, CoinGecko, CryptoCompare, Forex Factory, FRED
- **AI**: OpenAI/Anthropic/Custom LLM APIs
- **Messaging**: Telegram Bot API
- **Storage**: JSON files, SQLite (if used)

### Frontend (Current - TO BE REMOVED)
- **Framework**: React + TypeScript + Vite
- **Styling**: Tailwind CSS
- **State**: React hooks

### Frontend (New Admin - TO BE BUILT)
- **Framework**: Vite + React + TypeScript
- **Styling**: Tailwind CSS
- **Theme**: Black/white with Asia/Singapore timezone auto-switching

### API
- **Python**: Flask/FastAPI (to be determined)
- **Go**: Gin (for proxy management)

---

## Dependencies

### Python (signal_monitor/requirements.txt)
- requests
- ccxt (crypto exchange library)
- pandas (data manipulation)
- numpy (numerical computing)
- Other dependencies TBD

### Node.js (web/package.json)
- React
- TypeScript
- Vite
- Tailwind CSS
- Other dependencies TBD

---

## Configuration

### Signal Monitor Config
- `signal_monitor/config.py` - Main configuration
- `signal_monitor/anomaly_config.json` - Anomaly detection config
- `signal_monitor/ai_signal_config.json` - AI signal config
- Various other JSON configs

### Environment Variables
- `NOFX_PROXY` - Proxy settings
- `NOFX_ANOMALY_DEDUP_SECONDS` - Deduplication window
- AI API keys and endpoints
- Telegram bot tokens

---

## API Endpoints (Current)

### Existing APIs (to be documented)
- Proxy management (Go)
- Config management (Python)
- Market data endpoints
- Signal endpoints

### New APIs (Phase 7)
- Control API: `/api/control/*`
- Config API: `/api/config`
- Logs API: `/api/logs`
- Health API: `/api/health`
- Fundamentals API: `/api/fundamentals/*`

---

## Data Sources

### Market Data
- **Binance**: OHLCV, funding rates, open interest
- **CoinGecko**: Price, market cap, volume
- **CryptoCompare**: Historical data, social metrics

### Fundamentals
- **Forex Factory**: Economic calendar
- **FRED**: Economic indicators
- **Jin10** (TO BE ADDED): Real-time financial news

### Sentiment
- **Fear & Greed Index**: Market sentiment
- **Social metrics**: Twitter, Reddit (if used)

---

## Deployment

### Current Deployment
- VPS deployment scripts: `deploy_*.py`, `deploy_*.bat`
- Docker support: `Dockerfile.backend`, `Dockerfile.frontend`
- Systemd services: `valuescan-*.service`

### Deployment Strategy
- Backend: Python service on VPS
- Frontend (new admin): Static files served by nginx
- Telegram bot: Integrated with backend

---

## Testing Strategy

### Unit Tests
- Anomaly detection algorithms
- Feature extraction
- Data source integrations

### Integration Tests
- API endpoints
- Data pipeline
- AI integration

### End-to-End Tests
- Full workflow from data collection to signal generation
- Admin UI interactions

---

## Security Considerations

### Current
- API keys in environment variables
- Proxy support for external requests

### To Be Added
- Admin UI authentication (if needed)
- Rate limiting for AI APIs
- Input validation for config updates
- Secure storage of sensitive data

---

## Performance Considerations

### Current
- Caching for data sources (TTL based)
- Deduplication for signals (5-minute window)
- Request queue for AI calls

### To Be Improved
- Multi-timeframe data validation (200K requirement)
- Efficient level detection algorithms
- Real-time log streaming optimization

---

## Next Steps

1. Complete Phase 2: Removal & Cleanup
2. Implement Phase 3: Anomaly Detection v2
3. Continue with remaining phases sequentially
4. Maintain documentation throughout

---

## References

- SCHEMAS_V3.md - Data contracts and API schemas
- Implementation plan - Detailed phase-by-phase tasks
- Project memory - Key patterns and conventions

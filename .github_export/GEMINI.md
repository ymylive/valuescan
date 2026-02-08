# NOFX - Agentic Trading OS

## Project Overview

NOFX is an open-source AI trading system designed to orchestrate multiple AI models (DeepSeek, GPT, Claude, etc.) for automated crypto futures trading. It features a strategy studio, backtesting lab, and a "debate arena" where different AI personas compete to form trading decisions.

**Key Technologies:**
*   **Backend:** Go (Main Orchestration), Python (Data Science/Signal Processing)
*   **Frontend:** React, TypeScript
*   **Database:** SQLite (local storage)
*   **Infrastructure:** Docker Compose

## Architecture & Directory Structure

*   **`api/`**: Main backend logic. Contains Go source for the API server and Python scripts for specific metrics/calculations.
*   **`web/`**: The React-based frontend application.
*   **`binance_trader/`**: A Python-based component for Binance Futures trading, focusing on signal aggregation (FOMO + Alpha signals).
*   **`backtest/`**: Go-based backtesting engine.
*   **`mcp/`**: Model Context Protocol clients for interacting with various AI providers.
*   **`market/`**: Market data handling (WebSocket/API clients for exchanges).
*   **`strategy/`**, **`debate/`**, **`decision/`**: Core logic modules for the trading intelligence.
*   **`docker/`**: Dockerfiles for backend and frontend.

## Building and Running

### Prerequisites
*   Go 1.25+
*   Node.js 18+
*   Docker & Docker Compose (Optional but recommended)

### Quick Start (Docker)
```bash
docker compose up -d
```
Access the web interface at `http://127.0.0.1:3000`.

### Development (Manual)

**Backend:**
```bash
# Install dependencies
go mod download

# Run in dev mode
make run
# OR
go run main.go
```

**Frontend:**
```bash
cd web
npm install
npm run dev
```

**Python Components:**
Check `binance_trader/requirements.txt` or `api/requirements.txt` for Python dependencies.
```bash
pip install -r binance_trader/requirements.txt
```

### Testing
```bash
# Run all tests
make test

# Run backend tests only
make test-backend

# Run frontend tests only
make test-frontend
```

## Key Configuration

*   **`config/`**: Go configuration files.
*   **`.env`**: Environment variables (API keys, settings). See `.env.example`.
*   **`binance_trader/config.py`**: Configuration for the standalone Python trader.

## Workflow & Conventions
*   **Git**: Follow standard Pull Request workflows.
*   **Code Style**:
    *   Go: Standard `gofmt`.
    *   Frontend: Prettier/ESLint.
*   **Documentation**: extensive docs available in `docs/`.

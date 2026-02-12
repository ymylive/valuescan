# Signal Monitor

Signal Monitor focuses on real-time signal monitoring, AI signal briefs, macro market analysis, and Telegram delivery. Legacy integrations have been removed in favor of the current data source.

## Features
- Signal polling and deduplication
- AI signal brief (per-coin)
- Macro market analysis
- TradingView chart generation + overlays
- Proxy management (Clash)
- Web dashboard for configuration and logs

## Project Structure
- `api/`: configuration + utility API for the dashboard
- `signal_monitor/`: signal polling, AI briefs, macro analysis, chart generation
- `web/`: React + TypeScript dashboard (`web/src` for app code)
- `docker/`: Dockerfiles and Nginx config
- `data/`: runtime data and logs (bind-mounted)

## Docker Deployment
1. Copy `.env.example` to `.env` and fill in required values.
2. Build and start the stack:
   - `docker compose up -d --build`
3. View logs:
   - `docker compose logs -f <service>` (see `docker-compose.yml` for service names)
4. Stop the stack:
   - `docker compose down`

## Environment Notes
- See `.env.example` for the full list of environment variables and defaults.

## Frontend/Backend Routing Policy
- Canonical API base is same-origin `/api` for production deployments.
- `VITE_API_BASE_URL` is optional; if provided without `/api`, the frontend appends `/api` automatically.
- Local dev proxy (`web/vite.config.ts`) reads `VITE_DEV_API_PROXY_TARGET`:
  - Python backend local run: `http://localhost:5000`
  - Docker backend local run: `http://localhost:8081`
- `/ws` proxy is disabled by default. Enable only when backend websocket routes are implemented:
  - `VITE_ENABLE_WS_PROXY=1`
  - `VITE_DEV_WS_PROXY_TARGET=ws://<your-backend-host>:<port>`
- Keep frontend and reverse proxy aligned on `/api` path forwarding to avoid environment drift.

## Security
- Keep secrets out of git.
- For public access, use a reverse proxy (TLS) in front of the frontend container.

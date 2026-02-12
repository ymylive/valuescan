# Signal Monitor

`signal_monitor` contains the Python signal-processing pipeline used by the ValueScan stack.
It focuses on message ingestion, deduplication, AI analysis helpers, market data enrichment, and Telegram delivery.

## Quick Setup

From repository root:

```bash
pip install -r signal_monitor/requirements.txt
cp signal_monitor/config.example.py signal_monitor/config.py
```

Then edit `signal_monitor/config.py` for local credentials and runtime options.

## Core Modules (Current Tree)

- `message_handler.py`: message parsing, filtering, deduplication, Telegram dispatch hooks
- `database.py`: processed-message persistence and dedup state
- `signal_tracker.py`: signal confluence tracking
- `telegram.py` / `telegram_bot.py`: Telegram sending and formatting
- `ai_signal_scheduler.py`: periodic AI signal publishing workflow
- `ai_market_analysis.py`: AI market analysis pipeline
- `anomaly_detector/`: anomaly detection logic and supporting code
- `logger.py`: shared logging utilities

## Configuration and Data Files

- `config.example.py`: template for runtime config
- `config.py`: local runtime config (create manually, do not commit secrets)
- `ai_signal_config.json`, `ai_key_levels_config.json`, `ai_overlays_config.json`, `ai_market_summary_config.json`: AI feature configs
- `anomaly_config.json`, `market_alert_config.json`: monitoring/alert configs
- `data/` and `output/`: runtime artifacts and generated outputs

## Validation

Run targeted tests from repo root:

```bash
python -m pytest signal_monitor/test_macro_features.py signal_monitor/test_fundamentals_integration.py
```

## Notes

- Keep secrets out of version control (`config.py`, API keys, tokens).
- Prefer root-level orchestration (`make`, Docker Compose, service scripts) for integrated runs.

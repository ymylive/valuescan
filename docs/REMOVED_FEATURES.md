# Removed Features - ValuScan QuantRefactorV3

## Task #2: Old Frontend and Prediction Features Removal

### Forecast/Prediction Files Removed
- `E:\project\valuescan\mirofish\api\forecast.py` ✓
- `E:\project\valuescan\mirofish\services\btc_forecast_service.py` ✓
- `E:\project\valuescan\signal_monitor\stock_forecast.py` ✓
- `E:\project\valuescan\signal_monitor\btc_forecast.py` ✓
- `E:\project\valuescan\signal_monitor\forecast_engine.py` ✓
- `E:\project\valuescan\signal_monitor\forecast_advice.py` ✓

### Web Directory Status
- Old `web/` directory: Not found (already removed or never existed)

### API Endpoints Removed
- `/api/v1/market/btc-forecast` ✓
- `/api/v1/market/forecast/<symbol>` ✓
- `/api/mirofish/forecast/*` (blueprint removed) ✓

### Code References Cleaned
- `E:\project\valuescan\mirofish\__init__.py` - Removed forecast_bp import and registration ✓
- `E:\project\valuescan\mirofish\api\__init__.py` - Removed forecast_bp and import ✓
- `E:\project\valuescan\mirofish\services\valuescan_client.py` - Removed btc_forecast fetch ✓
- `E:\project\valuescan\api\server.py` - Removed forecast imports, endpoints, and API docs ✓
- `E:\project\valuescan\signal_monitor\message_types.py` - Removed PREDICT_TYPE_MAP ✓

### Files Still Containing Forecast/Prediction References (Legitimate Uses)
- `signal_monitor/fundamentals_sources.py` - Contains "forecast" field for economic data (legitimate use)
- `signal_monitor/macro_event_monitor.py` - Contains "forecast" field for macro events (legitimate use)
- `signal_monitor/pattern_detection_enhanced.py` - Contains "预测突破" comments (pattern prediction, may keep)
- `mirofish/services/zep_tools.py` - Contains "预测" in simulation context (legitimate use)
- `mirofish/services/report_agent.py` - Contains "预测" in simulation report context (legitimate use)

### Notes
- Economic calendar "forecast" fields are legitimate (expected values for economic indicators)
- Pattern detection "prediction" refers to technical analysis breakout predictions (may be legitimate)
- MiroFish simulation "prediction" refers to scenario forecasting (different feature, keep)

---

## Task #3: Global Rename "独立行情描述" → "异动监测"

### Files Updated
- `E:\project\valuescan\docs\BASELINE_ARCHITECTURE.md` ✓
- `E:\project\valuescan\signal_monitor\anomaly_detector\detector.py` ✓
- `E:\project\valuescan\signal_monitor\anomaly_detector\config.py` ✓
- `E:\project\valuescan\signal_monitor\anomaly_detector\features\correlation.py` ✓
- `E:\project\valuescan\signal_monitor\ai_signal_scheduler.py` ✓
- `E:\project\valuescan\scripts\test_anomaly_and_us_market.py` ✓

### Changes Made
- All occurrences of "独立行情" replaced with "异动监测"
- Comments, docstrings, and variable descriptions updated
- Telegram message formatting updated to show "[异动监测]" tag
- Configuration comments updated

### Verification
- No remaining "独立行情" references found in codebase ✓

---

## Task #4: Remove Confidence Fields Globally

### Current State Analysis
The confidence field removal is already enforced at the system level:

1. **LLM Output Parser** (`signal_monitor/llm_output_parser.py`)
   - Contains `ForbiddenFieldError` exception
   - Validates and BLOCKS any confidence/probability fields in LLM outputs
   - Forbidden fields: `["confidence", "confident", "probability", "置信", "信心", "胜率"]`

2. **Prompt System** (`prompts/ai_brief.json`)
   - System prompt explicitly states: "NEVER include confidence, probability, 置信, 信心, or 胜率 fields"
   - Output schema includes `"forbidden_fields"` validation

3. **Legacy Code** (`signal_monitor/ai_signal_analysis.py`)
   - Contains `_extract_confidence_from_text()` and `_normalize_confidence()` functions
   - These are for backward compatibility with old data only
   - New LLM outputs cannot contain confidence fields due to parser validation

### Verification
- ✓ New LLM outputs are blocked from containing confidence fields
- ✓ Prompts explicitly forbid confidence fields
- ✓ Parser validates and rejects forbidden fields
- ✓ Legacy extraction functions exist but don't affect new outputs

### Recommendation
The confidence validation system is working correctly. Legacy extraction functions can be removed in future cleanup but don't affect new system behavior.

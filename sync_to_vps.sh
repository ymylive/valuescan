#!/bin/bash
set -e

VPS_HOST="${VPS_HOST:-82.158.88.34}"
VPS_USER="${VPS_USER:-root}"
VPS_PORT="${VPS_PORT:-22}"
VPS_PATH="${VPS_PATH:-/root/valuescan}"
LOCAL_PATH="E:/project/valuescan"

echo "========================================"
echo "  ValueScan VPS Sync Tool"
echo "========================================"
echo ""

echo "VPS: ${VPS_USER}@${VPS_HOST}:${VPS_PORT}"
echo "PATH: ${VPS_PATH}"
echo ""

read -p "Continue sync? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Cancelled"
  exit 0
fi

echo ""
echo "[1/3] Sync AI config files..."
AI_CONFIGS=(
  "signal_monitor/ai_summary_config.json"
  "signal_monitor/ai_market_summary_config.json"
  "signal_monitor/ai_key_levels_config.json"
  "signal_monitor/ai_overlays_config.json"
)

for config in "${AI_CONFIGS[@]}"; do
  scp -P "$VPS_PORT" "$LOCAL_PATH/$config" "$VPS_USER@$VPS_HOST:$VPS_PATH/$config"
done

echo ""
echo "[2/3] Sync Python code..."
PYTHON_FILES=(
  "signal_monitor/ai_market_summary.py"
  "signal_monitor/chart_pro_v10.py"
  "signal_monitor/ai_signal_analysis.py"
  "signal_monitor/ai_key_levels_config.py"
)

for pyfile in "${PYTHON_FILES[@]}"; do
  scp -P "$VPS_PORT" "$LOCAL_PATH/$pyfile" "$VPS_USER@$VPS_HOST:$VPS_PATH/$pyfile"
done

echo ""
echo "[3/3] Sync frontend files..."
FRONTEND_FILES=(
  "web/src/components/valuescan/SignalMonitorConfigSection.tsx"
  "web/src/components/valuescan/TraderConfigSection.tsx"
  "web/src/components/valuescan/CopyTradeConfigSection.tsx"
  "web/src/components/valuescan/AdvancedSignalMonitorConfigSection.tsx"
  "web/src/components/valuescan/AdvancedTraderConfigSection.tsx"
  "web/src/types/config.ts"
  "web/src/utils/configValidation.ts"
)

for frontend in "${FRONTEND_FILES[@]}"; do
  scp -P "$VPS_PORT" "$LOCAL_PATH/$frontend" "$VPS_USER@$VPS_HOST:$VPS_PATH/$frontend"
done

echo ""
echo "========================================"
echo "  Sync complete"

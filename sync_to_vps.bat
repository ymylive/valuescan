@echo off
REM ValueScan VPS sync (Windows)
setlocal enabledelayedexpansion

set VPS_HOST=82.158.88.34
set VPS_USER=root
set VPS_PORT=22
set VPS_PATH=/root/valuescan
set LOCAL_PATH=E:\project\valuescan

echo ========================================
echo   ValueScan VPS Sync Tool
echo ========================================
echo.

if "%VPS_HOST%"=="your_vps_ip" (
    echo [ERROR] Please configure VPS settings
    pause
    exit /b 1
)

echo VPS: %VPS_USER%@%VPS_HOST%:%VPS_PORT%
echo PATH: %VPS_PATH%
echo.

set /p CONFIRM="Continue sync? (y/n): "
if /i not "%CONFIRM%"=="y" exit /b 0

echo.
echo [1/3] Sync AI config files...
scp -P %VPS_PORT% "%LOCAL_PATH%\signal_monitor\ai_summary_config.json" "%VPS_USER%@%VPS_HOST%:%VPS_PATH%/signal_monitor/"
scp -P %VPS_PORT% "%LOCAL_PATH%\signal_monitor\ai_market_summary_config.json" "%VPS_USER%@%VPS_HOST%:%VPS_PATH%/signal_monitor/"
scp -P %VPS_PORT% "%LOCAL_PATH%\signal_monitor\ai_key_levels_config.json" "%VPS_USER%@%VPS_HOST%:%VPS_PATH%/signal_monitor/"
scp -P %VPS_PORT% "%LOCAL_PATH%\signal_monitor\ai_overlays_config.json" "%VPS_USER%@%VPS_HOST%:%VPS_PATH%/signal_monitor/"

echo.
echo [2/3] Sync Python code...
scp -P %VPS_PORT% "%LOCAL_PATH%\signal_monitor\ai_market_summary.py" "%VPS_USER%@%VPS_HOST%:%VPS_PATH%/signal_monitor/"
scp -P %VPS_PORT% "%LOCAL_PATH%\signal_monitor\chart_pro_v10.py" "%VPS_USER%@%VPS_HOST%:%VPS_PATH%/signal_monitor/"

echo.
echo [3/3] Sync frontend files...
scp -P %VPS_PORT% "%LOCAL_PATH%\web\src\components\valuescan\SignalMonitorConfigSection.tsx" "%VPS_USER%@%VPS_HOST%:%VPS_PATH%/web/src/components/valuescan/"
scp -P %VPS_PORT% "%LOCAL_PATH%\web\src\components\valuescan\TraderConfigSection.tsx" "%VPS_USER%@%VPS_HOST%:%VPS_PATH%/web/src/components/valuescan/"
scp -P %VPS_PORT% "%LOCAL_PATH%\web\src\components\valuescan\CopyTradeConfigSection.tsx" "%VPS_USER%@%VPS_HOST%:%VPS_PATH%/web/src/components/valuescan/"
scp -P %VPS_PORT% "%LOCAL_PATH%\web\src\components\valuescan\AdvancedSignalMonitorConfigSection.tsx" "%VPS_USER%@%VPS_HOST%:%VPS_PATH%/web/src/components/valuescan/"
scp -P %VPS_PORT% "%LOCAL_PATH%\web\src\components\valuescan\AdvancedTraderConfigSection.tsx" "%VPS_USER%@%VPS_HOST%:%VPS_PATH%/web/src/components/valuescan/"
scp -P %VPS_PORT% "%LOCAL_PATH%\web\src\types\config.ts" "%VPS_USER%@%VPS_HOST%:%VPS_PATH%/web/src/types/"
scp -P %VPS_PORT% "%LOCAL_PATH%\web\src\utils\configValidation.ts" "%VPS_USER%@%VPS_HOST%:%VPS_PATH%/web/src/utils/"

echo.
echo ========================================
echo   Sync complete
pause

@echo off
REM ValueScan VPS sync (Windows) - Full sync
setlocal enabledelayedexpansion

set VPS_HOST=82.158.88.34
set VPS_USER=root
set VPS_PORT=22
set VPS_PATH=/root/valuescan
set LOCAL_PATH=E:\project\valuescan

echo ========================================
echo   ValueScan VPS Full Sync Tool
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
echo This will sync ALL changes including:
echo - Backend API (api/proxy.go)
echo - Frontend architecture refactor
echo - Clash proxy management
echo - Configuration management
echo.

set /p CONFIRM="Continue full sync? (y/n): "
if /i not "%CONFIRM%"=="y" exit /b 0

echo.
echo [1/5] Pulling latest changes on VPS...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "cd %VPS_PATH% && git pull origin master"

echo.
echo [2/5] Syncing backend files...
scp -P %VPS_PORT% "%LOCAL_PATH%\api\proxy.go" "%VPS_USER%@%VPS_HOST%:%VPS_PATH%/api/"

echo.
echo [3/5] Rebuilding backend...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "cd %VPS_PATH% && go build -o valuescan main.go"

echo.
echo [4/5] Rebuilding frontend...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "cd %VPS_PATH%/web && npm install && npm run build"

echo.
echo [5/5] Restarting services...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "systemctl restart valuescan-api && systemctl restart valuescan-signal && systemctl restart valuescan-trader"

echo.
echo ========================================
echo   Full sync complete!
echo ========================================
echo.
echo Services restarted:
echo - valuescan-api (backend)
echo - valuescan-signal (signal monitor)
echo - valuescan-trader (trading bot)
echo.
pause

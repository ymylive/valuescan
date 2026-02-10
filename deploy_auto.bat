@echo off
REM ValueScan ?????? - ????
setlocal enabledelayedexpansion

set VPS_HOST=82.158.88.34
set VPS_USER=root
set VPS_PORT=22
set VPS_PATH=/root/valuescan

echo ========================================
echo   ValueScan VPS ????
echo ========================================
echo.

echo [1/6] ??????...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "cd %VPS_PATH% && git fetch origin && git reset --hard origin/master"
if errorlevel 1 (
    echo [??] ??????
    exit /b 1
)
echo [??] ?????

echo.
echo [2/6] ????...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "cd %VPS_PATH% && go build -o valuescan main.go"
if errorlevel 1 (
    echo [??] ??????
    exit /b 1
)
echo [??] ??????

echo.
echo [3/6] ??????...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "cd %VPS_PATH%/web && npm install"
if errorlevel 1 (
    echo [??] ????????
    exit /b 1
)
echo [??] ???????

echo.
echo [4/6] ????...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "cd %VPS_PATH%/web && npm run build"
if errorlevel 1 (
    echo [??] ??????
    exit /b 1
)
echo [??] ??????

echo.
echo [5/6] ?? API ??...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "systemctl restart valuescan-api"
echo [??] API ?????

echo.
echo [6/6] ????????...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "systemctl restart valuescan-signal"
echo [??] ?????????

echo.
echo ========================================
echo   ?????
echo ========================================

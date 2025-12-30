@echo off
REM ValueScan 自动部署脚本 - 无需确认
setlocal enabledelayedexpansion

set VPS_HOST=82.158.88.34
set VPS_USER=root
set VPS_PORT=22
set VPS_PATH=/root/valuescan

echo ========================================
echo   ValueScan VPS 自动部署
echo ========================================
echo.

echo [1/7] 拉取最新代码...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "cd %VPS_PATH% && git fetch origin && git reset --hard origin/master"
if errorlevel 1 (
    echo [错误] 拉取代码失败
    exit /b 1
)
echo [完成] 代码已更新

echo.
echo [2/7] 构建后端...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "cd %VPS_PATH% && go build -o valuescan main.go"
if errorlevel 1 (
    echo [错误] 后端构建失败
    exit /b 1
)
echo [完成] 后端构建成功

echo.
echo [3/7] 安装前端依赖...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "cd %VPS_PATH%/web && npm install"
if errorlevel 1 (
    echo [错误] 前端依赖安装失败
    exit /b 1
)
echo [完成] 前端依赖已安装

echo.
echo [4/7] 构建前端...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "cd %VPS_PATH%/web && npm run build"
if errorlevel 1 (
    echo [错误] 前端构建失败
    exit /b 1
)
echo [完成] 前端构建成功

echo.
echo [5/7] 重启 API 服务...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "systemctl restart valuescan-api"
echo [完成] API 服务已重启

echo.
echo [6/7] 重启信号监控服务...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "systemctl restart valuescan-signal"
echo [完成] 信号监控服务已重启

echo.
echo [7/7] 重启交易机器人服务...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "systemctl restart valuescan-trader"
echo [完成] 交易机器人服务已重启

echo.
echo ========================================
echo   部署完成！
echo ========================================

@echo off
REM ValueScan 完整部署脚本 - 同步前后端到 VPS
setlocal enabledelayedexpansion

set VPS_HOST=82.158.88.34
set VPS_USER=root
set VPS_PORT=22
set VPS_PATH=/root/valuescan
set LOCAL_PATH=E:\project\valuescan

echo ========================================
echo   ValueScan VPS 完整部署工具
echo ========================================
echo.
echo VPS: %VPS_USER%@%VPS_HOST%:%VPS_PORT%
echo 路径: %VPS_PATH%
echo.
echo 部署内容:
echo   [1] 拉取最新代码
echo   [2] 构建后端 (Go)
echo   [3] 构建前端 (React)
echo   [4] 重启所有服务
echo.

set /p CONFIRM="确认部署? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo 部署已取消
    exit /b 0
)

echo.
echo [1/7] 拉取最新代码...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "cd %VPS_PATH% && git fetch origin && git reset --hard origin/master"
if errorlevel 1 (
    echo [错误] 拉取代码失败
    pause
    exit /b 1
)
echo [完成] 代码已更新

echo.
echo [2/7] 构建后端...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "cd %VPS_PATH% && go build -o valuescan main.go"
if errorlevel 1 (
    echo [错误] 后端构建失败
    pause
    exit /b 1
)
echo [完成] 后端构建成功

echo.
echo [3/7] 安装前端依赖...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "cd %VPS_PATH%/web && npm install"
if errorlevel 1 (
    echo [错误] 前端依赖安装失败
    pause
    exit /b 1
)
echo [完成] 前端依赖已安装

echo.
echo [4/7] 构建前端...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "cd %VPS_PATH%/web && npm run build"
if errorlevel 1 (
    echo [错误] 前端构建失败
    pause
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
echo.
echo 已完成的操作:
echo   [✓] 代码已更新到最新版本
echo   [✓] 后端已重新编译
echo   [✓] 前端已重新构建
echo   [✓] 所有服务已重启
echo.
echo 运行中的服务:
echo   - valuescan-api (API 服务)
echo   - valuescan-signal (信号监控)
echo   - valuescan-trader (交易机器人)
echo.
echo 访问地址: http://%VPS_HOST%
echo.
pause

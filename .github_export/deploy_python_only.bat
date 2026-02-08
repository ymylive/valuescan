@echo off
REM ValueScan Python 部署脚本 - 跳过 Go 构建
setlocal enabledelayedexpansion

set VPS_HOST=82.158.88.34
set VPS_USER=root
set VPS_PORT=22
set VPS_PATH=/root/valuescan

echo ========================================
echo   ValueScan VPS 部署 (Python Only)
echo ========================================
echo.
echo VPS: %VPS_USER%@%VPS_HOST%:%VPS_PORT%
echo 路径: %VPS_PATH%
echo.

echo [1/6] 拉取最新代码...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "cd %VPS_PATH% && git fetch origin && git reset --hard origin/master"
if errorlevel 1 (
    echo [错误] 拉取代码失败
    exit /b 1
)
echo [完成] 代码已更新

echo.
echo [2/6] 安装前端依赖...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "cd %VPS_PATH%/web && npm install"
if errorlevel 1 (
    echo [警告] 前端依赖安装失败，继续...
)
echo [完成] 前端依赖处理完成

echo.
echo [3/6] 构建前端...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "cd %VPS_PATH%/web && npm run build"
if errorlevel 1 (
    echo [错误] 前端构建失败
    exit /b 1
)
echo [完成] 前端构建成功

echo.
echo [4/6] 重启 API 服务...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "systemctl restart valuescan-api"
echo [完成] API 服务已重启

echo.
echo [5/6] 重启信号监控服务...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "systemctl restart valuescan-signal"
echo [完成] 信号监控服务已重启

echo.
echo [6/6] 检查服务状态...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% "systemctl status valuescan-api --no-pager -l | head -10"

echo.
echo ========================================
echo   部署完成！
echo ========================================
echo.
echo 访问地址: http://%VPS_HOST%
echo 代理管理: http://%VPS_HOST%/proxy
echo.
echo 提示: 如需启动 Clash 服务，请在代理管理页面点击"尝试启动服务"
echo       或手动执行: ssh %VPS_USER%@%VPS_HOST% "systemctl start clash"
echo.

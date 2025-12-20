# ValueScan VPS 远程清理部署脚本
# 从 Windows 本地执行，通过 SSH 在 VPS 上进行清理部署
# 保留 SSL 证书和 Nginx 域名配置

param(
    [string]$VpsHost = "82.158.88.34",
    [string]$VpsUser = "root",
    [string]$VpsPassword = "Qq159741",
    [string]$ValuescanDir = "/root/valuescan"
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "ValueScan VPS 远程清理部署" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "VPS: $VpsUser@$VpsHost" -ForegroundColor Yellow
Write-Host "目标目录: $ValuescanDir" -ForegroundColor Yellow
Write-Host ""

# 检查 plink 是否可用
$plinkPath = Get-Command plink -ErrorAction SilentlyContinue
if (-not $plinkPath) {
    Write-Host "警告: plink 未找到，尝试使用 ssh..." -ForegroundColor Yellow
    $useSsh = $true
} else {
    $useSsh = $false
}

# 部署命令
$deployCommands = @"
set -e
echo '=========================================='
echo 'ValueScan VPS 清理部署'
echo '=========================================='

VALUESCAN_DIR='$ValuescanDir'
BACKUP_DIR='/root/valuescan_backup_\$(date +%Y%m%d_%H%M%S)'
GITHUB_REPO='https://github.com/ymylive/valuescan.git'

# 停止服务
echo '停止服务...'
systemctl stop valuescan-monitor.service 2>/dev/null || true
systemctl stop valuescan-api.service 2>/dev/null || true
systemctl stop valuescan-keepalive.service 2>/dev/null || true
systemctl stop valuescan-token-refresher.service 2>/dev/null || true

# 备份配置
echo '备份配置文件...'
mkdir -p \$BACKUP_DIR
if [ -d "\$VALUESCAN_DIR" ]; then
    [ -f "\$VALUESCAN_DIR/signal_monitor/config.py" ] && cp "\$VALUESCAN_DIR/signal_monitor/config.py" "\$BACKUP_DIR/signal_monitor_config.py"
    [ -f "\$VALUESCAN_DIR/binance_trader/config.py" ] && cp "\$VALUESCAN_DIR/binance_trader/config.py" "\$BACKUP_DIR/binance_trader_config.py"
    [ -f "\$VALUESCAN_DIR/telegram_copytrade/config.py" ] && cp "\$VALUESCAN_DIR/telegram_copytrade/config.py" "\$BACKUP_DIR/telegram_copytrade_config.py"
    [ -f "\$VALUESCAN_DIR/keepalive_config.json" ] && cp "\$VALUESCAN_DIR/keepalive_config.json" "\$BACKUP_DIR/"
    [ -f "\$VALUESCAN_DIR/valuescan_cookies.json" ] && cp "\$VALUESCAN_DIR/valuescan_cookies.json" "\$BACKUP_DIR/"
    [ -f "\$VALUESCAN_DIR/valuescan_localstorage.json" ] && cp "\$VALUESCAN_DIR/valuescan_localstorage.json" "\$BACKUP_DIR/"
    [ -f "\$VALUESCAN_DIR/valuescan_sessionstorage.json" ] && cp "\$VALUESCAN_DIR/valuescan_sessionstorage.json" "\$BACKUP_DIR/"
    [ -f "\$VALUESCAN_DIR/xray_config.json" ] && cp "\$VALUESCAN_DIR/xray_config.json" "\$BACKUP_DIR/"
    [ -d "\$VALUESCAN_DIR/chrome-debug-profile" ] && cp -r "\$VALUESCAN_DIR/chrome-debug-profile" "\$BACKUP_DIR/"
fi

# 删除旧目录
echo '删除旧目录...'
rm -rf \$VALUESCAN_DIR

# 克隆新代码
echo '克隆最新代码...'
git clone \$GITHUB_REPO \$VALUESCAN_DIR

# 恢复配置
echo '恢复配置文件...'
[ -f "\$BACKUP_DIR/signal_monitor_config.py" ] && mkdir -p "\$VALUESCAN_DIR/signal_monitor" && cp "\$BACKUP_DIR/signal_monitor_config.py" "\$VALUESCAN_DIR/signal_monitor/config.py"
[ -f "\$BACKUP_DIR/binance_trader_config.py" ] && mkdir -p "\$VALUESCAN_DIR/binance_trader" && cp "\$BACKUP_DIR/binance_trader_config.py" "\$VALUESCAN_DIR/binance_trader/config.py"
[ -f "\$BACKUP_DIR/telegram_copytrade_config.py" ] && mkdir -p "\$VALUESCAN_DIR/telegram_copytrade" && cp "\$BACKUP_DIR/telegram_copytrade_config.py" "\$VALUESCAN_DIR/telegram_copytrade/config.py"
[ -f "\$BACKUP_DIR/keepalive_config.json" ] && cp "\$BACKUP_DIR/keepalive_config.json" "\$VALUESCAN_DIR/"
[ -f "\$BACKUP_DIR/valuescan_cookies.json" ] && cp "\$BACKUP_DIR/valuescan_cookies.json" "\$VALUESCAN_DIR/"
[ -f "\$BACKUP_DIR/valuescan_localstorage.json" ] && cp "\$BACKUP_DIR/valuescan_localstorage.json" "\$VALUESCAN_DIR/"
[ -f "\$BACKUP_DIR/valuescan_sessionstorage.json" ] && cp "\$BACKUP_DIR/valuescan_sessionstorage.json" "\$VALUESCAN_DIR/"
[ -f "\$BACKUP_DIR/xray_config.json" ] && cp "\$BACKUP_DIR/xray_config.json" "\$VALUESCAN_DIR/"
[ -d "\$BACKUP_DIR/chrome-debug-profile" ] && cp -r "\$BACKUP_DIR/chrome-debug-profile" "\$VALUESCAN_DIR/"

# 安装依赖
echo '安装 Python 依赖...'
cd \$VALUESCAN_DIR
pip install -r requirements.txt -q

# 构建前端
echo '构建前端...'
cd \$VALUESCAN_DIR/web
npm install --silent
npm run build

# 更新 systemd
echo '更新 systemd 服务...'
cp \$VALUESCAN_DIR/*.service /etc/systemd/system/ 2>/dev/null || true
systemctl daemon-reload

# 启动 API 服务
echo '启动 API 服务...'
systemctl start valuescan-api.service

echo ''
echo '=========================================='
echo '部署完成!'
echo '=========================================='
echo "备份位置: \$BACKUP_DIR"
systemctl status valuescan-api.service --no-pager | head -3
"@

Write-Host "开始执行远程部署..." -ForegroundColor Green
Write-Host ""

if ($useSsh) {
    # 使用 ssh (需要手动输入密码)
    Write-Host "请在提示时输入密码: $VpsPassword" -ForegroundColor Yellow
    $deployCommands | ssh -o StrictHostKeyChecking=no "$VpsUser@$VpsHost" "bash -s"
} else {
    # 使用 plink
    echo $VpsPassword | plink -ssh -pw $VpsPassword "$VpsUser@$VpsHost" $deployCommands
}

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "远程部署成功完成!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Red
    Write-Host "部署过程中出现错误" -ForegroundColor Red
    Write-Host "==========================================" -ForegroundColor Red
}

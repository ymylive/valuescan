#!/bin/bash
# ValueScan VPS 清理部署脚本
# 删除旧文件并从 GitHub 重新克隆，保留 SSL 和 Nginx 配置
# 密码: Qq159741

set -e

echo "=========================================="
echo "ValueScan VPS 清理部署脚本"
echo "=========================================="

# 配置
VALUESCAN_DIR="/root/valuescan"
GITHUB_REPO="https://github.com/ymylive/valuescan.git"
BACKUP_DIR="/root/valuescan_backup_$(date +%Y%m%d_%H%M%S)"

# 需要保留的配置文件
PRESERVE_FILES=(
    "signal_monitor/config.py"
    "binance_trader/config.py"
    "telegram_copytrade/config.py"
    "keepalive_config.json"
    "valuescan_cookies.json"
    "valuescan_localstorage.json"
    "valuescan_sessionstorage.json"
    "xray_config.json"
)

# 需要保留的目录
PRESERVE_DIRS=(
    "chrome-debug-profile"
)

echo ""
echo "步骤 1: 停止所有 ValueScan 服务..."
echo "=========================================="
systemctl stop valuescan-monitor.service 2>/dev/null || true
systemctl stop valuescan-api.service 2>/dev/null || true
systemctl stop valuescan-keepalive.service 2>/dev/null || true
systemctl stop valuescan-token-refresher.service 2>/dev/null || true
echo "✓ 服务已停止"

echo ""
echo "步骤 2: 备份配置文件..."
echo "=========================================="
mkdir -p "$BACKUP_DIR"

cd "$VALUESCAN_DIR" 2>/dev/null || { echo "目录不存在，跳过备份"; }

for file in "${PRESERVE_FILES[@]}"; do
    if [ -f "$VALUESCAN_DIR/$file" ]; then
        mkdir -p "$BACKUP_DIR/$(dirname $file)"
        cp "$VALUESCAN_DIR/$file" "$BACKUP_DIR/$file"
        echo "✓ 备份: $file"
    fi
done

for dir in "${PRESERVE_DIRS[@]}"; do
    if [ -d "$VALUESCAN_DIR/$dir" ]; then
        cp -r "$VALUESCAN_DIR/$dir" "$BACKUP_DIR/$dir"
        echo "✓ 备份目录: $dir"
    fi
done

echo ""
echo "步骤 3: 删除旧的 ValueScan 目录..."
echo "=========================================="
if [ -d "$VALUESCAN_DIR" ]; then
    rm -rf "$VALUESCAN_DIR"
    echo "✓ 已删除: $VALUESCAN_DIR"
else
    echo "目录不存在，跳过删除"
fi

echo ""
echo "步骤 4: 从 GitHub 克隆最新代码..."
echo "=========================================="
git clone "$GITHUB_REPO" "$VALUESCAN_DIR"
echo "✓ 克隆完成"

echo ""
echo "步骤 5: 恢复配置文件..."
echo "=========================================="
for file in "${PRESERVE_FILES[@]}"; do
    if [ -f "$BACKUP_DIR/$file" ]; then
        mkdir -p "$VALUESCAN_DIR/$(dirname $file)"
        cp "$BACKUP_DIR/$file" "$VALUESCAN_DIR/$file"
        echo "✓ 恢复: $file"
    fi
done

for dir in "${PRESERVE_DIRS[@]}"; do
    if [ -d "$BACKUP_DIR/$dir" ]; then
        cp -r "$BACKUP_DIR/$dir" "$VALUESCAN_DIR/$dir"
        echo "✓ 恢复目录: $dir"
    fi
done

echo ""
echo "步骤 6: 安装 Python 依赖..."
echo "=========================================="
cd "$VALUESCAN_DIR"
pip install -r requirements.txt
echo "✓ Python 依赖安装完成"

echo ""
echo "步骤 7: 构建前端..."
echo "=========================================="
cd "$VALUESCAN_DIR/web"
npm install
npm run build
echo "✓ 前端构建完成"

echo ""
echo "步骤 8: 设置文件权限..."
echo "=========================================="
chmod +x "$VALUESCAN_DIR/scripts/"*.sh 2>/dev/null || true
chmod +x "$VALUESCAN_DIR/start.sh" 2>/dev/null || true
echo "✓ 权限设置完成"

echo ""
echo "步骤 9: 重新加载 systemd 服务..."
echo "=========================================="
# 复制 service 文件到 systemd
cp "$VALUESCAN_DIR/"*.service /etc/systemd/system/ 2>/dev/null || true
systemctl daemon-reload
echo "✓ systemd 已重新加载"

echo ""
echo "步骤 10: 启动服务..."
echo "=========================================="
systemctl start valuescan-api.service
echo "✓ API 服务已启动"

# 可选：启动其他服务
# systemctl start valuescan-monitor.service
# systemctl start valuescan-keepalive.service

echo ""
echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo "备份位置: $BACKUP_DIR"
echo ""
echo "服务状态:"
systemctl status valuescan-api.service --no-pager -l | head -5
echo ""
echo "注意事项:"
echo "- SSL 证书和 Nginx 配置未被修改"
echo "- 如需启动信号监控，运行: systemctl start valuescan-monitor.service"
echo "- 如需启动 keepalive，运行: systemctl start valuescan-keepalive.service"
echo ""
echo "访问地址: https://your-domain.com"

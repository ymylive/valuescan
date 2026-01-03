# VPS 同步命令

## 修复内容总结

### 1. 黑屏问题修复
- 修复了 Vite 代理配置（端口从 8080 改为 5000）
- 添加了详细的调试日志

### 2. AI 简评功能修复
- 实现了异步执行（不阻塞 API 请求）
- 改进了日志输出
- 与生图功能使用相同的异步推送技术

## 需要同步的文件

### 核心文件
```bash
# API 服务器
api/server.py

# Signal Monitor
signal_monitor/ai_market_summary.py

# Web 前端
web/vite.config.ts
web/src/App.tsx
```

### 测试脚本
```bash
scripts/test_ai_summary.py
scripts/test_config_page_chrome.py
scripts/quick_test_config.py
```

## 同步命令

### 方法 1: 使用 rsync（推荐）

```bash
# 设置 VPS 地址
export VPS_HOST="root@valuescan.io"
export VPS_PATH="/root/valuescan"

# 同步核心文件
rsync -avz api/server.py $VPS_HOST:$VPS_PATH/api/
rsync -avz signal_monitor/ai_market_summary.py $VPS_HOST:$VPS_PATH/signal_monitor/
rsync -avz web/vite.config.ts $VPS_HOST:$VPS_PATH/web/
rsync -avz web/src/App.tsx $VPS_HOST:$VPS_PATH/web/src/

# 同步测试脚本
rsync -avz scripts/test_ai_summary.py $VPS_HOST:$VPS_PATH/scripts/
rsync -avz scripts/test_config_page_chrome.py $VPS_HOST:$VPS_PATH/scripts/
rsync -avz scripts/quick_test_config.py $VPS_HOST:$VPS_PATH/scripts/

# 同步文档
rsync -avz AI_SUMMARY_FIX_REPORT.md $VPS_HOST:$VPS_PATH/
rsync -avz AI_SUMMARY_QUICK_GUIDE.md $VPS_HOST:$VPS_PATH/
rsync -avz BLACK_SCREEN_FIX_REPORT.md $VPS_HOST:$VPS_PATH/
rsync -avz BLACK_SCREEN_FIX_GUIDE.md $VPS_HOST:$VPS_PATH/
```

### 方法 2: 使用 scp

```bash
# 设置 VPS 地址
export VPS_HOST="root@valuescan.io"
export VPS_PATH="/root/valuescan"

# 同步核心文件
scp api/server.py $VPS_HOST:$VPS_PATH/api/
scp signal_monitor/ai_market_summary.py $VPS_HOST:$VPS_PATH/signal_monitor/
scp web/vite.config.ts $VPS_HOST:$VPS_PATH/web/
scp web/src/App.tsx $VPS_HOST:$VPS_PATH/web/src/

# 同步测试脚本
scp scripts/test_ai_summary.py $VPS_HOST:$VPS_PATH/scripts/
scp scripts/test_config_page_chrome.py $VPS_HOST:$VPS_PATH/scripts/
scp scripts/quick_test_config.py $VPS_HOST:$VPS_PATH/scripts/
```

### 方法 3: 使用 Git（如果 VPS 上有 Git 仓库）

```bash
# 在本地提交更改
git add api/server.py signal_monitor/ai_market_summary.py web/vite.config.ts web/src/App.tsx
git commit -m "fix: 修复黑屏问题和 AI 简评异步执行"

# 推送到远程仓库
git push origin master

# 在 VPS 上拉取更新
ssh $VPS_HOST "cd $VPS_PATH && git pull"
```

## 重启服务

```bash
# SSH 到 VPS
ssh $VPS_HOST

# 重新构建前端
cd /root/valuescan/web
npm run build

# 重启 API 服务器
systemctl restart valuescan-api

# 重启 Signal Monitor
systemctl restart valuescan-signal

# 检查服务状态
systemctl status valuescan-api valuescan-signal
```

## 验证

### 1. 验证黑屏修复

```bash
# 访问 Web 界面
# http://your-vps-ip:3000

# 点击"系统配置"标签
# 确认页面正常显示，不再黑屏
```

### 2. 验证 AI 简评

```bash
# 方法 1: 通过 API
curl -X POST http://your-vps-ip:5000/api/valuescan/ai-summary/trigger

# 方法 2: 通过测试脚本
ssh $VPS_HOST "cd $VPS_PATH && python scripts/test_ai_summary.py"

# 方法 3: 通过 Web 界面
# 进入"系统配置" → "信号监控"
# 点击"触发 AI 简评"按钮
```

### 3. 查看日志

```bash
# 查看 API 服务器日志
ssh $VPS_HOST "journalctl -u valuescan-api -f"

# 查看 Signal Monitor 日志
ssh $VPS_HOST "journalctl -u valuescan-signal -f"

# 查看 AI 简评生成日志
ssh $VPS_HOST "tail -f /root/valuescan/logs/valuescan.log"
```

## 预期结果

### 黑屏修复
- ✅ 配置页面正常显示
- ✅ 所有配置区块可见
- ✅ 可以正常编辑和保存配置

### AI 简评
- ✅ API 立即返回（不阻塞）
- ✅ 后台异步生成
- ✅ 详细的进度日志
- ✅ 生成完成后发送到 Telegram

## 故障排查

### 问题 1: 前端构建失败

```bash
# 检查 Node.js 版本
ssh $VPS_HOST "node --version"

# 重新安装依赖
ssh $VPS_HOST "cd $VPS_PATH/web && npm install"

# 重新构建
ssh $VPS_HOST "cd $VPS_PATH/web && npm run build"
```

### 问题 2: 服务重启失败

```bash
# 检查服务状态
ssh $VPS_HOST "systemctl status valuescan-api valuescan-signal"

# 查看错误日志
ssh $VPS_HOST "journalctl -u valuescan-api -n 50"
ssh $VPS_HOST "journalctl -u valuescan-signal -n 50"

# 手动启动服务
ssh $VPS_HOST "systemctl start valuescan-api"
ssh $VPS_HOST "systemctl start valuescan-signal"
```

### 问题 3: AI 简评不工作

```bash
# 检查配置
ssh $VPS_HOST "cat $VPS_PATH/signal_monitor/ai_summary_config.json"

# 测试 AI 简评
ssh $VPS_HOST "cd $VPS_PATH && python scripts/test_ai_summary.py"

# 查看详细日志
ssh $VPS_HOST "tail -f $VPS_PATH/logs/valuescan.log | grep AI"
```

## 快速同步脚本

创建一个快速同步脚本 `sync.sh`:

```bash
#!/bin/bash
set -e

VPS_HOST="root@valuescan.io"
VPS_PATH="/root/valuescan"

echo "=== 同步文件到 VPS ==="

# 同步核心文件
rsync -avz api/server.py $VPS_HOST:$VPS_PATH/api/
rsync -avz signal_monitor/ai_market_summary.py $VPS_HOST:$VPS_PATH/signal_monitor/
rsync -avz web/vite.config.ts $VPS_HOST:$VPS_PATH/web/
rsync -avz web/src/App.tsx $VPS_HOST:$VPS_PATH/web/src/

echo "=== 重新构建前端 ==="
ssh $VPS_HOST "cd $VPS_PATH/web && npm run build"

echo "=== 重启服务 ==="
ssh $VPS_HOST "systemctl restart valuescan-api valuescan-signal"

echo "=== 检查服务状态 ==="
ssh $VPS_HOST "systemctl status valuescan-api valuescan-signal --no-pager"

echo "=== 完成 ==="
```

使用方法:
```bash
chmod +x sync.sh
./sync.sh
```

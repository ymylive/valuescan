# AI 交易系统 VPS 部署指南

## 概述

本指南详细说明如何将 AI 交易系统部署到 VPS 服务器。

## 系统架构

```
VPS 服务器 (valuescan.io)
├── /root/valuescan/
│   ├── signal_monitor/          # 信号监控服务
│   │   ├── ai_signal_forwarder.py  # NEW: AI 信号转发器
│   │   └── ...
│   ├── binance_trader/          # 交易服务
│   │   ├── ai_mode_handler.py      # NEW: AI 模式处理器
│   │   ├── ai_position_agent.py    # NEW: AI 仓位代理
│   │   ├── ai_performance_tracker.py  # NEW: 性能追踪器
│   │   ├── ai_evolution_engine.py  # NEW: 进化引擎
│   │   ├── ai_evolution_profiles.py  # NEW: 策略配置
│   │   ├── futures_main.py         # UPDATED: 集成 AI 系统
│   │   ├── config.py               # 配置文件
│   │   └── data/                   # 数据目录
│   │       ├── ai_performance.db   # AI 性能数据库
│   │       └── ai_evolution_config.json  # 进化配置
│   ├── web/                     # Web 前端
│   │   └── src/
│   │       ├── types/config.ts     # UPDATED: 类型定义
│   │       ├── components/valuescan/
│   │       │   └── AITradingConfigSection.tsx  # NEW: AI 配置界面
│   │       └── pages/
│   │           └── SettingsPage.tsx  # UPDATED: 添加 AI 交易标签
│   └── scripts/
│       └── deploy_ai_trading_system.py  # NEW: 部署脚本
```

## 部署步骤

### 1. 准备工作

**本地环境检查**:
```bash
# 确保所有 AI 模块文件存在
ls -la signal_monitor/ai_signal_forwarder.py
ls -la binance_trader/ai_*.py
ls -la web/src/components/valuescan/AITradingConfigSection.tsx
```

**VPS 连接测试**:
```bash
# 测试 SSH 连接
ssh root@valuescan.io "echo 'Connection OK'"

# 或使用 Python 脚本测试
python scripts/deploy_ai_trading_system.py
```

### 2. 执行部署

**方式 1: 使用部署脚本 (推荐)**
```bash
# 运行部署脚本
python scripts/deploy_ai_trading_system.py
```

部署脚本会自动:
1. 上传所有 AI 模块文件
2. 创建必要的数据目录
3. 重新构建前端
4. 重启相关服务
5. 检查服务状态

**方式 2: 手动部署**
```bash
# 1. 上传后端文件
scp signal_monitor/ai_signal_forwarder.py root@valuescan.io:/root/valuescan/signal_monitor/
scp binance_trader/ai_*.py root@valuescan.io:/root/valuescan/binance_trader/
scp binance_trader/futures_main.py root@valuescan.io:/root/valuescan/binance_trader/
scp scripts/valuescan_futures_bridge.py root@valuescan.io:/root/valuescan/scripts/

# 2. 上传前端文件
scp web/src/types/config.ts root@valuescan.io:/root/valuescan/web/src/types/
scp web/src/components/valuescan/AITradingConfigSection.tsx root@valuescan.io:/root/valuescan/web/src/components/valuescan/
scp web/src/pages/SettingsPage.tsx root@valuescan.io:/root/valuescan/web/src/pages/

# 3. 上传文档
scp AI_*.md root@valuescan.io:/root/valuescan/

# 4. SSH 到 VPS
ssh root@valuescan.io

# 5. 创建数据目录
mkdir -p /root/valuescan/data
mkdir -p /root/valuescan/binance_trader/data

# 6. 重新构建前端
cd /root/valuescan/web
npm run build

# 7. 重启服务
systemctl restart valuescan-signal
systemctl restart valuescan-trader
systemctl restart valuescan-api
```

### 3. 配置 AI 系统

**SSH 到 VPS**:
```bash
ssh root@valuescan.io
cd /root/valuescan/binance_trader
```

**编辑配置文件**:
```bash
# 如果 config.py 不存在，从示例复制
cp config.example.py config.py

# 编辑配置
nano config.py
```

**必要的配置项**:
```python
# ============ 币种黑名单 ============
COIN_BLACKLIST = ["DOGE", "SHIB"]  # 不想交易的币种

# ============ AI 模式配置 ============
# 启用 AI 模式 (禁用手动策略)
ENABLE_AI_MODE = True

# 启用 AI 仓位代理
ENABLE_AI_POSITION_AGENT = True
AI_POSITION_CHECK_INTERVAL = 300  # 5分钟检查一次

# AI 仓位代理 API 配置 (可选，留空使用 AI Signal 配置)
AI_POSITION_API_KEY = ""
AI_POSITION_API_URL = ""
AI_POSITION_MODEL = ""

# ============ AI 自我进化配置 ============
# 启用 AI 自我进化系统
ENABLE_AI_EVOLUTION = True

# 选择进化策略 (6 种可选)
AI_EVOLUTION_PROFILE = "balanced_day"  # 推荐: 平衡日内
# 可选值:
#   - conservative_scalping: 稳健剥头皮
#   - conservative_swing: 稳健波段
#   - balanced_day: 平衡日内 ⭐ 推荐
#   - balanced_swing: 平衡波段
#   - aggressive_scalping: 激进剥头皮
#   - aggressive_day: 激进日内

# AI 进化最少交易数（达到此数量才开始学习）
AI_EVOLUTION_MIN_TRADES = 50

# AI 进化学习周期（天）
AI_EVOLUTION_LEARNING_PERIOD_DAYS = 30

# AI 进化间隔（小时）
AI_EVOLUTION_INTERVAL_HOURS = 24

# 是否启用 A/B 测试
ENABLE_AI_AB_TESTING = True

# A/B 测试比例（0-1）
AI_AB_TEST_RATIO = 0.2  # 20% 使用新策略

# AI 进化 API 配置（如果为空，使用 ai_signal_config.json 中的配置）
AI_EVOLUTION_API_KEY = ""
AI_EVOLUTION_API_URL = ""
AI_EVOLUTION_MODEL = ""
```

**保存并退出**:
```bash
# Ctrl+O 保存
# Ctrl+X 退出
```

### 4. 重启服务

```bash
# 重启交易服务
systemctl restart valuescan-trader

# 重启信号监控服务
systemctl restart valuescan-signal

# 重启 API 服务
systemctl restart valuescan-api
```

### 5. 验证部署

**检查服务状态**:
```bash
# 查看服务状态
systemctl status valuescan-trader
systemctl status valuescan-signal
systemctl status valuescan-api

# 查看实时日志
journalctl -u valuescan-trader -f
```

**查看 AI 系统日志**:
```bash
# 查看交易日志，应该看到 AI 相关输出
journalctl -u valuescan-trader -f | grep -E "AI|🤖|🧬"

# 示例输出:
# 🤖 AI 模式已启用
# 🤖 AI 仓位代理已启用
# 🧬 AI 进化系统已启用
# 🧬 进化策略: balanced_day (平衡日内)
# 🤖 AI 性能 (7天): 交易=45, 胜率=62.2%, 总盈亏=125.50
```

**检查数据库**:
```bash
# 查看 AI 性能数据库
cd /root/valuescan/binance_trader/data
ls -lh ai_performance.db

# 使用 SQLite 查看数据
sqlite3 ai_performance.db
> .tables
> SELECT COUNT(*) FROM ai_trades;
> .quit
```

**检查进化配置**:
```bash
# 查看进化配置文件
cat /root/valuescan/binance_trader/data/ai_evolution_config.json
```

### 6. Web 界面配置

1. 访问 Web 界面: `https://valuescan.io`
2. 登录账户
3. 进入 **Settings** (设置)
4. 点击 **AI 交易** 标签
5. 配置所有 AI 选项:
   - AI Trading Mode
   - AI Position Agent
   - AI Evolution System
   - Strategy Profile
   - Learning Parameters
   - A/B Testing
   - Coin Blacklist
6. 点击 **Save** 保存配置

## 服务管理

### Systemd 服务

**valuescan-trader.service**:
```ini
[Unit]
Description=ValueScan Binance Trader (IPC)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/valuescan/binance_trader
ExecStart=/usr/bin/python3.9 /root/valuescan/binance_trader/ipc_server.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
Environment=VALUESCAN_TRADER_MODE=ipc

[Install]
WantedBy=multi-user.target
```

**valuescan-signal.service**:
```ini
[Unit]
Description=ValueScan Signal Polling Monitor
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/valuescan/signal_monitor
ExecStart=/usr/bin/python3.9 /root/valuescan/signal_monitor/start_polling.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

### 常用命令

```bash
# 启动服务
systemctl start valuescan-trader
systemctl start valuescan-signal

# 停止服务
systemctl stop valuescan-trader
systemctl stop valuescan-signal

# 重启服务
systemctl restart valuescan-trader
systemctl restart valuescan-signal

# 查看状态
systemctl status valuescan-trader
systemctl status valuescan-signal

# 查看日志
journalctl -u valuescan-trader -f
journalctl -u valuescan-signal -f

# 查看最近 100 行日志
journalctl -u valuescan-trader -n 100

# 查看今天的日志
journalctl -u valuescan-trader --since today
```

## 数据备份

### 备份 AI 数据

```bash
# 备份性能数据库
cp /root/valuescan/binance_trader/data/ai_performance.db \
   /root/valuescan/backups/ai_performance_$(date +%Y%m%d).db

# 备份进化配置
cp /root/valuescan/binance_trader/data/ai_evolution_config.json \
   /root/valuescan/backups/ai_evolution_config_$(date +%Y%m%d).json

# 创建定时备份 (crontab)
crontab -e

# 添加每天凌晨 2 点备份
0 2 * * * cp /root/valuescan/binance_trader/data/ai_performance.db /root/valuescan/backups/ai_performance_$(date +\%Y\%m\%d).db
0 2 * * * cp /root/valuescan/binance_trader/data/ai_evolution_config.json /root/valuescan/backups/ai_evolution_config_$(date +\%Y\%m\%d).json
```

### 恢复数据

```bash
# 恢复性能数据库
cp /root/valuescan/backups/ai_performance_20250101.db \
   /root/valuescan/binance_trader/data/ai_performance.db

# 恢复进化配置
cp /root/valuescan/backups/ai_evolution_config_20250101.json \
   /root/valuescan/binance_trader/data/ai_evolution_config.json

# 重启服务
systemctl restart valuescan-trader
```

## 故障排除

### 问题 1: AI 模式未启动

**症状**: 日志中没有 "AI 模式已启用" 消息

**检查**:
```bash
# 1. 检查配置
grep "ENABLE_AI_MODE" /root/valuescan/binance_trader/config.py

# 2. 检查模块是否存在
ls -la /root/valuescan/binance_trader/ai_mode_handler.py

# 3. 查看错误日志
journalctl -u valuescan-trader -n 100 | grep -i error
```

**解决**:
```bash
# 确保配置正确
nano /root/valuescan/binance_trader/config.py
# 设置 ENABLE_AI_MODE = True

# 重启服务
systemctl restart valuescan-trader
```

### 问题 2: AI 进化系统未运行

**症状**: 没有进化相关日志

**检查**:
```bash
# 1. 检查配置
grep "ENABLE_AI_EVOLUTION" /root/valuescan/binance_trader/config.py

# 2. 检查交易数量
sqlite3 /root/valuescan/binance_trader/data/ai_performance.db \
  "SELECT COUNT(*) FROM ai_trades;"

# 3. 检查 AI API 配置
cat /root/valuescan/signal_monitor/ai_signal_config.json
```

**解决**:
```bash
# 1. 确保至少有 50 笔交易
# 2. 确保 AI API 配置正确
# 3. 等待进化间隔时间 (默认 24 小时)
```

### 问题 3: 前端配置页面不显示

**症状**: Settings 页面没有 "AI 交易" 标签

**检查**:
```bash
# 1. 检查前端文件
ls -la /root/valuescan/web/src/components/valuescan/AITradingConfigSection.tsx
ls -la /root/valuescan/web/src/pages/SettingsPage.tsx

# 2. 检查前端构建
ls -la /root/valuescan/web/dist/
```

**解决**:
```bash
# 重新构建前端
cd /root/valuescan/web
npm run build

# 重启 API 服务
systemctl restart valuescan-api

# 清除浏览器缓存并刷新
```

### 问题 4: AI 信号未转发到交易系统

**症状**: AI 信号分析生成，但交易系统未收到

**检查**:
```bash
# 1. 检查信号转发器
ls -la /root/valuescan/signal_monitor/ai_signal_forwarder.py

# 2. 检查 IPC 配置
grep "IPC_HOST\|IPC_PORT" /root/valuescan/ipc_config.py

# 3. 检查端口监听
netstat -an | grep 8765
```

**解决**:
```bash
# 1. 确保 ai_signal_forwarder.py 已部署
# 2. 确保 IPC 端口正确 (默认 8765)
# 3. 重启信号监控服务
systemctl restart valuescan-signal
```

### 问题 5: 数据库权限错误

**症状**: "Permission denied" 或 "unable to open database file"

**解决**:
```bash
# 修复数据目录权限
chown -R root:root /root/valuescan/binance_trader/data
chmod 755 /root/valuescan/binance_trader/data
chmod 644 /root/valuescan/binance_trader/data/*.db

# 重启服务
systemctl restart valuescan-trader
```

## 性能监控

### 查看 AI 性能统计

```bash
# 使用 Python 脚本查看
cd /root/valuescan/binance_trader
python3.9 -c "
from ai_performance_tracker import AIPerformanceTracker
tracker = AIPerformanceTracker()
stats = tracker.get_performance_stats(days=7)
print(f'7天统计:')
print(f'  总交易数: {stats[\"total_trades\"]}')
print(f'  胜率: {stats[\"win_rate\"]:.2f}%')
print(f'  总盈亏: {stats[\"total_pnl\"]:.2f}')
print(f'  平均盈亏: {stats[\"avg_pnl\"]:.2f}%')
"
```

### 查看进化历史

```bash
# 查看进化配置文件
cat /root/valuescan/binance_trader/data/ai_evolution_config.json | python3.9 -m json.tool

# 查看进化历史
python3.9 -c "
import json
with open('data/ai_evolution_config.json', 'r') as f:
    config = json.load(f)
    history = config.get('evolution_history', [])
    print(f'进化次数: {len(history)}')
    for i, record in enumerate(history[-5:], 1):
        print(f'\n进化 {i}:')
        print(f'  时间: {record[\"timestamp\"]}')
        print(f'  交易数: {record[\"trades_analyzed\"]}')
        print(f'  预期改进: {record[\"expected_improvement\"]:.2f}%')
        print(f'  洞察: {record[\"insights\"][:2]}')
"
```

## 更新部署

### 更新单个模块

```bash
# 从本地上传单个文件
scp binance_trader/ai_evolution_engine.py root@valuescan.io:/root/valuescan/binance_trader/

# SSH 到 VPS 并重启
ssh root@valuescan.io "systemctl restart valuescan-trader"
```

### 完整更新

```bash
# 运行部署脚本
python scripts/deploy_ai_trading_system.py
```

## 安全建议

1. **API 密钥安全**:
   - 不要在配置文件中硬编码 API 密钥
   - 使用环境变量或独立的配置文件
   - 定期轮换 API 密钥

2. **数据库安全**:
   - 定期备份数据库
   - 限制数据库文件权限
   - 不要在公网暴露数据库

3. **服务安全**:
   - 使用防火墙限制端口访问
   - 启用 SSH 密钥认证
   - 定期更新系统和依赖

4. **监控告警**:
   - 设置服务异常告警
   - 监控交易异常
   - 定期检查日志

## 相关文档

- [AI_TRADING_SYSTEM.md](AI_TRADING_SYSTEM.md) - AI 交易系统总览
- [AI_EVOLUTION_SYSTEM.md](AI_EVOLUTION_SYSTEM.md) - AI 进化系统详解
- [AI_EVOLUTION_STRATEGIES.md](AI_EVOLUTION_STRATEGIES.md) - 策略配置指南
- [CLAUDE.md](CLAUDE.md) - 项目总体文档

## 支持

如有问题，请查看:
1. 系统日志: `journalctl -u valuescan-trader -f`
2. 错误日志: `journalctl -u valuescan-trader -p err`
3. 项目文档: 上述相关文档

---

部署完成后，AI 交易系统将自动运行，并根据配置的策略进行自我学习和优化！🚀

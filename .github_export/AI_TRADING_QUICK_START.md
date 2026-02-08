# AI 交易系统快速开始

## 🚀 快速部署

### 1. 部署到 VPS

```bash
# 运行部署脚本
python scripts/deploy_ai_trading_system.py
```

### 2. 配置 AI 系统

```bash
# SSH 到 VPS
ssh root@valuescan.io

# 配置
cd /root/valuescan/binance_trader
cp config.example.py config.py
nano config.py
```

**必须配置的选项**:
```python
ENABLE_AI_MODE = True
ENABLE_AI_POSITION_AGENT = True
ENABLE_AI_EVOLUTION = True
AI_EVOLUTION_PROFILE = "balanced_day"  # 推荐
```

### 3. 重启服务

```bash
systemctl restart valuescan-signal
systemctl restart valuescan-trader
systemctl restart valuescan-api
```

### 4. 验证

```bash
# 查看 AI 日志
journalctl -u valuescan-trader -f | grep -E "AI|🤖|🧬"
```

## 📚 文档

| 文档 | 说明 |
|------|------|
| [AI_TRADING_SYSTEM.md](AI_TRADING_SYSTEM.md) | 系统总览和架构 |
| [AI_EVOLUTION_SYSTEM.md](AI_EVOLUTION_SYSTEM.md) | 进化系统详解 |
| [AI_EVOLUTION_STRATEGIES.md](AI_EVOLUTION_STRATEGIES.md) | 策略配置指南 |
| [AI_TRADING_VPS_DEPLOYMENT.md](AI_TRADING_VPS_DEPLOYMENT.md) | 完整部署指南 |
| [AI_TRADING_DEPLOYMENT_CHECKLIST.md](AI_TRADING_DEPLOYMENT_CHECKLIST.md) | 部署检查清单 |
| [AI_TRADING_IMPLEMENTATION_SUMMARY.md](AI_TRADING_IMPLEMENTATION_SUMMARY.md) | 实现总结 |

## ⚙️ 核心功能

### 1. AI 托管模式
- 完全由 AI 控制交易
- 禁用手动策略
- 币种黑名单

### 2. AI 仓位代理
- 自主决策加仓/减仓/平仓
- 每 5 分钟分析一次

### 3. AI 自我进化
- 从交易数据学习
- 自动优化策略
- A/B 测试新策略

### 4. 进化策略
6 种可选策略:
- `conservative_scalping` - 稳健剥头皮
- `conservative_swing` - 稳健波段
- `balanced_day` - 平衡日内 ⭐ 推荐
- `balanced_swing` - 平衡波段
- `aggressive_scalping` - 激进剥头皮
- `aggressive_day` - 激进日内

## 🎯 快速配置

### 后端配置 (config.py)

```python
# AI 模式
ENABLE_AI_MODE = True
COIN_BLACKLIST = ["DOGE", "SHIB"]

# AI 仓位代理
ENABLE_AI_POSITION_AGENT = True
AI_POSITION_CHECK_INTERVAL = 300

# AI 进化
ENABLE_AI_EVOLUTION = True
AI_EVOLUTION_PROFILE = "balanced_day"
AI_EVOLUTION_MIN_TRADES = 50
AI_EVOLUTION_LEARNING_PERIOD_DAYS = 30
AI_EVOLUTION_INTERVAL_HOURS = 24
ENABLE_AI_AB_TESTING = True
AI_AB_TEST_RATIO = 0.2
```

### 前端配置

1. 访问 `https://valuescan.io`
2. Settings → **AI 交易**
3. 配置所有选项
4. 保存

## 📊 监控

### 查看 AI 性能

```bash
journalctl -u valuescan-trader -f | grep "AI 性能"
```

### 查看进化历史

```bash
cd /root/valuescan/binance_trader
cat data/ai_evolution_config.json | python3.9 -m json.tool
```

### 查看数据库

```bash
sqlite3 data/ai_performance.db "SELECT COUNT(*) FROM ai_trades;"
```

## 🔧 故障排除

### AI 模式未启动
```bash
grep "ENABLE_AI_MODE" config.py
systemctl restart valuescan-trader
```

### AI 进化未运行
```bash
# 检查交易数量 (需要至少 50 笔)
sqlite3 data/ai_performance.db "SELECT COUNT(*) FROM ai_trades;"
```

### 前端 AI 标签不显示
```bash
cd /root/valuescan/web
npm run build
systemctl restart valuescan-api
```

## 📈 使用建议

1. **新手**: 使用 `balanced_day` 策略
2. **稳健**: 使用 `conservative_swing` 策略
3. **激进**: 使用 `aggressive_day` 策略
4. **上班族**: 使用 `balanced_swing` 策略

## 🔒 安全提示

- 定期备份数据库
- 不要硬编码 API 密钥
- 使用 A/B 测试模式
- 密切监控性能

## 📞 支持

查看日志:
```bash
journalctl -u valuescan-trader -f
```

查看错误:
```bash
journalctl -u valuescan-trader -p err --since today
```

---

**版本**: v1.0.0
**更新**: 2025-12-29

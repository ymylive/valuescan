# AI 交易系统部署检查清单

## 部署前检查 ✓

### 本地环境
- [ ] 所有 AI 模块文件已创建并测试
- [ ] 前端构建成功 (`cd web && npm run build`)
- [ ] 部署脚本可执行 (`python scripts/deploy_ai_trading_system.py --help`)
- [ ] SSH 连接正常 (`ssh root@valuescan.io "echo OK"`)

### 文件清单
**Backend - Signal Monitor:**
- [ ] `signal_monitor/ai_signal_forwarder.py`

**Backend - Binance Trader:**
- [ ] `binance_trader/ai_mode_handler.py`
- [ ] `binance_trader/ai_position_agent.py`
- [ ] `binance_trader/ai_performance_tracker.py`
- [ ] `binance_trader/ai_evolution_engine.py`
- [ ] `binance_trader/ai_evolution_profiles.py`
- [ ] `binance_trader/futures_main.py` (已更新)
- [ ] `binance_trader/config.example.py` (已更新)

**Backend - Scripts:**
- [ ] `scripts/valuescan_futures_bridge.py` (已更新)

**Frontend:**
- [ ] `web/src/types/config.ts` (已更新)
- [ ] `web/src/components/valuescan/AITradingConfigSection.tsx`
- [ ] `web/src/pages/SettingsPage.tsx` (已更新)

**Documentation:**
- [ ] `AI_TRADING_SYSTEM.md`
- [ ] `AI_EVOLUTION_SYSTEM.md`
- [ ] `AI_EVOLUTION_STRATEGIES.md`
- [ ] `AI_TRADING_VPS_DEPLOYMENT.md`

## 部署步骤 ✓

### 1. 执行部署
```bash
python scripts/deploy_ai_trading_system.py
```

- [ ] 文件上传成功 (应显示 "✅ 完成")
- [ ] 数据目录创建成功
- [ ] 前端构建成功
- [ ] 服务重启成功
- [ ] 服务状态检查通过

### 2. 配置 AI 系统
```bash
ssh root@valuescan.io
cd /root/valuescan/binance_trader
cp config.example.py config.py
nano config.py
```

**必须配置的选项:**
- [ ] `COIN_BLACKLIST = []` (根据需要设置)
- [ ] `ENABLE_AI_MODE = True`
- [ ] `ENABLE_AI_POSITION_AGENT = True`
- [ ] `AI_POSITION_CHECK_INTERVAL = 300`
- [ ] `ENABLE_AI_EVOLUTION = True`
- [ ] `AI_EVOLUTION_PROFILE = "balanced_day"`
- [ ] `AI_EVOLUTION_MIN_TRADES = 50`
- [ ] `AI_EVOLUTION_LEARNING_PERIOD_DAYS = 30`
- [ ] `AI_EVOLUTION_INTERVAL_HOURS = 24`
- [ ] `ENABLE_AI_AB_TESTING = True`
- [ ] `AI_AB_TEST_RATIO = 0.2`

**可选配置 (留空使用默认):**
- [ ] `AI_POSITION_API_KEY = ""`
- [ ] `AI_POSITION_API_URL = ""`
- [ ] `AI_POSITION_MODEL = ""`
- [ ] `AI_EVOLUTION_API_KEY = ""`
- [ ] `AI_EVOLUTION_API_URL = ""`
- [ ] `AI_EVOLUTION_MODEL = ""`

### 3. 重启服务
```bash
systemctl restart valuescan-signal
systemctl restart valuescan-trader
systemctl restart valuescan-api
```

- [ ] valuescan-signal 重启成功
- [ ] valuescan-trader 重启成功
- [ ] valuescan-api 重启成功

## 部署后验证 ✓

### 1. 服务状态检查
```bash
systemctl status valuescan-trader
systemctl status valuescan-signal
systemctl status valuescan-api
```

- [ ] valuescan-trader: Active (running)
- [ ] valuescan-signal: Active (running)
- [ ] valuescan-api: Active (running)

### 2. 日志检查
```bash
journalctl -u valuescan-trader -n 50 | grep -E "AI|🤖|🧬"
```

**应该看到的日志:**
- [ ] "🤖 AI 模式已启用"
- [ ] "🤖 AI 仓位代理已启用"
- [ ] "🧬 AI 进化系统已启用"
- [ ] "🧬 进化策略: balanced_day"
- [ ] "📊 AI 性能追踪器已初始化"

### 3. 数据库检查
```bash
ls -lh /root/valuescan/binance_trader/data/ai_performance.db
sqlite3 /root/valuescan/binance_trader/data/ai_performance.db ".tables"
```

- [ ] ai_performance.db 文件存在
- [ ] 包含表: ai_trades, ai_position_actions, ai_learning_sessions

### 4. 配置文件检查
```bash
cat /root/valuescan/binance_trader/data/ai_evolution_config.json
```

- [ ] ai_evolution_config.json 文件存在
- [ ] 包含正确的 evolution_profile
- [ ] 包含 strategy_parameters

### 5. Web 界面检查
访问: `https://valuescan.io`

- [ ] 登录成功
- [ ] Settings 页面可访问
- [ ] "AI 交易" 标签存在
- [ ] AI Trading Mode 配置可见
- [ ] AI Evolution System 配置可见
- [ ] Strategy Profile 选择器可见 (6 个选项)
- [ ] Coin Blacklist 配置可见
- [ ] 保存配置成功

### 6. 功能测试

**AI 信号转发测试:**
```bash
# 查看信号监控日志
journalctl -u valuescan-signal -f | grep "AI_SIGNAL"
```
- [ ] 看到 "➡️ 转发 AI 信号到交易系统" 消息

**AI 模式处理测试:**
```bash
# 查看交易日志
journalctl -u valuescan-trader -f | grep "AI 信号"
```
- [ ] 看到 "收到 AI 信号" 消息
- [ ] 看到 "处理 AI 交易信号" 消息

**AI 仓位代理测试:**
```bash
# 等待有持仓后查看日志
journalctl -u valuescan-trader -f | grep "仓位代理"
```
- [ ] 看到 "AI 仓位代理分析" 消息
- [ ] 看到仓位决策 (hold/add/reduce/close)

**AI 进化测试:**
```bash
# 等待至少 50 笔交易后查看
journalctl -u valuescan-trader -f | grep "进化"
```
- [ ] 看到 "开始 AI 进化过程" 消息
- [ ] 看到 "AI 进化完成" 消息
- [ ] 看到预期改进百分比

## 性能监控 ✓

### 每日检查
- [ ] 查看服务状态: `systemctl status valuescan-trader`
- [ ] 查看错误日志: `journalctl -u valuescan-trader -p err --since today`
- [ ] 查看 AI 性能统计 (通过 Web 界面或日志)

### 每周检查
- [ ] 备份数据库: `cp ai_performance.db backups/`
- [ ] 查看进化历史
- [ ] 检查策略参数变化
- [ ] 评估整体性能

### 每月检查
- [ ] 评估策略配置是否需要调整
- [ ] 检查是否需要切换 evolution_profile
- [ ] 清理旧日志和备份
- [ ] 更新系统和依赖

## 故障排除清单 ✓

### AI 模式未启动
- [ ] 检查 `ENABLE_AI_MODE` 配置
- [ ] 检查 `ai_mode_handler.py` 文件存在
- [ ] 查看错误日志
- [ ] 重启服务

### AI 进化未运行
- [ ] 检查交易数量 >= 50
- [ ] 检查 AI API 配置
- [ ] 检查进化间隔时间
- [ ] 查看进化配置文件

### 前端配置不显示
- [ ] 检查前端文件存在
- [ ] 重新构建前端
- [ ] 清除浏览器缓存
- [ ] 重启 API 服务

### AI 信号未转发
- [ ] 检查 `ai_signal_forwarder.py` 存在
- [ ] 检查 IPC 端口 (8765)
- [ ] 检查网络连接
- [ ] 重启信号服务

### 数据库错误
- [ ] 检查文件权限
- [ ] 检查磁盘空间
- [ ] 检查数据库完整性
- [ ] 恢复备份

## 回滚计划 ✓

如果部署出现严重问题，执行回滚:

### 1. 停止服务
```bash
systemctl stop valuescan-trader
systemctl stop valuescan-signal
```

### 2. 恢复旧文件
```bash
# 从备份恢复 (假设有备份)
cp /root/valuescan/backups/futures_main.py.bak /root/valuescan/binance_trader/futures_main.py
# ... 恢复其他文件
```

### 3. 禁用 AI 功能
```bash
nano /root/valuescan/binance_trader/config.py
# 设置:
# ENABLE_AI_MODE = False
# ENABLE_AI_EVOLUTION = False
```

### 4. 重启服务
```bash
systemctl start valuescan-signal
systemctl start valuescan-trader
```

### 5. 验证回滚
```bash
systemctl status valuescan-trader
journalctl -u valuescan-trader -n 50
```

## 完成标记 ✓

- [ ] 所有部署步骤完成
- [ ] 所有验证测试通过
- [ ] 文档已更新
- [ ] 团队已通知
- [ ] 监控已设置

---

**部署日期**: _______________
**部署人员**: _______________
**版本号**: v1.0.0
**备注**: _______________

---

## 快速命令参考

```bash
# 部署
python scripts/deploy_ai_trading_system.py

# 查看日志
journalctl -u valuescan-trader -f

# 查看 AI 日志
journalctl -u valuescan-trader -f | grep -E "AI|🤖|🧬"

# 重启服务
systemctl restart valuescan-trader

# 查看状态
systemctl status valuescan-trader

# 查看性能
cd /root/valuescan/binance_trader
python3.9 -c "from ai_performance_tracker import AIPerformanceTracker; t=AIPerformanceTracker(); print(t.get_performance_stats(7))"

# 查看进化历史
cat data/ai_evolution_config.json | python3.9 -m json.tool

# 备份数据
cp data/ai_performance.db backups/ai_performance_$(date +%Y%m%d).db
```

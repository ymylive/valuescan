# AI 自我进化系统

## 概述

AI 自我进化系统让 AI 能够根据实际交易数据进行自我学习和策略优化，实现真正的智能进化。

## 核心功能

### 1. **性能追踪** ✅
- **模块**: [binance_trader/ai_performance_tracker.py](binance_trader/ai_performance_tracker.py)
- **数据库**: `data/ai_performance.db`
- **功能**:
  - 记录每笔 AI 交易的完整信息
  - 追踪入场/出场价格和时间
  - 保存 AI 分析和信心度
  - 记录实际盈亏
  - 存储市场条件
  - 追踪仓位调整动作

**数据表结构**:
```sql
-- AI 交易记录
ai_trades (
  trade_id, symbol, direction,
  entry_time, entry_price, entry_quantity,
  ai_analysis, ai_confidence, ai_stop_loss, ai_take_profit, ai_risk_level,
  exit_time, exit_price, exit_quantity, exit_reason,
  realized_pnl, realized_pnl_percent,
  market_conditions, status
)

-- AI 仓位调整记录
ai_position_actions (
  trade_id, action_time, action_type,
  ai_reason, ai_confidence,
  quantity_before, quantity_after, price,
  market_conditions
)

-- AI 学习记录
ai_learning_sessions (
  session_id, start_time, end_time,
  trades_analyzed, patterns_discovered, insights,
  old_parameters, new_parameters, expected_improvement,
  actual_improvement, validation_period_days, status
)
```

### 2. **进化引擎** ✅
- **模块**: [binance_trader/ai_evolution_engine.py](binance_trader/ai_evolution_engine.py)
- **配置**: `data/ai_evolution_config.json`
- **功能**:
  - 分析历史交易数据
  - 发现成功/失败模式
  - 生成优化建议
  - 自动调整策略参数
  - A/B 测试新策略

**进化流程**:
```
1. 收集交易数据 (最近 N 天)
   ↓
2. 分析交易模式
   - 信心度与胜率相关性
   - 币种表现分析
   - 方向表现分析
   - 风险等级表现分析
   ↓
3. AI 生成优化建议
   - 调用 AI API 分析数据
   - 提取优化参数
   - 计算预期改进
   ↓
4. 应用新策略
   - A/B 测试模式: 部分交易使用新策略
   - 直接应用模式: 全部使用新策略
   ↓
5. 验证效果
   - 持续监控性能
   - 对比新旧策略
   - 决定是否保留
```

### 3. **策略参数优化** ✅
AI 可以优化以下参数：
- `confidence_threshold`: 信心度阈值
- `risk_multiplier`: 风险倍数
- `position_size_multiplier`: 仓位大小倍数
- `stop_loss_multiplier`: 止损倍数
- `take_profit_multiplier`: 止盈倍数

### 4. **A/B 测试** ✅
- 新策略先在部分交易中测试
- 可配置测试比例 (默认 20%)
- 对比新旧策略性能
- 自动决定是否全面应用

### 5. **前端配置界面** ✅
- **位置**: [web/src/components/valuescan/TraderConfigSection.tsx](web/src/components/valuescan/TraderConfigSection.tsx)
- **功能**:
  - 启用/禁用进化系统
  - 配置学习参数
  - 设置进化间隔
  - 配置 A/B 测试
  - 查看进化历史

## 配置示例

### 后端配置 (binance_trader/config.py)

```python
# ============ AI 自我进化配置 ============
# 是否启用 AI 自我进化系统
ENABLE_AI_EVOLUTION = True

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

### 前端配置

1. 进入 **Settings** → **Trader Configuration**
2. 找到 **AI Evolution System** 部分
3. 开启 **Enable AI Evolution**
4. 配置学习参数:
   - **Min Trades for Learning**: 最少交易数 (默认 50)
   - **Learning Period**: 学习周期天数 (默认 30)
   - **Evolution Interval**: 进化间隔小时 (默认 24)
5. 配置 A/B 测试:
   - 开启 **Enable A/B Testing**
   - 设置 **Test Ratio** (默认 0.2 = 20%)
6. 保存配置

## 工作流程

### 1. 数据收集阶段
```
AI 交易执行 → 记录入场信息 → 追踪持仓变化 → 记录出场信息
                    ↓
            性能追踪器 (SQLite)
```

### 2. 学习分析阶段
```
定期检查 (每小时) → 是否达到进化条件?
                        ↓ 是
                  获取交易数据 (最近 N 天)
                        ↓
                  分析交易模式
                        ↓
                  AI 生成优化建议
                        ↓
                  记录进化历史
```

### 3. 策略应用阶段
```
A/B 测试模式:
  新交易 → 随机选择 (20% 新策略, 80% 旧策略) → 执行

直接应用模式:
  新交易 → 使用新策略 → 执行
```

### 4. 效果验证阶段
```
持续监控 → 对比性能 → 决定保留/回滚
```

## 进化示例

### 场景: AI 发现高信心度交易表现更好

**分析结果**:
```json
{
  "confidence_correlation": {
    "high": {
      "count": 30,
      "win_rate": 75.0,
      "avg_pnl_percent": 4.5
    },
    "medium": {
      "count": 40,
      "win_rate": 55.0,
      "avg_pnl_percent": 1.2
    },
    "low": {
      "count": 20,
      "win_rate": 35.0,
      "avg_pnl_percent": -1.8
    }
  }
}
```

**AI 优化建议**:
```json
{
  "insights": [
    "发现1: 高信心度交易 (>0.7) 胜率显著更高 (75% vs 55%)",
    "发现2: 低信心度交易 (<0.5) 平均亏损",
    "发现3: 建议提高信心度阈值，减少低质量交易"
  ],
  "new_parameters": {
    "confidence_threshold": 0.6,  // 从 0.5 提高到 0.6
    "risk_multiplier": 1.0,
    "position_size_multiplier": 1.2,  // 高信心度时增加仓位
    "stop_loss_multiplier": 1.0,
    "take_profit_multiplier": 1.0
  },
  "expected_improvement": 8.5,  // 预期改进 8.5%
  "reasoning": "通过提高信心度阈值过滤低质量信号，同时在高信心度时增加仓位，预期可提升整体收益"
}
```

**应用结果**:
- 新策略在 20% 的交易中测试
- 持续监控 7-30 天
- 如果实际改进 >= 预期改进的 70%，全面应用
- 否则回滚到旧策略

## 性能指标

### 追踪的指标
1. **总体指标**:
   - 总交易数
   - 胜率
   - 平均盈亏
   - 总盈亏
   - 平均信心度

2. **分类指标**:
   - 按方向 (LONG/SHORT)
   - 按币种
   - 按信心度等级
   - 按风险等级

3. **进化指标**:
   - 进化次数
   - 参数变化历史
   - 预期 vs 实际改进
   - A/B 测试结果

### 查看性能统计

**Python API**:
```python
from binance_trader.ai_performance_tracker import AIPerformanceTracker

tracker = AIPerformanceTracker()

# 获取最近 30 天统计
stats = tracker.get_performance_stats(days=30)
print(f"胜率: {stats['win_rate']:.2f}%")
print(f"总盈亏: {stats['total_pnl']:.2f}")

# 获取用于学习的交易数据
trades = tracker.get_trades_for_learning(min_trades=50, days=30)
print(f"可用于学习的交易数: {len(trades)}")
```

**日志输出**:
```
🤖 AI 性能 (7天): 交易=45, 胜率=62.2%, 总盈亏=125.50
🧬 开始 AI 进化过程...
🧬 AI 进化完成!
  - 分析交易数: 45
  - 预期改进: 8.50%
  💡 发现1: 高信心度交易胜率显著更高
  💡 发现2: BTC 和 ETH 表现最佳
  💡 发现3: 建议提高信心度阈值
  🧪 A/B 测试已启动: 20% 使用新策略
```

## 安全机制

1. **保守优化**: 每次参数调整不超过 20%
2. **数据驱动**: 基于实际交易数据，不过度优化
3. **A/B 测试**: 新策略先小规模测试
4. **回滚机制**: 性能不佳时自动回滚
5. **最小样本**: 至少 50 笔交易才开始学习
6. **进化间隔**: 避免过于频繁的调整

## 高级功能

### 1. 手动触发进化
```python
from binance_trader.ai_evolution_engine import AIEvolutionEngine
from binance_trader.ai_performance_tracker import AIPerformanceTracker

tracker = AIPerformanceTracker()
engine = AIEvolutionEngine(tracker)

# 强制进化
result = engine.analyze_and_evolve()
if result:
    print(f"进化完成，预期改进: {result['expected_improvement']:.2f}%")
```

### 2. 查看进化历史
```python
# 查看所有进化记录
history = engine.config["evolution_history"]
for record in history:
    print(f"时间: {record['timestamp']}")
    print(f"交易数: {record['trades_analyzed']}")
    print(f"预期改进: {record['expected_improvement']:.2f}%")
    print(f"洞察: {record['insights']}")
```

### 3. 自定义优化目标
可以修改 `_build_optimization_prompt` 方法来自定义优化目标，例如:
- 最大化夏普比率
- 最小化最大回撤
- 平衡风险收益比
- 优化特定币种表现

## 故障排除

### 问题 1: 进化系统未启动
**检查**:
1. `ENABLE_AI_EVOLUTION = True`
2. AI API 配置正确
3. 至少有 50 笔交易记录

### 问题 2: 进化失败
**检查**:
1. 查看日志: `journalctl -u valuescan-trader -f`
2. 验证 AI API 可访问
3. 检查交易数据完整性

### 问题 3: A/B 测试不生效
**检查**:
1. `ENABLE_AI_AB_TESTING = True`
2. `AI_AB_TEST_RATIO` 设置合理 (0.05-0.5)
3. 查看进化配置文件: `data/ai_evolution_config.json`

## 最佳实践

1. **初期**: 收集至少 100 笔交易数据再启用进化
2. **测试**: 先在测试网验证进化系统
3. **监控**: 密切关注进化后的性能变化
4. **保守**: 使用 A/B 测试模式，避免激进调整
5. **记录**: 定期备份进化配置和交易数据
6. **分析**: 定期查看进化历史，理解 AI 的学习过程

## 未来增强

- [ ] 多目标优化 (帕累托前沿)
- [ ] 强化学习集成
- [ ] 集成学习 (多模型投票)
- [ ] 实时性能可视化
- [ ] 自动异常检测和回滚
- [ ] 策略版本管理
- [ ] 进化过程可视化
- [ ] 社区策略共享

## 总结

AI 自我进化系统让交易 AI 能够:
1. ✅ 从实际交易中学习
2. ✅ 发现成功模式
3. ✅ 自动优化策略
4. ✅ 持续改进性能
5. ✅ 适应市场变化

这是一个真正的"自我进化"系统，AI 不再是静态的，而是能够根据经验不断成长和优化！

---

详细文档请查看:
- [AI Trading System](AI_TRADING_SYSTEM.md) - AI 交易系统总览
- [binance_trader/ai_performance_tracker.py](binance_trader/ai_performance_tracker.py) - 性能追踪器
- [binance_trader/ai_evolution_engine.py](binance_trader/ai_evolution_engine.py) - 进化引擎

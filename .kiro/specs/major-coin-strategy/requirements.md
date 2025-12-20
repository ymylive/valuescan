# 主流币独立策略设置

## 概述
为主流加密货币（BTC、ETH、BNB、SOL、XRP等）提供独立的交易策略配置，包括杠杆倍数和仓位大小，与山寨币策略分开管理。

## 用户故事

### US-1: 主流币独立杠杆设置
**作为** 交易者
**我想要** 为主流币设置独立的杠杆倍数
**以便** 根据主流币较低的波动性使用不同的风险策略

**验收标准:**
- [x] 前端显示"主流币杠杆倍数"输入框
- [x] 后端配置支持 `MAJOR_COIN_LEVERAGE` 参数
- [x] 交易执行时根据币种类型自动选择对应杠杆
- [x] 未设置时回退到全局杠杆设置

### US-2: 主流币独立仓位大小
**作为** 交易者
**我想要** 为主流币设置独立的最大仓位比例
**以便** 在主流币上使用更大的仓位（因为风险较低）

**验收标准:**
- [x] 前端显示"主流币单笔最大仓位"输入框
- [x] 后端配置支持 `MAJOR_COIN_MAX_POSITION_PERCENT` 参数
- [x] 风险管理器根据币种类型计算仓位大小
- [x] 未设置时回退到全局仓位设置

### US-3: 策略对比展示
**作为** 交易者
**我想要** 在界面上看到主流币和山寨币策略的对比
**以便** 快速了解两种策略的差异

**验收标准:**
- [x] 前端显示策略对比表格
- [x] 对比内容包括：杠杆、单笔仓位、止损、止盈1/2/3

## 技术实现

### 前端修改
- `web/src/types/config.ts` - 添加 `major_coin_leverage` 和 `major_coin_max_position_percent` 类型
- `web/src/components/valuescan/TraderConfigSection.tsx` - 添加主流币杠杆和仓位输入框，更新策略对比表

### 后端修改
- `binance_trader/config.py` - 添加 `MAJOR_COIN_LEVERAGE` 和 `MAJOR_COIN_MAX_POSITION_PERCENT` 配置
- `binance_trader/risk_manager.py` - 修改 `calculate_position_size` 支持主流币独立仓位
- `binance_trader/futures_main.py` - 添加 `_get_leverage` 方法支持主流币独立杠杆

### API 映射
- `api/server.py` - 已有 `major_coin_leverage` 和 `major_coin_max_position_percent` 的映射

## 状态
✅ 已完成并部署到 VPS

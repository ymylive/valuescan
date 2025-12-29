<p align="center">
  <img src="screenshots/logo.png" alt="ValueScan Logo" width="120" />
</p>

<h1 align="center">ValueScan</h1>

<p align="center">
  <strong>🚀 AI 驱动的加密货币信号监控与自动交易系统</strong>
</p>

<p align="center">
  <a href="README.md">English</a> | <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="#功能特性">功能特性</a> •
  <a href="#ai-交易系统">AI 交易</a> •
  <a href="#系统架构">系统架构</a> •
  <a href="#快速开始">快速开始</a> •
  <a href="#部署">部署</a> •
  <a href="#文档">文档</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Go-1.21+-00ADD8?style=flat-square&logo=go" alt="Go Version" />
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python" alt="Python Version" />
  <img src="https://img.shields.io/badge/React-18+-61DAFB?style=flat-square&logo=react" alt="React" />
  <img src="https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=flat-square&logo=typescript" alt="TypeScript" />
  <img src="https://img.shields.io/badge/License-AGPL--3.0-blue?style=flat-square" alt="License" />
</p>

---

## 📖 概述

**ValueScan** 是一个综合性的加密货币交易平台，集成了实时信号监控、AI 驱动的市场分析和**全自动 AI 交易**功能。采用微服务架构，使用 Go 构建高性能后端，Python 实现 AI 集成，React 打造现代化 Web 界面。

### 🎯 核心功能

| 模块 | 描述 |
|------|------|
| **🤖 AI 交易系统** | **全新！** 自主 AI 交易，具备自我学习和策略进化能力 |
| **📡 信号监控** | 实时监控 ValueScan API 的交易信号，支持 Telegram 通知 |
| **🧠 AI 市场摘要** | 使用 GPT/Claude 自动生成市场分析，六维度量化分析 |
| **💹 自动交易** | 币安合约交易机器人，支持加仓、移动止损和风险管理 |
| **📋 Telegram 跟单** | 从 Telegram 信号频道复制交易到您的交易所账户 |
| **🔄 保活系统** | 健康监控和服务自动重启 |
| **📊 模拟模式** | 使用虚拟资金进行策略测试 |

---

## ✨ 功能特性

### 🤖 AI 交易系统（全新！）

**由 AI 驱动的完全自主交易，具备自我学习能力**

#### 核心功能：
- **AI 模式**：完全 AI 控制，禁用手动策略
- **币种黑名单**：排除特定币种
- **AI 仓位代理**：自主仓位管理
  - 每 5 分钟分析持仓
  - AI 决策：持有 / 加仓 / 减仓 / 平仓
  - 综合考虑开仓价、当前价、盈亏、止损、止盈
- **绩效追踪**：SQLite 数据库记录所有 AI 交易
  - 完整的交易历史和 AI 分析
  - 仓位操作日志
  - 学习会话记录
- **AI 进化引擎**：自我学习系统优化策略
  - 自动分析交易模式
  - 通过 AI 生成优化建议
  - A/B 测试新策略
  - 可配置进化间隔（默认：24 小时）

#### 策略配置（6 种选项）：

| 策略 | 风险 | 收益潜力 | 交易频率 | 持仓时间 | 适用人群 |
|------|------|----------|----------|----------|----------|
| **保守剥头皮** | ⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | 1-5 分钟 | 保守短线 |
| **保守波段** | ⭐ | ⭐⭐⭐ | ⭐⭐ | 2-10 天 | 保守中线 |
| **平衡日内** ⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | 1-8 小时 | **推荐** |
| **平衡波段** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | 2-10 天 | 上班族 |
| **激进剥头皮** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 1-5 分钟 | 专业交易者 |
| **激进日内** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 1-8 小时 | 激进交易者 |

**快速启动**：
```python
# binance_trader/config.py
ENABLE_AI_MODE = True
ENABLE_AI_POSITION_AGENT = True
ENABLE_AI_EVOLUTION = True
AI_EVOLUTION_PROFILE = "balanced_day"  # 推荐
```

📚 **详细文档**：[AI 交易系统指南](AI_TRADING_SYSTEM.md)

---

### 📡 信号监控
- 实时轮询 ValueScan 交易信号
- 多频道 Telegram 通知，附带 TradingView 图表
- 按类型过滤信号（看涨、看跌、套利、巨鲸）
- 重复检测和智能消息格式化
- 移动列表追踪（Alpha 和 FOMO 币种）
- **AI 信号转发**：自动将 AI 分析转发到交易系统

### 🧠 AI 市场摘要
- 每小时发送 AI 生成的市场分析到 Telegram
- **六维度分析**：
  1. 市场情绪
  2. 资金流向
  3. 技术信号
  4. 巨鲸活动
  5. 新闻影响
  6. 风险评估
- 集成多个数据源：
  - **ValueScan 信号** - 交易信号统计
  - **NOFX 量化 API** - 资金流、持仓量、价格数据
  - **CryptoCompare** - 加密货币新闻
  - **CoinGecko** - 热门币种和市场数据
- 支持 OpenAI、Claude、DeepSeek 等兼容 API

### 💹 自动交易
- **币安合约**支持 USDT 本位永续合约
- 可配置仓位级别的加仓策略
- 动态移动止损与激活阈值
- 多级止盈（TP1、TP2、TP3）部分平仓
- 止损与保证金率监控
- 基于账户余额的仓位管理
- **AI 模式集成**：与 AI 交易系统无缝集成

### 🔄 Telegram 跟单
- 监控 Telegram 群组/频道的交易信号
- 自动信号解析和交易执行
- 可配置杠杆的仓位管理
- 黑名单/白名单币种过滤

### 📊 Web 仪表盘
- 实时信号展示和统计
- 服务状态监控（启动/停止/重启）
- 可视化配置管理
- **AI 交易配置**：专用"AI 交易"标签页
  - AI 模式设置
  - 仓位代理配置
  - 进化系统设置
  - 策略配置选择器
  - 学习参数
  - A/B 测试选项
- 日志查看器与过滤功能
- 多语言支持（EN/中文/日本語）

---

## 🏗 系统架构

```
valuescan/
├── api/                    # REST API 服务器 (Python Flask)
│   ├── server.py           # 主 API 端点
│   └── metrics_calculator.py
│
├── signal_monitor/         # 信号监控模块 (Python)
│   ├── polling_monitor.py  # 主轮询循环
│   ├── message_handler.py  # 信号处理
│   ├── telegram.py         # Telegram 集成
│   ├── ai_market_summary.py # AI 摘要生成
│   ├── ai_signal_forwarder.py # AI 信号转发
│   └── database.py         # SQLite 存储
│
├── binance_trader/         # 交易机器人 (Python)
│   ├── futures_main.py     # 主交易循环（集成 AI）
│   ├── futures_trader.py   # 订单执行
│   ├── signal_aggregator.py # 信号融合
│   ├── trailing_stop.py    # 移动止损逻辑
│   ├── risk_manager.py     # 风险管理
│   │
│   └── AI 交易系统：
│       ├── ai_mode_handler.py        # AI 模式信号处理
│       ├── ai_position_agent.py      # AI 仓位管理
│       ├── ai_performance_tracker.py # 绩效追踪
│       ├── ai_evolution_engine.py    # 自我学习引擎
│       └── ai_evolution_profiles.py  # 策略配置
│
├── keepalive/              # 健康监控 (Python)
│   ├── health.py           # 服务健康检查
│   └── alerter.py          # 告警通知
│
├── simulation/             # 模拟交易 (Python)
│   ├── simulator.py        # 交易模拟
│   └── api_routes.py       # 模拟 API
│
├── telegram_copytrade/     # 跟单模块 (Python)
│   └── copytrade_main.py   # Telegram 监听器
│
├── web/                    # 前端 (React + TypeScript)
│   ├── src/
│   │   ├── components/     # UI 组件
│   │   │   └── valuescan/
│   │   │       └── AITradingConfigSection.tsx # AI 配置界面
│   │   ├── pages/          # 页面视图
│   │   │   └── SettingsPage.tsx # 含 AI 标签页
│   │   └── lib/            # API 客户端和工具
│   └── dist/               # 生产构建
│
├── provider/               # 数据提供者 (Go)
│   └── coinank/            # CoinAnk API 客户端
│
├── trader/                 # Go 交易模块
├── backtest/               # 回测引擎
├── mcp/                    # MCP (Model Context Protocol)
└── scripts/                # 工具脚本
    └── deploy_ai_trading_system.py # AI 系统部署脚本
```

### 数据流

```
1. 信号流：
   ValueScan API → polling_monitor → message_handler → Telegram + 数据库 + IPC

2. AI 交易流：
   AI 信号分析 → ai_signal_forwarder → IPC → ai_mode_handler → futures_trader → 币安

3. AI 进化流：
   交易数据 → ai_performance_tracker → ai_evolution_engine → 策略优化 → A/B 测试

4. AI 摘要流：
   多数据源 → ai_market_summary → Telegram

5. Web 仪表盘：
   React 前端 → Flask API → Python 服务
```

---

## 🚀 快速开始

### 环境要求

- **Python 3.9+** 和 pip
- **Node.js 18+** 和 npm
- **Go 1.21+**（可选，用于 Go 模块）
- **Telegram Bot Token**（用于通知）
- **币安 API 密钥**（用于交易）
- **AI API 密钥**（OpenAI/Claude/DeepSeek，用于 AI 功能）

### 安装

```bash
# 克隆仓库
git clone https://github.com/ymylive/valuescan.git
cd valuescan

# 安装 Python 依赖
pip install -r requirements.txt

# 安装前端依赖
cd web && npm install && cd ..

# 复制环境配置
cp .env.example .env
```

### 配置

编辑 `.env` 并配置：

```bash
# Telegram 配置
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# ValueScan API（信号监控必需）
VALUESCAN_API_URL=https://api.valuescan.io

# 币安 API（交易必需）
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret

# AI API（AI 功能必需）
AI_API_KEY=your_openai_or_claude_key
AI_API_URL=https://api.openai.com/v1/chat/completions
AI_MODEL=gpt-4o-mini
```

### 配置 AI 交易系统

```bash
# 复制示例配置
cd binance_trader
cp config.example.py config.py

# 编辑 config.py 启用 AI 功能
nano config.py
```

**核心 AI 配置**：
```python
# AI 模式
ENABLE_AI_MODE = True
COIN_BLACKLIST = ["DOGE", "SHIB"]  # 可选

# AI 仓位代理
ENABLE_AI_POSITION_AGENT = True
AI_POSITION_CHECK_INTERVAL = 300  # 5 分钟

# AI 进化
ENABLE_AI_EVOLUTION = True
AI_EVOLUTION_PROFILE = "balanced_day"  # 推荐
AI_EVOLUTION_MIN_TRADES = 50
AI_EVOLUTION_LEARNING_PERIOD_DAYS = 30
AI_EVOLUTION_INTERVAL_HOURS = 24
ENABLE_AI_AB_TESTING = True
AI_AB_TEST_RATIO = 0.2  # 20% 测试比例
```

### 启动服务

```bash
# 启动 API 服务器
python -m api.server

# 启动信号监控（含 AI 信号转发）
python -m signal_monitor.polling_monitor

# 启动 AI 交易机器人
python -m binance_trader.futures_main

# 启动 Web 前端
cd web && npm run dev
```

访问仪表盘：**http://localhost:3000**

### 验证 AI 系统

```bash
# 检查日志中的 AI 系统初始化
tail -f logs/trader.log | grep -E "AI|🤖|🧬"

# 预期输出：
# 🤖 AI 模式已启用
# 🤖 AI 仓位代理已启用
# 🧬 AI 进化系统已启用
# 🧬 进化策略: balanced_day
```

---

## ⚙️ 配置说明

### AI 交易系统配置

| 选项 | 描述 | 默认值 |
|------|------|--------|
| `ENABLE_AI_MODE` | 启用完全 AI 控制 | `False` |
| `COIN_BLACKLIST` | 排除交易的币种 | `[]` |
| `ENABLE_AI_POSITION_AGENT` | 启用 AI 仓位管理 | `False` |
| `AI_POSITION_CHECK_INTERVAL` | 仓位检查间隔（秒） | `300` |
| `ENABLE_AI_EVOLUTION` | 启用自我学习系统 | `False` |
| `AI_EVOLUTION_PROFILE` | 策略配置 | `"balanced_day"` |
| `AI_EVOLUTION_MIN_TRADES` | 学习前最小交易数 | `50` |
| `AI_EVOLUTION_LEARNING_PERIOD_DAYS` | 学习周期 | `30` |
| `AI_EVOLUTION_INTERVAL_HOURS` | 进化间隔 | `24` |
| `ENABLE_AI_AB_TESTING` | 启用 A/B 测试 | `True` |
| `AI_AB_TEST_RATIO` | 测试比例 (0-1) | `0.2` |

### 信号监控配置

| 选项 | 描述 | 默认值 |
|------|------|--------|
| `telegram_bot_token` | Telegram Bot API token | 必需 |
| `telegram_chat_id` | 目标聊天/频道 ID | 必需 |
| `enable_telegram` | 启用 Telegram 通知 | `true` |
| `chrome_debug_port` | Chrome DevTools 截图端口 | `9222` |
| `enable_tradingview_chart` | 包含 TradingView 图表 | `true` |

### AI 摘要配置

| 选项 | 描述 | 默认值 |
|------|------|--------|
| `enabled` | 启用 AI 市场摘要 | `false` |
| `api_key` | OpenAI/Claude API 密钥 | 必需 |
| `api_url` | API 端点 URL | OpenAI |
| `model` | 模型名称 | `gpt-4o-mini` |
| `interval_hours` | 摘要间隔 | `1` |
| `lookback_hours` | 数据回溯周期 | `1` |

### 交易配置

| 选项 | 描述 | 默认值 |
|------|------|--------|
| `leverage` | 交易杠杆 | `10` |
| `max_position_percent` | 最大仓位占余额百分比 | `10` |
| `stop_loss_percent` | 止损百分比 | `5` |
| `take_profit_1_percent` | 第一止盈级别 | `3` |
| `trailing_stop_activation` | 移动止损激活百分比 | `2` |
| `trailing_stop_callback` | 移动止损回调百分比 | `1` |

---

## 📡 API 参考

### AI 交易 API

```http
GET  /api/ai/performance?days=7        # 获取 AI 绩效统计
GET  /api/ai/evolution/history         # 获取进化历史
GET  /api/ai/evolution/config          # 获取进化配置
POST /api/ai/evolution/trigger         # 手动触发进化
```

### 信号监控 API

```http
GET  /api/config                      # 获取所有配置
POST /api/config                      # 保存配置

GET  /api/signals?limit=10            # 获取最近信号
GET  /api/alerts?limit=10             # 获取最近告警

GET  /api/valuescan/status            # 服务状态
POST /api/valuescan/signal/start      # 启动信号监控
POST /api/valuescan/signal/stop       # 停止信号监控
```

### AI 摘要 API

```http
GET  /api/valuescan/ai-summary/config     # 获取 AI 摘要配置
POST /api/valuescan/ai-summary/config     # 保存 AI 摘要配置
POST /api/valuescan/ai-summary/trigger    # 手动触发摘要
```

### 交易 API

```http
GET  /api/trader/positions            # 获取持仓
GET  /api/trader/balance              # 获取账户余额
POST /api/trader/start                # 启动交易机器人
POST /api/trader/stop                 # 停止交易机器人
```

---

## 🚢 部署

### 快速部署（VPS）

```bash
# 部署 AI 交易系统到 VPS
python scripts/deploy_ai_trading_system.py

# 在 VPS 上配置
ssh root@your-vps.com
cd /root/valuescan/binance_trader
cp config.example.py config.py
nano config.py  # 设置 ENABLE_AI_MODE=True 等

# 重启服务
systemctl restart valuescan-signal
systemctl restart valuescan-trader
systemctl restart valuescan-api

# 验证
journalctl -u valuescan-trader -f | grep -E "AI|🤖|🧬"
```

### Systemd 服务

```bash
# 复制服务文件
sudo cp valuescan-*.service /etc/systemd/system/

# 启用并启动服务
sudo systemctl enable valuescan-api valuescan-signal valuescan-trader
sudo systemctl start valuescan-api valuescan-signal valuescan-trader

# 检查状态
sudo systemctl status valuescan-trader
```

### Docker 部署

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### Nginx 配置

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    root /var/www/valuescan;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

---

## 📚 文档

### AI 交易系统
- [AI 交易系统概述](AI_TRADING_SYSTEM.md) - 完整系统架构
- [AI 进化系统](AI_EVOLUTION_SYSTEM.md) - 自我学习引擎详情
- [AI 进化策略](AI_EVOLUTION_STRATEGIES.md) - 策略配置指南
- [VPS 部署指南](AI_TRADING_VPS_DEPLOYMENT.md) - 完整部署说明
- [部署检查清单](AI_TRADING_DEPLOYMENT_CHECKLIST.md) - 分步检查清单
- [快速入门指南](AI_TRADING_QUICK_START.md) - 快速设置指南
- [实现摘要](AI_TRADING_IMPLEMENTATION_SUMMARY.md) - 技术细节

### 通用
- [CLAUDE.md](CLAUDE.md) - 项目概述和开发指南
- [CONTRIBUTING.md](CONTRIBUTING.md) - 贡献指南

---

## 📁 项目结构

| 目录 | 语言 | 描述 |
|------|------|------|
| `api/` | Python | REST API 服务器（Flask） |
| `signal_monitor/` | Python | 信号轮询和处理 |
| `binance_trader/` | Python | 币安合约交易机器人（含 AI） |
| `keepalive/` | Python | 服务健康监控 |
| `simulation/` | Python | 模拟交易 |
| `telegram_copytrade/` | Python | Telegram 信号跟单 |
| `web/` | TypeScript/React | Web 仪表盘前端 |
| `provider/` | Go | 外部数据提供者 |
| `trader/` | Go | 高性能交易 |
| `backtest/` | Go | 策略回测 |
| `mcp/` | Go | Model Context Protocol |
| `scripts/` | Python | 工具和部署脚本 |

---

## 🗄️ 数据库结构

### AI 绩效数据库 (`ai_performance.db`)

**ai_trades** - 完整 AI 交易历史
```sql
trade_id, symbol, direction, entry_time, entry_price, entry_quantity,
ai_analysis, ai_confidence, ai_stop_loss, ai_take_profit, ai_risk_level,
exit_time, exit_price, exit_quantity, exit_reason,
realized_pnl, realized_pnl_percent, market_conditions, status
```

**ai_position_actions** - 仓位管理操作
```sql
action_id, trade_id, action_time, action_type, ai_reason, ai_confidence,
quantity_before, quantity_after, price, market_conditions
```

**ai_learning_sessions** - 进化历史
```sql
session_id, start_time, end_time, trades_analyzed, patterns_discovered,
insights, old_parameters, new_parameters, expected_improvement,
actual_improvement, validation_period_days, status
```

---

## 🔐 安全

- **API 密钥**：存储在环境变量或 `.env` 文件中（切勿提交）
- **Telegram**：使用受限权限的 bot token
- **交易所**：启用 IP 白名单和提现限制
- **代理**：支持 SOCKS5/HTTP 代理用于受限地区
- **AI 数据**：绩效数据库本地存储，权限受限

---

## 📊 数据来源

| 来源 | 数据类型 | 用途 |
|------|----------|------|
| **ValueScan API** | 交易信号 | 信号监控 |
| **NOFX API** | 资金流、OI、价格 | AI 市场摘要 |
| **CryptoCompare** | 新闻标题 | AI 市场摘要 |
| **CoinGecko** | 热门币种 | AI 市场摘要 |
| **币安 API** | 市场数据、交易 | 自动交易 |
| **OpenAI/Claude** | AI 分析 | AI 交易和摘要 |

---

## 🎯 使用场景

### 1. 自主 AI 交易
```python
# 设置后无需干预 - AI 处理一切
ENABLE_AI_MODE = True
ENABLE_AI_POSITION_AGENT = True
ENABLE_AI_EVOLUTION = True
AI_EVOLUTION_PROFILE = "balanced_day"
```

### 2. 仅信号监控
```python
# 只监控信号，不交易
ENABLE_AI_MODE = False
# 仅配置 signal_monitor
```

### 3. AI 辅助手动交易
```python
# AI 提供分析，您做决定
ENABLE_AI_MODE = False
# 将 AI 信号作为参考
```

### 4. AI 模拟交易
```python
# 无风险测试 AI 策略
# 使用模拟模式
```

---

## 📈 绩效监控

### 查看 AI 绩效

```bash
# 通过日志
journalctl -u valuescan-trader -f | grep "AI 性能"

# 通过 Python
cd binance_trader
python3 -c "
from ai_performance_tracker import AIPerformanceTracker
tracker = AIPerformanceTracker()
stats = tracker.get_performance_stats(days=7)
print(f'胜率: {stats[\"win_rate\"]:.2f}%')
print(f'总盈亏: {stats[\"total_pnl\"]:.2f}')
"
```

### 查看进化历史

```bash
cd binance_trader
cat data/ai_evolution_config.json | python3 -m json.tool
```

### 数据库查询

```bash
# 检查交易数量
sqlite3 data/ai_performance.db "SELECT COUNT(*) FROM ai_trades;"

# 查看最近交易
sqlite3 data/ai_performance.db "SELECT * FROM ai_trades ORDER BY entry_time DESC LIMIT 10;"
```

---

## 🤝 贡献

欢迎贡献！请阅读我们的 [贡献指南](CONTRIBUTING.md) 了解：

- 代码风格和规范
- Pull Request 流程
- Issue 报告
- AI 系统开发指南

---

## 📄 许可证

本项目采用 **GNU AGPL-3.0** 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

## 📞 支持

- **Issues**：[GitHub Issues](https://github.com/ymylive/valuescan/issues)
- **Telegram**：[开发者社区](https://t.me/valuescan_dev)
- **文档**：参见上方 [文档](#文档) 部分

---

## 🙏 致谢

- **OpenAI/Anthropic** - AI 模型提供商
- **币安** - 交易所 API
- **ValueScan** - 信号数据提供商
- **NOFX** - 量化数据提供商
- **社区贡献者** - 感谢您的支持！

---

## 🗺️ 路线图

- [x] 实时信号监控
- [x] AI 市场摘要
- [x] 自动交易
- [x] **AI 自主交易系统**
- [x] **AI 自我学习和进化**
- [x] **6 种策略配置**
- [ ] 多交易所支持
- [ ] 高级回测
- [ ] 移动应用
- [ ] 策略市场
- [ ] 社交交易功能

---

<p align="center">
  <strong>由 ValueScan 团队用 ❤️ 打造</strong>
</p>

<p align="center">
  <sub>⭐ 如果您觉得这个项目有用，请在 GitHub 上给我们点个星！</sub>
</p>

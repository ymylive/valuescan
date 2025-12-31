# AI 服务配置总结

## 配置完成时间
2025-12-31

## 配置的 AI 服务

### 1. AI 主力关键位服务 ✅

**配置文件**: `signal_monitor/ai_key_levels_config.py`

**配置内容**:
- API URL: `https://chat.cornna.xyz/gemini/v1/chat/completions`
- API Key: `Qq159741`
- Model: `gemini-3-flash-preview-search`
- 状态: 已启用

**环境变量** (可选):
```bash
export VALUESCAN_AI_LEVELS_ENABLED=1
export VALUESCAN_AI_LEVELS_API_KEY=Qq159741
export VALUESCAN_AI_LEVELS_API_URL=https://chat.cornna.xyz/gemini/v1/chat/completions
export VALUESCAN_AI_LEVELS_MODEL=gemini-3-flash-preview-search
```

---

### 2. AI 简评服务 ✅

**配置文件**: `signal_monitor/ai_signal_config.json`

**配置内容**:
```json
{
  "enabled": true,
  "api_key": "Qq159741",
  "api_url": "https://chat.cornna.xyz/gemini/v1/chat/completions",
  "model": "gemini-3-pro-preview-search",
  "interval_hours": 1.0,
  "lookback_hours": 1.0
}
```

**功能**: 为每个交易信号生成专业的 AI 简评

---

### 3. 市场分析服务 ✅

**配置文件**: `signal_monitor/ai_market_summary_config.json`

**配置内容**:
```json
{
  "enabled": true,
  "interval_hours": 1,
  "api_key": "Qq159741",
  "api_url": "https://chat.cornna.xyz/gemini/v1/chat/completions",
  "model": "gemini-3-pro-preview-search",
  "lookback_hours": 48
}
```

**功能**: 定期生成市场整体分析报告

---

## 配置说明

### API 配置对照表

| 服务 | API URL | API Key | Model |
|------|---------|---------|-------|
| AI主力关键位 | gemini/v1 | Qq159741 | gemini-3-flash-preview-search |
| AI简评 | gemini/v1 | Qq159741 | gemini-3-pro-preview-search |
| 市场分析 | gemini/v1 | Qq159741 | gemini-3-pro-preview-search |

### 生图服务说明

**生图服务使用 TradingView 的 chart-img.com API，不是 AI 服务**

配置位置: `signal_monitor/config.py`

```python
# TradingView 图表配置
ENABLE_TRADINGVIEW_CHART = True
CHART_IMG_API_KEY = ""  # 从 https://www.chart-img.com/ 获取
CHART_IMG_LAYOUT_ID = "oeTZqtUR"
CHART_IMG_WIDTH = 800
CHART_IMG_HEIGHT = 600
CHART_IMG_TIMEOUT = 90
```

### 启用/禁用服务

所有服务都可以通过配置文件中的 `enabled` 字段控制:
- `true`: 启用服务
- `false`: 禁用服务

---

## 下一步操作

1. **启动信号监控服务**:
   ```bash
   python -m signal_monitor.polling_monitor
   ```

2. **验证配置**:
   - 检查日志输出,确认 AI 服务正常调用
   - 观察 Telegram 消息,验证 AI 简评是否生成

3. **调整参数** (可选):
   - `interval_hours`: 调整服务运行频率
   - `lookback_hours`: 调整数据回溯时间
   - `temperature`: 调整 AI 创造性 (0.0-1.0)

---

## 故障排查

### 问题 1: AI 服务无响应
- 检查 API Key 是否正确
- 检查网络连接和代理设置
- 查看日志: `tail -f signal_monitor/valuescan.log`

### 问题 2: 配置未生效
- 确认配置文件路径正确
- 重启服务使配置生效
- 检查 JSON 格式是否正确

### 问题 3: API 调用失败
- 验证 API URL 是否可访问
- 检查 API Key 是否有效
- 确认模型名称是否正确

---

## 配置文件位置

```
signal_monitor/
├── ai_key_levels_config.py          # AI主力关键位配置
├── ai_signal_config.json            # AI简评配置
├── ai_market_summary_config.json    # 市场分析配置
└── ai_pattern_drawer.py             # 生图服务(代码配置)
```

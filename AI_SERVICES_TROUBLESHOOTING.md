# AI服务问题排查报告

## 更新时间
2025-12-31

## 问题描述

用户反馈:
1. ✅ Telegram能看到信号推送
2. ❌ AI主力位没有显示
3. ❌ AI简评没有显示
4. ❌ 生图服务没有生效
5. ❌ 市场分析服务没有生效
6. ⚠️ 日志中经常显示Token过期,但实际还在正常获取数据

---

## 已完成的检查

### 1. VPS代码同步 ✅
- 最新提交: `a6a072a`
- 代码已成功同步到VPS

### 2. AI服务配置检查 ✅

**AI简评配置** (`ai_signal_config.json`):
```json
{
  "enabled": true,
  "api_key": "Qq159741",
  "api_url": "https://chat.cornna.xyz/gemini/v1/chat/completions",
  "model": "gemini-3-pro-preview-search"
}
```

**AI主力关键位配置** (`ai_key_levels_config.py`):
```python
AI_LEVELS_ENABLED = True
AI_LEVELS_API_KEY = "Qq159741"
AI_LEVELS_API_URL = "https://chat.cornna.xyz/gemini/v1/chat/completions"
AI_LEVELS_MODEL = "gemini-3-flash-preview-search"
```

### 3. AI服务开关检查 ✅

VPS上的 `config.py` 中所有AI开关都已启用:
- `ENABLE_AI_KEY_LEVELS = True`
- `ENABLE_AI_SIGNAL_ANALYSIS = True`
- `ENABLE_AI_MARKET_ANALYSIS = True`
- `ENABLE_PRO_CHART = True`

### 4. VPS服务状态 ✅
- valuescan-monitor: active
- 服务已重启,配置已生效

---

## 问题分析

### 可能的原因

#### 1. AI服务调用条件未满足
AI服务可能需要特定条件才会触发:
- AI简评: 可能需要新信号才会生成
- AI主力位: 可能需要特定的信号类型
- 市场分析: 按时间间隔触发(1小时)

#### 2. 代理配置问题
AI API调用需要代理才能访问:
- 检查VPS是否配置了代理
- 检查代理是否正常工作

#### 3. API调用失败
- API Key可能无效
- API URL可能无法访问
- 网络连接问题

---

## 下一步排查建议

### 1. 检查代理配置
```bash
# 在VPS上检查
echo $HTTP_PROXY
echo $HTTPS_PROXY
```

### 2. 手动测试AI API
```bash
curl -X POST https://chat.cornna.xyz/gemini/v1/chat/completions \
  -H "Authorization: Bearer Qq159741" \
  -H "Content-Type: application/json" \
  -d '{"model":"gemini-3-pro-preview-search","messages":[{"role":"user","content":"test"}]}'
```

### 3. 查看详细日志
```bash
# 查看完整日志
journalctl -u valuescan-monitor -f

# 查看AI相关日志
journalctl -u valuescan-monitor | grep -i "ai\|简评\|主力位\|market"
```

### 4. 检查本地服务
本地服务是否有AI输出?
- 查看本地CMD窗口的日志
- 检查是否有AI API调用

---

## Token过期问题

### 现象
日志显示Token过期,但实际还在正常获取数据

### 可能原因
1. Token刷新机制正常工作
2. 日志中的"过期"是检测到过期后立即刷新的正常流程
3. 不影响实际功能

### 建议
这是正常现象,Token刷新服务会自动处理过期问题。

---

## 待确认事项

1. [ ] VPS是否配置了代理?
2. [ ] AI API是否可以从VPS访问?
3. [ ] 本地服务是否有AI输出?
4. [ ] 是否有新的信号触发AI服务?

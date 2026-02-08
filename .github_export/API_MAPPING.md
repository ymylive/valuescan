# ValueScan 前后端 API 对接文档

## 文档说明
本文档记录了前端页面与后端API的对接情况，确保所有数据项和配置项准确对接。

**更新日期**: 2025-12-31
**baseURL**: `/api` (已在 api.ts 中配置)

---

## 1. Clash 代理管理 (ProxyPage.tsx)

### 1.1 获取 Clash 配置
- **前端调用**: `api.get('/clash/config')`
- **后端路由**: `GET /api/clash/config`
- **状态**: ✅ 已对接
- **响应格式**:
```json
{
  "port": 7890,
  "socksPort": 7891,
  "allowLan": false,
  "mode": "rule",
  "logLevel": "info",
  "externalController": "127.0.0.1:9090",
  "secret": "",
  "subscriptions": [],
  "autoTest": true,
  "autoTestInterval": 30,
  "testUrl": "http://www.gstatic.com/generate_204",
  "testTimeout": 5,
  "selectedProxy": "node-id"
}
```

### 1.2 保存 Clash 配置
- **前端调用**: `api.post('/clash/config', config)`
- **后端路由**: `POST /api/clash/config`
- **状态**: ✅ 已对接
- **请求格式**: 同上
- **响应格式**: `{ "success": true }`

### 1.3 获取节点列表
- **前端调用**: `api.get('/clash/nodes')`
- **后端路由**: `GET /api/clash/nodes`
- **状态**: ✅ 已对接
- **响应格式**:
```json
[
  {
    "id": "node-1",
    "name": "节点名称",
    "type": "ss",
    "server": "example.com",
    "port": 8388,
    "cipher": "aes-256-gcm",
    "password": "password",
    "subscriptionId": "sub-1",
    "delay": 100,
    "available": true,
    "lastTest": 1234567890
  }
]
```

### 1.4 保存节点列表
- **前端调用**: `api.post('/clash/nodes', nodes)`
- **后端路由**: `POST /api/clash/nodes`
- **状态**: ✅ 已对接

### 1.5 更新订阅
- **前端调用**: `api.post('/clash/subscription/update', { url, type })`
- **后端路由**: `POST /api/clash/subscription/update`
- **状态**: ✅ 已对接 (已添加代理支持)
- **请求格式**:
```json
{
  "url": "https://example.com/subscription",
  "type": "clash"
}
```
- **响应格式**:
```json
{
  "nodes": [...],
  "count": 10
}
```

### 1.6 测试节点
- **前端调用**: `api.post('/clash/test-node', { nodeId })`
- **后端路由**: `POST /api/clash/test-node`
- **状态**: ✅ 已对接 (新增)
- **请求格式**: `{ "nodeId": "node-1" }`
- **响应格式**:
```json
{
  "nodeId": "node-1",
  "delay": 100,
  "success": true,
  "timestamp": 1234567890000
}
```

### 1.7 获取统计信息
- **前端调用**: `api.get('/clash/stats')`
- **后端路由**: `GET /api/clash/stats`
- **状态**: ✅ 已对接
- **响应格式**:
```json
{
  "uploadTotal": 0,
  "downloadTotal": 0,
  "connections": 0,
  "uploadSpeed": 0,
  "downloadSpeed": 0
}
```

---

## 2. 服务管理 (ServicesPage.tsx)

### 2.1 获取服务状态
- **前端调用**: `fetch('/api/services/status')`
- **后端路由**: `GET /api/services/status`
- **状态**: ✅ 已对接 (已修复 Windows/Linux 兼容性)
- **响应格式**:
```json
{
  "valuescan-monitor": "running",
  "valuescan-trader": "stopped",
  "valuescan-api": "running",
  "valuescan-token-refresher": "stopped"
}
```

### 2.2 启动服务
- **前端调用**: `fetch('/api/services/start', { method: 'POST', body: { service } })`
- **后端路由**: `POST /api/services/start`
- **状态**: ✅ 已对接 (已添加防重复启动)
- **请求格式**: `{ "service": "valuescan-monitor" }`
- **响应格式**: `{ "message": "服务启动成功" }`

### 2.3 停止服务
- **前端调用**: `fetch('/api/services/stop', { method: 'POST', body: { service } })`
- **后端路由**: `POST /api/services/stop`
- **状态**: ✅ 已对接
- **请求格式**: `{ "service": "valuescan-monitor" }`
- **响应格式**: `{ "message": "服务停止成功" }`

### 2.4 重启服务
- **前端调用**: `fetch('/api/services/restart', { method: 'POST', body: { service } })`
- **后端路由**: `POST /api/services/restart`
- **状态**: ✅ 已对接
- **请求格式**: `{ "service": "valuescan-monitor" }`
- **响应格式**: `{ "message": "服务重启成功" }`

---

## 3. 日志管理 (LogsPage.tsx)

### 3.1 获取服务日志
- **前端调用**: `api.get('/logs/${service}?lines=2000')`
- **后端路由**: `GET /api/logs/<service>`
- **状态**: ✅ 已对接
- **查询参数**: `lines` (默认100, 最大2000)
- **响应格式**:
```json
{
  "logs": [
    {
      "timestamp": 1234567890000,
      "level": "6",
      "component": "signal",
      "message": "日志消息",
      "data": {
        "unit": "valuescan-signal.service",
        "pid": "12345"
      }
    }
  ],
  "service": "signal",
  "count": 100
}
```

**注意**: 前端有 `convertPriorityToLevel()` 函数将 syslog priority 转换为日志级别。

---

## 4. 仪表盘 (Dashboard.tsx)

### 4.1 获取数据库状态
- **前端调用**: `api.get('/db/status')`
- **后端路由**: `GET /api/db/status`
- **状态**: ✅ 已对接

### 4.2 获取信号列表
- **前端调用**: `api.get('/signals', { params: { limit: 5 } })`
- **后端路由**: `GET /api/signals`
- **状态**: ✅ 已对接

### 4.3 获取告警列表
- **前端调用**: `api.get('/alerts', { params: { limit: 5 } })`
- **后端路由**: `GET /api/alerts`
- **状态**: ✅ 已对接

---

## 待检查的页面

以下页面需要继续检查API对接情况:
- [x] PerformanceStats.tsx - 无API调用
- [ ] ConfigurationPage.tsx
- [x] Dashboard.tsx - 已验证
- [ ] PositionMonitor.tsx
- [ ] TradingHistory.tsx

---

## 修复记录

### 2025-12-31
1. ✅ 添加 `/api/clash/test-node` 端点
2. ✅ 修复 Clash 订阅导入代理支持
3. ✅ 修复 Telegram 消息发送代理支持
4. ✅ 修复服务管理 Windows/Linux 兼容性
5. ✅ 添加防止重复启动服务的逻辑

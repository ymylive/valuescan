# 修复验证测试计划

## 测试日期
2025-12-31

## 修复内容概述

### 1. Clash 订阅导入功能
- ✅ 添加代理支持
- ✅ 支持环境变量配置
- ✅ 自动回退到直连

### 2. Telegram 消息发送
- ✅ 所有 Telegram API 调用添加代理支持
- ✅ 支持多种代理配置方式

### 3. 服务管理界面
- ✅ 支持 Windows 和 Linux 系统
- ✅ 防止重复启动服务
- ✅ 优化界面样式

## 测试步骤

### 测试 1: Clash 订阅导入
```bash
# 1. 启动后端服务
python -m api.server

# 2. 访问前端代理管理页面
# http://localhost:3000/proxy

# 3. 测试添加订阅
# - 输入订阅名称和 URL
# - 点击"添加订阅"
# - 验证节点是否成功导入
```

**预期结果**:
- 订阅成功导入
- 节点列表显示正确
- 如果代理失败,自动尝试直连

### 测试 2: Telegram 消息发送
```bash
# 1. 配置代理
# 方式1: 环境变量
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890

# 方式2: config.py
# HTTP_PROXY = "http://127.0.0.1:7890"

# 2. 启动信号监控
python -m signal_monitor.polling_monitor

# 3. 等待信号触发或手动测试
```

**预期结果**:
- Telegram 消息成功发送
- 使用配置的代理
- 日志显示代理连接成功

### 测试 3: 服务管理界面
```bash
# 1. 启动后端服务
python -m api.server

# 2. 访问服务管理页面
# http://localhost:3000/services

# 3. 测试功能
# - 查看服务状态(应该显示实际状态,不是"加载中")
# - 尝试启动已运行的服务(应该提示已在运行)
# - 停止服务
# - 重启服务
```

**预期结果**:
- 服务状态正确显示
- 防止重复启动
- 界面样式与整体一致

## 环境要求

### Python 依赖
```bash
pip install psutil
```

### 代理配置
确保以下之一可用:
1. 本地 Clash 代理 (127.0.0.1:7890)
2. 环境变量 HTTP_PROXY/HTTPS_PROXY
3. config.py 中的 HTTP_PROXY 配置

## 故障排查

### 问题 1: 订阅导入失败
- 检查代理是否正常运行
- 查看后端日志: `tail -f logs/api.log`
- 尝试直接访问订阅 URL

### 问题 2: Telegram 发送失败
- 检查代理配置
- 验证 TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID
- 查看日志: `tail -f signal_monitor/valuescan.log`

### 问题 3: 服务状态显示错误
- 确保 psutil 已安装
- 检查进程名称是否匹配
- 查看浏览器控制台错误

## 已知限制

1. **Windows 系统**:
   - 不支持通过界面启动/重启服务
   - 需要手动启动服务
   - 可以查看状态和停止服务

2. **Linux 系统**:
   - 需要 systemd 服务配置
   - 或者使用进程检测回退方案

## 修复文件清单

- `api/server.py` - 后端 API 修复
- `signal_monitor/telegram.py` - Telegram 代理支持
- `web/src/pages/ServicesPage.tsx` - 前端界面优化

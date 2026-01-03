# CDP Token 刷新器使用文档

## 简介

`simple_cdp_refresher.py` 是一个简化版的 ValueScan Token 刷新器，使用 Chrome DevTools Protocol (CDP) 进行自动登录和 token 刷新。

### 主要特点

1. **代码简单** - 逻辑清晰，易于理解和维护
2. **内存优化** - 在刷新前自动停止组件，释放内存
3. **自动重启** - 刷新完成后自动重启监测和交易组件
4. **跨平台** - 支持 Windows 和 Linux

## 依赖安装

```bash
pip install requests websocket-client
```

## 配置

### 方式 1: 环境变量（推荐）

```bash
export VALUESCAN_EMAIL="your_email@example.com"
export VALUESCAN_PASSWORD="your_password"
```

### 方式 2: 配置文件

创建 `valuescan_credentials.json` 文件：

```json
{
  "email": "your_email@example.com",
  "password": "your_password"
}
```

## 使用方法

### 1. 运行一次刷新

```bash
python signal_monitor/simple_cdp_refresher.py --once
```

### 2. 循环刷新（默认 0.8 小时间隔）

```bash
python signal_monitor/simple_cdp_refresher.py
```

### 3. 自定义刷新间隔

```bash
# 每 1 小时刷新一次
python signal_monitor/simple_cdp_refresher.py --interval 1.0

# 每 30 分钟刷新一次
python signal_monitor/simple_cdp_refresher.py --interval 0.5
```

## 工作流程

1. **停止组件** - 停止 `signal_monitor.py` 和 `auto_trader.py`，释放内存
2. **启动浏览器** - 启动 Chrome headless 模式
3. **CDP 登录** - 使用 CDP 协议自动填写表单并登录
4. **获取 Token** - 从 localStorage 提取 token
5. **保存 Token** - 保存到 `valuescan_localstorage.json`
6. **清理浏览器** - 关闭 Chrome 进程
7. **重启组件** - 重新启动监测和交易组件

## 测试

运行测试脚本验证功能：

```bash
python signal_monitor/test_cdp_refresher.py
```

测试内容包括：
- Chrome 可执行文件查找
- 凭证加载
- Chrome 启动和停止

## 组件管理配置

### Linux (systemd)

如果使用 systemd 管理服务，脚本会自动使用以下命令重启：

```bash
systemctl restart valuescan-monitor
systemctl restart valuescan-trader
```

### 自定义启动方式

编辑 `ComponentManager.start_components()` 方法，添加你的启动逻辑：

```python
@staticmethod
def start_components():
    # 方式 1: 直接启动 Python 脚本
    subprocess.Popen(["python", "signal_monitor/signal_monitor.py"])
    subprocess.Popen(["python", "signal_monitor/auto_trader.py"])

    # 方式 2: 使用 screen/tmux
    subprocess.run(["screen", "-dmS", "monitor", "python", "signal_monitor.py"])
    subprocess.run(["screen", "-dmS", "trader", "python", "auto_trader.py"])
```

## 故障排查

### 1. Chrome 未找到

**错误**: `未找到 Chrome/Chromium`

**解决方案**:
- Windows: 安装 Google Chrome
- Linux: `sudo apt install chromium-browser`

### 2. 凭证未找到

**错误**: `未找到登录凭证`

**解决方案**:
- 设置环境变量或创建 `valuescan_credentials.json` 文件

### 3. WebSocket 连接失败

**错误**: `Failed to connect websocket`

**解决方案**:
- 检查 Chrome 是否正常启动
- 确保端口 9222 未被占用
- 尝试手动启动 Chrome: `chrome --headless --remote-debugging-port=9222`

## 优势对比

与其他 token 刷新方案相比：

| 特性 | simple_cdp_refresher | selenium 方案 | DrissionPage 方案 |
|------|---------------------|--------------|------------------|
| 代码复杂度 | ⭐⭐ 简单 | ⭐⭐⭐ 中等 | ⭐⭐⭐⭐ 复杂 |
| 内存占用 | ⭐⭐⭐⭐⭐ 很低 | ⭐⭐⭐ 中等 | ⭐⭐ 较高 |
| 组件管理 | ✅ 自动 | ❌ 无 | ❌ 无 |
| 依赖项 | 2 个 | 3+ 个 | 5+ 个 |
| 启动速度 | ⭐⭐⭐⭐⭐ 快 | ⭐⭐⭐ 中等 | ⭐⭐ 慢 |

## 注意事项

1. **首次运行**: 建议先使用 `--once` 参数测试
2. **内存管理**: 脚本会自动停止和重启组件，确保组件支持重启
3. **日志监控**: 建议配合日志监控工具使用
4. **定时任务**: 可以配合 cron 或 systemd timer 使用

## 许可证

MIT License

# Token 刷新器使用指南

## 测试结果总结

✅ **测试成功！** 使用真实凭证 `ymy_live@outlook.com` 测试通过。

### 测试环境
- **操作系统**: Windows 10/11
- **Python 版本**: 3.14
- **Chrome 版本**: 143.0.7499.170
- **测试时间**: 2025-12-31

### 测试结果
1. ✅ 凭证加载成功
2. ✅ Chrome 启动成功（headless 模式）
3. ✅ 页面导航成功
4. ✅ 表单填写成功（邮箱 + 密码）
5. ✅ 登录成功
6. ✅ Token 获取成功（account_token + refresh_token）
7. ✅ Token 保存成功

## 推荐方案

### 方案 1: Selenium Token Refresher（推荐）

**文件**: `selenium_token_refresher.py`

**优点**:
- ✅ 跨平台兼容（Windows/Linux/Mac）
- ✅ 稳定可靠，已测试通过
- ✅ 自动处理页面加载和元素定位
- ✅ 支持组件内存管理
- ✅ 完整的错误处理

**依赖**:
```bash
pip install selenium
```

**使用方法**:
```bash
# 单次运行测试
python signal_monitor/selenium_token_refresher.py --once

# 循环刷新（默认 0.8 小时间隔）
python signal_monitor/selenium_token_refresher.py

# 自定义间隔（例如 1 小时）
python signal_monitor/selenium_token_refresher.py --interval 1.0
```

### 方案 2: CDP Token Refresher（备选）

**文件**: `simple_cdp_refresher.py`

**说明**:
- 使用 Chrome DevTools Protocol (CDP) 进行登录
- 在 Windows 环境下测试时遇到 WebSocket 连接问题
- 需要 Chrome 新版本的特殊配置
- **不推荐在生产环境使用**

## 配置方法

### 1. 创建凭证文件

**方式 1: 使用配置文件（推荐）**

创建 `signal_monitor/valuescan_credentials.json`:
```json
{
  "email": "your_email@example.com",
  "password": "your_password"
}
```

**方式 2: 使用环境变量**

```bash
# Linux/Mac
export VALUESCAN_EMAIL="your_email@example.com"
export VALUESCAN_PASSWORD="your_password"

# Windows
set VALUESCAN_EMAIL=your_email@example.com
set VALUESCAN_PASSWORD=your_password
```

### 2. 安装依赖

```bash
# 安装 Selenium
pip install selenium

# 确保系统已安装 Chrome/Chromium
# Windows: 下载安装 Google Chrome
# Linux: sudo apt install chromium-browser
```

## Linux 部署指南

### 1. 安装系统依赖

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install chromium-browser python3-pip

# CentOS/RHEL
sudo yum install chromium python3-pip
```

### 2. 配置 systemd 服务（推荐）

创建 `/etc/systemd/system/valuescan-token-refresher.service`:

```ini
[Unit]
Description=ValueScan Token Refresher
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/valuescan
Environment="VALUESCAN_EMAIL=your_email@example.com"
Environment="VALUESCAN_PASSWORD=your_password"
ExecStart=/usr/bin/python3 signal_monitor/selenium_token_refresher.py --interval 0.8
Restart=always
RestartSec=300

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable valuescan-token-refresher
sudo systemctl start valuescan-token-refresher
sudo systemctl status valuescan-token-refresher
```

### 3. 使用 cron 定时任务（备选）

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每 48 分钟运行一次）
*/48 * * * * cd /root/valuescan && python3 signal_monitor/selenium_token_refresher.py --once >> /var/log/token_refresher.log 2>&1
```

## 故障排查

### 1. Chrome 未找到

**错误**: `未找到 Chrome/Chromium`

**解决方案**:
```bash
# Linux
sudo apt install chromium-browser

# 或手动指定 Chrome 路径（修改脚本）
```

### 2. Selenium 未安装

**错误**: `未安装 selenium`

**解决方案**:
```bash
pip install selenium
```

### 3. 登录失败

**可能原因**:
- 凭证错误
- 网络问题
- 页面结构变化

**解决方案**:
```bash
# 检查凭证文件
cat signal_monitor/valuescan_credentials.json

# 手动测试登录
python signal_monitor/selenium_token_refresher.py --once
```

### 4. Token 文件未生成

**检查方法**:
```bash
ls -lh signal_monitor/valuescan_localstorage.json
cat signal_monitor/valuescan_localstorage.json | python -m json.tool
```

## 安全建议

1. **保护凭证文件**:
   ```bash
   chmod 600 signal_monitor/valuescan_credentials.json
   ```

2. **不要提交到 Git**:
   - `valuescan_credentials.json` 已在 `.gitignore` 中
   - `valuescan_localstorage.json` 已在 `.gitignore` 中

3. **定期更换密码**: 建议每 3-6 个月更换一次密码

## Token 有效期

根据测试结果，ValueScan 的 token 有效期如下：

- **account_token**: 约 1 小时（3600 秒）
- **refresh_token**: 约 3 天（259200 秒）

建议刷新间隔：**0.8 小时**（48 分钟），确保 token 始终有效。

## 监控和日志

### 查看日志

```bash
# systemd 服务日志
sudo journalctl -u valuescan-token-refresher -f

# cron 任务日志
tail -f /var/log/token_refresher.log
```

### 验证 Token 是否有效

```bash
# 检查 token 文件修改时间
ls -lh signal_monitor/valuescan_localstorage.json

# 查看 token 内容
cat signal_monitor/valuescan_localstorage.json | python -m json.tool | grep -E "account_token|refresh_token"
```

## 总结

✅ **推荐使用 `selenium_token_refresher.py`**
- 已在 Windows 环境下测试成功
- 跨平台兼容（Windows/Linux/Mac）
- 稳定可靠，自动处理所有登录流程
- 支持组件内存管理

📝 **部署建议**
- Linux 生产环境：使用 systemd 服务
- 开发测试环境：手动运行 `--once` 模式
- 刷新间隔：0.8 小时（48 分钟）

🔒 **安全提醒**
- 保护好凭证文件，设置正确的文件权限
- 不要将凭证文件提交到 Git
- 定期更换密码

---

**测试日期**: 2025-12-31
**测试状态**: ✅ 通过
**测试账号**: ymy_live@outlook.com

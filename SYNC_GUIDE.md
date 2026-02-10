# ValueScan VPS 同步指南

## 📋 需要同步的文件清单

### 1. AI 配置文件 (4个)

```
signal_monitor/ai_summary_config.json          # AI 简评配置 (GPT-5.2)
signal_monitor/ai_market_summary_config.json   # AI 市场分析配置 (Gemini Pro)
signal_monitor/ai_key_levels_config.json       # AI 主力位配置 (Gemini Flash)
signal_monitor/ai_overlays_config.json         # AI 画线配置 (Gemini Flash)
```

### 2. Python 代码文件 (4个)

```
signal_monitor/ai_market_summary.py            # 新增 get_ai_overlays_config() 函数
signal_monitor/chart_pro_v10.py                # 修改为使用 get_ai_overlays_config()
signal_monitor/ai_signal_analysis.py           # AI 简评生成模块
signal_monitor/ai_key_levels_config.py         # AI 主力位配置模块
```

### 3. 前端文件 (2个)

```
web/src/components/valuescan/SignalMonitorConfigSection.tsx  # 新增 20+ 配置字段
web/src/types/config.ts                                      # 配置类型定义
```

---

## 🚀 同步方法

### 方法 1: 使用自动同步脚本 (推荐)

#### Windows 用户:

1. 编辑 `sync_to_vps.bat`，修改 VPS 配置:
```batch
set VPS_HOST=your_vps_ip
set VPS_USER=root
set VPS_PORT=22
set VPS_PATH=/root/valuescan
```

2. 运行脚本:
```cmd
sync_to_vps.bat
```

#### Linux/Mac 用户:

1. 编辑 `sync_to_vps.sh`，修改 VPS 配置:
```bash
VPS_HOST="your_vps_ip"
VPS_USER="root"
VPS_PORT="22"
VPS_PATH="/root/valuescan"
```

2. 添加执行权限并运行:
```bash
chmod +x sync_to_vps.sh
./sync_to_vps.sh
```

---

### 方法 2: 手动使用 SCP 命令

#### 1. 同步 AI 配置文件

```bash
# 设置变量
VPS="root@your_vps_ip"
VPS_PATH="/root/valuescan"

# 同步 AI 配置
scp signal_monitor/ai_summary_config.json $VPS:$VPS_PATH/signal_monitor/
scp signal_monitor/ai_market_summary_config.json $VPS:$VPS_PATH/signal_monitor/
scp signal_monitor/ai_key_levels_config.json $VPS:$VPS_PATH/signal_monitor/
scp signal_monitor/ai_overlays_config.json $VPS:$VPS_PATH/signal_monitor/
```

#### 2. 同步 Python 代码

```bash
scp signal_monitor/ai_market_summary.py $VPS:$VPS_PATH/signal_monitor/
scp signal_monitor/chart_pro_v10.py $VPS:$VPS_PATH/signal_monitor/
scp signal_monitor/ai_signal_analysis.py $VPS:$VPS_PATH/signal_monitor/
scp signal_monitor/ai_key_levels_config.py $VPS:$VPS_PATH/signal_monitor/
```

#### 3. 同步前端文件

```bash
scp web/src/components/valuescan/SignalMonitorConfigSection.tsx \
    $VPS:$VPS_PATH/web/src/components/valuescan/

scp web/src/types/config.ts $VPS:$VPS_PATH/web/src/types/
```

---

### 方法 3: 使用 rsync (更高效)

```bash
# 同步整个 signal_monitor 目录
rsync -avz --progress \
  --include='ai*.json' \
  --include='ai*.py' \
  --include='chart_pro_v10.py' \
  signal_monitor/ $VPS:$VPS_PATH/signal_monitor/

# 同步前端文件
rsync -avz --progress \
  web/src/components/valuescan/SignalMonitorConfigSection.tsx \
  web/src/types/config.ts \
  $VPS:$VPS_PATH/web/src/
```

---

### 方法 4: 使用 Git (如果 VPS 有 Git 仓库)

```bash
# 在本地提交更改
git add .
git commit -m "feat: add AI config management and frontend enhancements"
git push

# 在 VPS 上拉取更新
ssh $VPS "cd $VPS_PATH && git pull"
```

---

## ✅ 同步后验证

### 1. 验证 AI 配置文件

```bash
ssh $VPS "cd $VPS_PATH && ls -lh signal_monitor/ai*config*.json"
```

预期输出:
```
-rw-r--r-- 1 root root  158 Dec 28 11:17 ai_key_levels_config.json
-rw-r--r-- 1 root root  211 Dec 28 11:18 ai_market_summary_config.json
-rw-r--r-- 1 root root  158 Dec 28 11:21 ai_overlays_config.json
-rw-r--r-- 1 root root  192 Dec 28 09:54 ai_summary_config.json
```

### 2. 验证 AI 配置加载

```bash
ssh $VPS "cd $VPS_PATH/signal_monitor && python3 -c '
from ai_market_summary import get_ai_summary_config, get_ai_market_config, get_ai_overlays_config
from ai_key_levels_config import get_ai_levels_config
print(\"AI 简评:\", get_ai_summary_config().get(\"model\"))
print(\"AI 市场:\", get_ai_market_config().get(\"model\"))
print(\"AI 主力位:\", get_ai_levels_config().get(\"model\"))
print(\"AI 画线:\", get_ai_overlays_config().get(\"model\"))
'"
```

预期输出:
```
AI 简评: gpt-5.2
AI 市场: gemini-3-flash-preview-search
AI 主力位: gemini-3-flash-preview-search
AI 画线: gemini-3-flash-preview-search
```

### 3. 测试 AI 简评功能

```bash
ssh $VPS "cd $VPS_PATH/signal_monitor && python3 -c '
from ai_signal_analysis import analyze_signal
result = analyze_signal(symbol=\"BTC\", signal_payload={\"type\": 108, \"price\": 95000})
if result:
    print(\"✅ AI 简评测试成功\")
    print(\"分析长度:\", len(result.get(\"analysis\", \"\")), \"字符\")
else:
    print(\"❌ AI 简评测试失败\")
'"
```

---

## 🔄 同步后操作

### 1. 重启服务

```bash
# SSH 登录到 VPS
ssh root@your_vps_ip

# 重启 signal_monitor 服务
systemctl restart valuescan-signal

# 重启 API 服务器
systemctl restart valuescan-api

# 检查服务状态
systemctl status valuescan-signal
systemctl status valuescan-api
```

### 2. 重新构建前端 (如果修改了前端)

```bash
# SSH 登录到 VPS
ssh root@your_vps_ip

# 进入项目目录
cd /root/valuescan/web

# 安装依赖 (如果需要)
npm install

# 构建前端
npm run build

# 重启 API 服务器以使用新的前端
systemctl restart valuescan-api
```

### 3. 查看日志

```bash
# 查看 signal_monitor 日志
journalctl -u valuescan-signal -f

# 查看 API 日志
journalctl -u valuescan-api -f

# 查看应用日志
tail -f /root/valuescan/signal_monitor/valuescan.log
```

---

## 📊 同步内容总结

### AI 配置更新

| 配置文件 | 模型 | API Key | 用途 |
|---------|------|---------|------|
| ai_summary_config.json | gpt-5.2 | sk-chat2api | AI 简评 |
| ai_market_summary_config.json | gemini-3-flash-preview-search | Qq159741 | AI 市场分析 |
| ai_key_levels_config.json | gemini-3-flash-preview-search | Qq159741 | AI 主力位 |
| ai_overlays_config.json | gemini-3-flash-preview-search | Qq159741 | AI 画线 |

### 代码更新

1. **ai_market_summary.py**
   - 新增 `get_ai_overlays_config()` 函数
   - 新增 `_load_overlays_config()` 函数

2. **chart_pro_v10.py**
   - 导入 `get_ai_overlays_config`
   - 修改第 607 行使用独立的 overlays 配置

3. **SignalMonitorConfigSection.tsx**
   - 新增 20+ 配置字段
   - 新增 5 个配置组
   - 新增 4 个图标导入

### 前端更新

- 新增配置字段：轮询监控、信号过滤、Token 刷新器、外部 API 密钥等
- 文件大小：从 562 行增加到 877 行 (+56%)

---

## ⚠️ 注意事项

1. **备份配置**
   - 同步前建议备份 VPS 上的现有配置
   ```bash
   ssh $VPS "cd $VPS_PATH && tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz signal_monitor/*.json"
   ```

2. **服务停机时间**
   - 重启服务会导致短暂停机（约 5-10 秒）
   - 建议在低峰时段进行同步

3. **前端构建时间**
   - 前端构建可能需要 2-5 分钟
   - 构建期间 API 服务可以继续运行

4. **配置验证**
   - 同步后务必验证 AI 配置是否正确加载
   - 测试 AI 简评功能是否正常工作

---

## 🆘 故障排查

### 问题 1: SCP 连接失败

```bash
# 检查 SSH 连接
ssh -v root@your_vps_ip

# 检查端口是否正确
ssh -p 22 root@your_vps_ip
```

### 问题 2: 权限错误

```bash
# 检查文件权限
ssh $VPS "ls -la $VPS_PATH/signal_monitor/"

# 修复权限
ssh $VPS "chmod 644 $VPS_PATH/signal_monitor/*.json"
ssh $VPS "chmod 644 $VPS_PATH/signal_monitor/*.py"
```

### 问题 3: Python 模块导入错误

```bash
# 检查 Python 路径
ssh $VPS "cd $VPS_PATH/signal_monitor && python3 -c 'import sys; print(sys.path)'"

# 重新安装依赖
ssh $VPS "cd $VPS_PATH && pip3 install -r requirements.txt"
```

### 问题 4: 服务启动失败

```bash
# 查看详细错误日志
ssh $VPS "journalctl -u valuescan-signal -n 50 --no-pager"

# 手动测试启动
ssh $VPS "cd $VPS_PATH/signal_monitor && python3 start_polling.py"
```

---

## 📞 联系支持

如果遇到问题，请提供以下信息：
1. 错误日志
2. 系统环境 (OS, Python 版本)
3. 同步的文件列表
4. 执行的命令

---

**最后更新**: 2025-12-28
**版本**: v1.0

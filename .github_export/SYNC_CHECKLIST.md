# ValueScan 同步文件清单

## 需要同步的文件 (共 10 个)

### AI 配置文件 (4个) - 必须同步
- [ ] signal_monitor/ai_summary_config.json
- [ ] signal_monitor/ai_market_summary_config.json
- [ ] signal_monitor/ai_key_levels_config.json
- [ ] signal_monitor/ai_overlays_config.json

### Python 代码 (4个) - 必须同步
- [ ] signal_monitor/ai_market_summary.py
- [ ] signal_monitor/chart_pro_v10.py
- [ ] signal_monitor/ai_signal_analysis.py
- [ ] signal_monitor/ai_key_levels_config.py

### 前端文件 (2个) - 可选同步
- [ ] web/src/components/valuescan/SignalMonitorConfigSection.tsx
- [ ] web/src/types/config.ts

## 快速同步命令

### 一键同步所有文件 (Linux/Mac)

```bash
VPS="root@your_vps_ip"
VPS_PATH="/root/valuescan"

# AI 配置
scp signal_monitor/ai_*.json $VPS:$VPS_PATH/signal_monitor/

# Python 代码
scp signal_monitor/ai_market_summary.py \
    signal_monitor/chart_pro_v10.py \
    signal_monitor/ai_signal_analysis.py \
    signal_monitor/ai_key_levels_config.py \
    $VPS:$VPS_PATH/signal_monitor/

# 前端 (可选)
scp web/src/components/valuescan/SignalMonitorConfigSection.tsx \
    $VPS:$VPS_PATH/web/src/components/valuescan/
scp web/src/types/config.ts \
    $VPS:$VPS_PATH/web/src/types/
```

### 一键同步所有文件 (Windows)

```cmd
set VPS=root@your_vps_ip
set VPS_PATH=/root/valuescan

REM AI 配置
scp signal_monitor\ai_*.json %VPS%:%VPS_PATH%/signal_monitor/

REM Python 代码
scp signal_monitor\ai_market_summary.py %VPS%:%VPS_PATH%/signal_monitor/
scp signal_monitor\chart_pro_v10.py %VPS%:%VPS_PATH%/signal_monitor/
scp signal_monitor\ai_signal_analysis.py %VPS%:%VPS_PATH%/signal_monitor/
scp signal_monitor\ai_key_levels_config.py %VPS%:%VPS_PATH%/signal_monitor/

REM 前端 (可选)
scp web\src\components\valuescan\SignalMonitorConfigSection.tsx %VPS%:%VPS_PATH%/web/src/components/valuescan/
scp web\src\types\config.ts %VPS%:%VPS_PATH%/web/src/types/
```

## 同步后验证

```bash
# 验证 AI 配置
ssh $VPS "cd $VPS_PATH/signal_monitor && python3 -c '
from ai_market_summary import get_ai_summary_config, get_ai_market_config, get_ai_overlays_config
from ai_key_levels_config import get_ai_levels_config
print(\"✅ AI 简评:\", get_ai_summary_config().get(\"model\"))
print(\"✅ AI 市场:\", get_ai_market_config().get(\"model\"))
print(\"✅ AI 主力位:\", get_ai_levels_config().get(\"model\"))
print(\"✅ AI 画线:\", get_ai_overlays_config().get(\"model\"))
'"

# 重启服务
ssh $VPS "systemctl restart valuescan-signal && systemctl restart valuescan-api"
```

## 文件大小参考

```
ai_summary_config.json              192 bytes
ai_market_summary_config.json       211 bytes
ai_key_levels_config.json           158 bytes
ai_overlays_config.json             158 bytes
ai_market_summary.py                ~50 KB
chart_pro_v10.py                    ~80 KB
ai_signal_analysis.py               ~30 KB
ai_key_levels_config.py             ~5 KB
SignalMonitorConfigSection.tsx      ~35 KB
config.ts                           ~15 KB
```

总大小: ~215 KB

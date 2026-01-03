#!/usr/bin/env python3
"""添加 Chrome 启动参数"""
with open("/opt/valuescan/signal_monitor/api_monitor.py", "r") as f:
    content = f.read()

# 在 --no-sandbox 后添加 --remote-allow-origins=*
if "--remote-allow-origins" not in content:
    content = content.replace(
        "co.set_argument('--no-sandbox')",
        "co.set_argument('--no-sandbox')\n            co.set_argument('--remote-allow-origins=*')"
    )
    with open("/opt/valuescan/signal_monitor/api_monitor.py", "w") as f:
        f.write(content)
    print("Added --remote-allow-origins=* to Chrome args")
else:
    print("Already has --remote-allow-origins")

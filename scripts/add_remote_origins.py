#!/usr/bin/env python3
with open('/opt/valuescan/signal_monitor/api_monitor.py', 'r') as f:
    content = f.read()

if '--remote-allow-origins' not in content:
    content = content.replace(
        "co.set_argument('--no-sandbox')",
        "co.set_argument('--no-sandbox')\n            co.set_argument('--remote-allow-origins=*')"
    )
    with open('/opt/valuescan/signal_monitor/api_monitor.py', 'w') as f:
        f.write(content)
    print("Added --remote-allow-origins=*")
else:
    print("Already has --remote-allow-origins")

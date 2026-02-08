#!/usr/bin/env python3
import re
with open("/opt/valuescan/signal_monitor/config.py", "r") as f:
    c = f.read()
c = re.sub(r'SOCKS5_PROXY = ""', 'SOCKS5_PROXY = "socks5://127.0.0.1:1080"', c)
with open("/opt/valuescan/signal_monitor/config.py", "w") as f:
    f.write(c)
print("Signal monitor proxy configured")

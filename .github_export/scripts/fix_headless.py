#!/usr/bin/env python3
import re
with open("/opt/valuescan/signal_monitor/config.py", "r") as f:
    c = f.read()
c = re.sub(r"HEADLESS_MODE = False", "HEADLESS_MODE = True", c)
with open("/opt/valuescan/signal_monitor/config.py", "w") as f:
    f.write(c)
print("HEADLESS_MODE set to True")

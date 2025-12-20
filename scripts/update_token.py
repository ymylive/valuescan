#!/usr/bin/env python3
with open("/opt/valuescan/signal_monitor/config.py", "r") as f:
    c = f.read()
c = c.replace('TELEGRAM_BOT_TOKEN = ""', 'TELEGRAM_BOT_TOKEN = "8574875999:AAGV2QmoHXMVVnsH2MCZL03Pa2V5wpqzGEk"')
with open("/opt/valuescan/signal_monitor/config.py", "w") as f:
    f.write(c)
print("Token updated!")

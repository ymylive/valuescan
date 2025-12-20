#!/usr/bin/env python3
# Update SOCKS5 proxy config for signal_monitor
with open("/opt/valuescan/signal_monitor/config.py", "r") as f:
    c = f.read()
c = c.replace('SOCKS5_PROXY = ""', 'SOCKS5_PROXY = "socks5://127.0.0.1:1080"')
with open("/opt/valuescan/signal_monitor/config.py", "w") as f:
    f.write(c)

# Update for binance_trader
with open("/opt/valuescan/binance_trader/config.py", "r") as f:
    c = f.read()
c = c.replace('SOCKS5_PROXY = None', 'SOCKS5_PROXY = "socks5://127.0.0.1:1080"')
with open("/opt/valuescan/binance_trader/config.py", "w") as f:
    f.write(c)
print("Proxy configured!")

#!/usr/bin/env python3
import re
with open("/opt/valuescan/binance_trader/config.py", "r") as f:
    c = f.read()
c = re.sub(r'BINANCE_API_KEY = "[^"]*"', 'BINANCE_API_KEY = "xFvUoan5T1dvW2SOCgEfIoS7uFkClVrNnAmCKLbCcuffybBHRVrNF7Gv4NaEqNGd"', c)
c = re.sub(r'BINANCE_API_SECRET = "[^"]*"', 'BINANCE_API_SECRET = "llEikv30igZ8QTm8AvXgvh0858aXqG76S9BQUeg7mV5rpezI9BfjHjDxXixVzhNS"', c)
with open("/opt/valuescan/binance_trader/config.py", "w") as f:
    f.write(c)
print("New API Key configured!")

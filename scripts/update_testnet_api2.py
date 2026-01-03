#!/usr/bin/env python3
import re
with open("/opt/valuescan/binance_trader/config.py", "r") as f:
    c = f.read()
# Update API Key
c = re.sub(r'BINANCE_API_KEY = "[^"]*"', 'BINANCE_API_KEY = "PbZaRLjAtZhiUXt1VjxvAt4eP4yz8cq08yTaYv2anVjJPXB5kd4fRremBHhk1D4k"', c)
# Update API Secret
c = re.sub(r'BINANCE_API_SECRET = "[^"]*"', 'BINANCE_API_SECRET = "7mbAxjCLRit87SMfSuDVOh80B3wIU2cpoJVXgzHfT5faxmlaE3T3ADxgFXIdUIN8"', c)
with open("/opt/valuescan/binance_trader/config.py", "w") as f:
    f.write(c)
print("New Testnet API Key with Futures permission configured!")

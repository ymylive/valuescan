#!/usr/bin/env python3
import re
with open("/opt/valuescan/binance_trader/config.py", "r") as f:
    c = f.read()
# Update API Key
c = re.sub(r'BINANCE_API_KEY = "[^"]*"', 'BINANCE_API_KEY = "s7Ic7xNz5N4IpRBYAcSihYhBghy0UX0SGYPhsnEfYvTXCxGNXjZNROWcCIRY5bdc"', c)
# Update API Secret
c = re.sub(r'BINANCE_API_SECRET = "[^"]*"', 'BINANCE_API_SECRET = "q3bN4SHTZ5PWvhtHypp2FsHCMIMvDX9djhneIx5XQGXUAgmojDpRFMGS0jX4AQIR"', c)
with open("/opt/valuescan/binance_trader/config.py", "w") as f:
    f.write(c)
print("Testnet API Key configured!")

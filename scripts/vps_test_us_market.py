#!/usr/bin/env python3
"""VPS test US market signal script"""
import sys
sys.path.insert(0, '/root/valuescan/signal_monitor')
from telegram import send_message_with_async_chart

# Test US market signal
msg = "[TEST] US Market Open Signal\n"
msg += "\U0001F4CA SPY: +0.85% \U0001F4C8\n"
msg += "\U0001F4CA QQQ: +1.12% \U0001F4C8\n"
msg += "\nMarket sentiment: Bullish\n"
msg += "Crypto may follow upward"

send_message_with_async_chart(msg, 'BTC')
print('US market signal sent!')

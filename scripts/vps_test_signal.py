#!/usr/bin/env python3
"""VPS test signal script"""
import sys
sys.path.insert(0, '/root/valuescan/signal_monitor')
from telegram import send_message_with_async_chart

# Test anomaly signal
msg = "[TEST] Anomaly Signal\n"
msg += "\U0001F7E1 BTC \U0001F4C8\n"
msg += "Volume spike: 5.2x\n"
msg += "Funding rate: -0.015%\n"
msg += "Independent move confirmed"

send_message_with_async_chart(msg, 'BTC')
print('Anomaly signal sent!')

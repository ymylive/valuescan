#!/usr/bin/env python3
"""Test macro analysis function"""
import sys
import os

# Add paths
sys.path.insert(0, '/root/valuescan')
sys.path.insert(0, '/root/valuescan/signal_monitor')
os.chdir('/root/valuescan/signal_monitor')

import traceback
from ai_market_summary import generate_market_summary

try:
    result = generate_market_summary(force=True)
    print("Result:", result[:500] if result else "None")
except Exception as e:
    print("Error:", e)
    traceback.print_exc()

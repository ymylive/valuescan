#!/usr/bin/env python3
import sys
sys.path.insert(0, "/root/valuescan")
sys.path.insert(0, "/root/valuescan/signal_monitor")
import os
os.chdir("/root/valuescan/signal_monitor")

from signal_monitor.ai_signal_analysis import analyze_signal

print("Testing AI signal analysis for BTC...")
result = analyze_signal("BTC")

if result:
    print("SUCCESS!")
    print("Analysis:", result.get("analysis", "")[:200])
    print("Supports:", result.get("supports"))
    print("Resistances:", result.get("resistances"))
else:
    print("FAILED - No result returned")

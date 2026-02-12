#!/usr/bin/env python3
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "signal_monitor"))
os.chdir(BASE_DIR / "signal_monitor")

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

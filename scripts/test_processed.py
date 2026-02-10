#!/usr/bin/env python3
import sys
sys.path.insert(0, '/opt/valuescan/signal_monitor')
from database import is_message_processed
print("36307 processed:", is_message_processed("36307"))
print("36306 processed:", is_message_processed("36306"))
print("36308 processed:", is_message_processed("36308"))

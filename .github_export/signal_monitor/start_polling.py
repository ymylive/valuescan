#!/usr/bin/env python3
"""
Compatibility entrypoint for older systemd units.

Some VPS deployments use a unit that runs:
  /root/valuescan/signal_monitor/start_polling.py

The current repo uses `polling_monitor.py` as the polling-based monitor.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    # Ensure local imports work when executed via absolute path.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from polling_monitor import main as polling_main

    polling_main()


if __name__ == "__main__":
    main()


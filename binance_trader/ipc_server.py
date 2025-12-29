#!/usr/bin/env python3
"""
Compatibility entrypoint for older systemd units.

Some VPS deployments use a unit that runs:
  /root/valuescan/binance_trader/ipc_server.py

This repo now provides the IPC bridge at `scripts/valuescan_futures_bridge.py`.
By default we start the IPC bridge (so signal_monitor can forward signals).

Set `VALUESCAN_TRADER_MODE=standalone` to run the trader loop without IPC.
"""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


def _run_ipc_bridge(repo_root: Path) -> None:
    target = repo_root / "scripts" / "valuescan_futures_bridge.py"
    if not target.exists():
        raise SystemExit(f"IPC bridge not found: {target}")
    runpy.run_path(str(target), run_name="__main__")


def _run_standalone() -> None:
    from futures_main import FuturesAutoTradingSystem

    system = FuturesAutoTradingSystem()
    system.run_standalone()


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(Path(__file__).resolve().parent))

    mode = (os.getenv("VALUESCAN_TRADER_MODE") or "ipc").strip().lower()
    if mode in {"standalone", "solo", "direct"}:
        _run_standalone()
        return

    _run_ipc_bridge(repo_root)


if __name__ == "__main__":
    main()


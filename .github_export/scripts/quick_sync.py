#!/usr/bin/env python3
"""Quick sync essential files to VPS."""

import os
import sys
import paramiko

VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "")
VPS_PATH = "/root/valuescan"

# Essential files only
ESSENTIAL_FILES = [
    "signal_monitor/ai_market_summary.py",
    "signal_monitor/polling_monitor.py",
    "signal_monitor/message_handler.py",
    "api/server.py",
    "binance_trader/trading_signal_processor.py",
]

def main():
    if not VPS_PASSWORD:
        print("Error: VALUESCAN_VPS_PASSWORD not set")
        return 1

    print(f"Quick Sync to {VPS_USER}@{VPS_HOST}")
    print()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=30)
        print("[+] Connected")
    except Exception as e:
        print(f"[ERROR] {e}")
        return 1

    sftp = ssh.open_sftp()

    for file in ESSENTIAL_FILES:
        if not os.path.exists(file):
            print(f"[SKIP] {file}")
            continue

        try:
            remote_path = f"{VPS_PATH}/{file}"
            sftp.put(file, remote_path)
            print(f"[OK] {file}")
        except Exception as e:
            print(f"[FAIL] {file}: {e}")

    sftp.close()

    # Restart services
    print("\nRestarting services...")
    ssh.exec_command("systemctl restart valuescan-signal")
    ssh.exec_command("systemctl restart valuescan-api")
    print("[OK] Services restarted")

    ssh.close()
    print("\n[SUCCESS] Sync completed")
    return 0

if __name__ == "__main__":
    sys.exit(main())

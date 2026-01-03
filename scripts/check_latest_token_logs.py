#!/usr/bin/env python3
"""Check latest token refresher logs."""

import os
import sys
import paramiko

def main():
    host = os.environ.get("VALUESCAN_VPS_HOST", "82.158.88.34")
    user = os.environ.get("VALUESCAN_VPS_USER", "root")
    password = os.environ.get("VALUESCAN_VPS_PASSWORD", "")

    if not password:
        print("Error: VALUESCAN_VPS_PASSWORD not set")
        return 1

    print(f"[*] Connecting to {user}@{host}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(host, username=user, password=password, timeout=30)
        print("[+] Connected\n")
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return 1

    # Get latest logs
    print("=" * 60)
    print("[*] Latest token refresher logs (last 20 lines):")
    print("=" * 60)
    stdin, stdout, stderr = ssh.exec_command(
        "journalctl -u valuescan-token-refresher -n 20 --no-pager",
        timeout=30
    )
    print(stdout.read().decode('utf-8', errors='ignore'))

    # Check token file
    print("\n" + "=" * 60)
    print("[*] Current token file content:")
    print("=" * 60)
    stdin, stdout, stderr = ssh.exec_command(
        "cat /root/valuescan/signal_monitor/valuescan_localstorage.json",
        timeout=30
    )
    print(stdout.read().decode('utf-8', errors='ignore'))

    ssh.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())

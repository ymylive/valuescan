#!/usr/bin/env python3
"""Check signal service status on VPS."""

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

    # Check signal service status
    print("=" * 60)
    print("[*] Signal service status:")
    print("=" * 60)
    stdin, stdout, stderr = ssh.exec_command(
        "systemctl status valuescan-signal --no-pager -l | head -20",
        timeout=30
    )
    output = stdout.read().decode('utf-8', errors='replace')
    print(output)

    # Check latest logs
    print("\n" + "=" * 60)
    print("[*] Latest signal service logs (last 20 lines):")
    print("=" * 60)
    stdin, stdout, stderr = ssh.exec_command(
        "journalctl -u valuescan-signal -n 20 --no-pager",
        timeout=30
    )
    output = stdout.read().decode('utf-8', errors='replace')
    print(output)

    ssh.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())

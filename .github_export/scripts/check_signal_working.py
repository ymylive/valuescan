#!/usr/bin/env python3
"""Check if signal service is working on VPS."""

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

    # Check if service detected 4002 error
    print("=" * 60)
    print("[*] Checking for 4002 error detection:")
    print("=" * 60)
    stdin, stdout, stderr = ssh.exec_command(
        "journalctl -u valuescan-signal --since '5 minutes ago' | grep -E '4002|Token.*expired|SUCCESS' | tail -20",
        timeout=30
    )
    output = stdout.read().decode('utf-8', errors='replace')
    if output.strip():
        print(output)
    else:
        print("No 4002 errors or token refresh in last 5 minutes")

    # Check current token file
    print("\n" + "=" * 60)
    print("[*] Current token file:")
    print("=" * 60)
    stdin, stdout, stderr = ssh.exec_command(
        "cat /root/valuescan/signal_monitor/valuescan_localstorage.json | python3 -m json.tool | head -20",
        timeout=30
    )
    output = stdout.read().decode('utf-8', errors='replace')
    print(output)

    ssh.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())

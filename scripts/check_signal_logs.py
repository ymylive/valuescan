#!/usr/bin/env python3
"""Check signal service logs on VPS."""

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

    # Check latest logs
    print("=" * 60)
    print("[*] Latest signal service logs (last 30 lines):")
    print("=" * 60)
    stdin, stdout, stderr = ssh.exec_command(
        "journalctl -u valuescan-signal -n 30 --no-pager",
        timeout=30
    )

    # Read and print line by line to avoid encoding issues
    for line in stdout:
        try:
            print(line.rstrip())
        except:
            print(line.encode('utf-8', errors='replace').decode('utf-8', errors='replace').rstrip())

    ssh.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())

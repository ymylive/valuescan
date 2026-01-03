#!/usr/bin/env python3
"""Restart VPS token refresher and monitor logs."""

import os
import sys
import time
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

    # Restart service
    print("=" * 60)
    print("[*] Restarting token refresher service...")
    print("=" * 60)
    stdin, stdout, stderr = ssh.exec_command("systemctl restart valuescan-token-refresher", timeout=30)
    stdout.read()
    time.sleep(2)

    # Check status
    print("\n[*] Service status:")
    stdin, stdout, stderr = ssh.exec_command("systemctl status valuescan-token-refresher --no-pager -l | head -20", timeout=30)
    print(stdout.read().decode('utf-8', errors='ignore'))

    # Monitor logs
    print("\n" + "=" * 60)
    print("[*] Monitoring logs (last 30 lines)...")
    print("=" * 60)
    stdin, stdout, stderr = ssh.exec_command("journalctl -u valuescan-token-refresher -n 30 --no-pager", timeout=30)
    print(stdout.read().decode('utf-8', errors='ignore'))

    ssh.close()
    print("\n[+] Done! Service restarted successfully.")
    print("\nTo continue monitoring logs, run:")
    print("  ssh root@82.158.88.34 'journalctl -u valuescan-token-refresher -f'")
    return 0

if __name__ == "__main__":
    sys.exit(main())

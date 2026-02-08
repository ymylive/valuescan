#!/usr/bin/env python3
"""Check VPS token refresher service status."""

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
        print("[+] Connected successfully\n")
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return 1

    commands = [
        ("Token refresher service status", "systemctl status valuescan-token-refresher --no-pager -l | head -30"),
        ("Token refresher logs (last 50 lines)", "journalctl -u valuescan-token-refresher -n 50 --no-pager"),
        ("Check token file", "cat /root/valuescan/signal_monitor/valuescan_localstorage.json 2>&1 | head -20"),
        ("Check credentials file", "ls -la /root/valuescan/signal_monitor/valuescan_credentials.json"),
        ("Check browser process", "ps aux | grep -E 'chromium|chrome' | grep -v grep"),
        ("Check CDP port", "netstat -tlnp | grep 9222"),
    ]

    for desc, cmd in commands:
        print("=" * 60)
        print(f"[*] {desc}")
        print("=" * 60)
        print(f"$ {cmd}\n")

        try:
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')

            if output:
                print(output)
            if error:
                print(f"[ERROR] {error}")
        except Exception as e:
            print(f"[ERROR] Command failed: {e}")

        print()

    ssh.close()
    print("[+] Check completed!")
    return 0

if __name__ == "__main__":
    sys.exit(main())

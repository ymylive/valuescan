#!/usr/bin/env python3
"""Deploy signal monitor fix to VPS."""

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

    # Upload polling_monitor.py
    print("[*] Uploading polling_monitor.py...")
    sftp = ssh.open_sftp()
    try:
        sftp.put(
            "signal_monitor/polling_monitor.py",
            "/root/valuescan/signal_monitor/polling_monitor.py"
        )
        print("[+] File uploaded successfully\n")
    except Exception as e:
        print(f"[ERROR] Upload failed: {e}")
        sftp.close()
        ssh.close()
        return 1

    sftp.close()

    # Restart signal service
    print("[*] Restarting valuescan-signal service...")
    stdin, stdout, stderr = ssh.exec_command("systemctl restart valuescan-signal", timeout=30)
    stdout.channel.recv_exit_status()

    import time
    time.sleep(3)

    # Check service status
    print("\n[*] Service status:")
    stdin, stdout, stderr = ssh.exec_command(
        "systemctl status valuescan-signal --no-pager -l | head -20",
        timeout=30
    )
    output = stdout.read().decode('utf-8', errors='replace')
    print(output)

    # Check logs
    print("\n[*] Latest logs (last 15 lines):")
    stdin, stdout, stderr = ssh.exec_command(
        "journalctl -u valuescan-signal -n 15 --no-pager",
        timeout=30
    )
    output = stdout.read().decode('utf-8', errors='replace')
    print(output)

    ssh.close()
    print("\n[+] Done! Signal service restarted with fix.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check the status of the Selenium token refresher on VPS.
"""

import os
import subprocess
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


def _get_paramiko():
    try:
        import paramiko
        return paramiko
    except ImportError:
        print("Installing paramiko...")
        subprocess.run([sys.executable, "-m", "pip", "install", "paramiko"], check=True)
        import paramiko
        return paramiko


def main():
    paramiko = _get_paramiko()

    host = os.environ.get("VALUESCAN_VPS_HOST", "82.158.88.34")
    user = os.environ.get("VALUESCAN_VPS_USER", "root")
    password = os.environ.get("VALUESCAN_VPS_PASSWORD", "")

    if not password:
        print("Error: VALUESCAN_VPS_PASSWORD environment variable is required")
        return 1

    print(f"Connecting to {user}@{host} ...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(host, username=user, password=password, timeout=30)
    except Exception as e:
        print(f"Connection failed: {e}")
        return 1

    print("\n" + "="*60)
    print("Service Status")
    print("="*60)
    stdin, stdout, stderr = ssh.exec_command('systemctl status valuescan-token-refresher --no-pager -l | head -30')
    print(stdout.read().decode())

    print("\n" + "="*60)
    print("Recent Logs (last 50 lines)")
    print("="*60)
    stdin, stdout, stderr = ssh.exec_command('journalctl -u valuescan-token-refresher -n 50 --no-pager')
    print(stdout.read().decode())

    print("\n" + "="*60)
    print("Token File Status")
    print("="*60)
    stdin, stdout, stderr = ssh.exec_command('ls -lh /root/valuescan/signal_monitor/valuescan_localstorage.json && echo "" && cat /root/valuescan/signal_monitor/valuescan_localstorage.json | python3 -m json.tool | head -20')
    print(stdout.read().decode())

    ssh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

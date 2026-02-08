#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查 Telegram 服务状态
"""

import os
import subprocess
import sys
import time

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
        print("Retrying in 5 seconds...")
        time.sleep(5)
        try:
            ssh.connect(host, username=user, password=password, timeout=30)
        except Exception as e2:
            print(f"Connection failed again: {e2}")
            return 1

    print("\n" + "="*60)
    print("Signal Monitor 服务状态")
    print("="*60)
    stdin, stdout, stderr = ssh.exec_command('systemctl status valuescan-monitor --no-pager -l | head -30')
    print(stdout.read().decode())

    print("\n" + "="*60)
    print("最近的 Telegram 日志 (最后 50 行)")
    print("="*60)
    stdin, stdout, stderr = ssh.exec_command('journalctl -u valuescan-monitor -n 50 --no-pager | grep -i telegram')
    output = stdout.read().decode()
    if output.strip():
        print(output)
    else:
        print("没有找到 Telegram 相关日志")

    ssh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix VPS dependencies and configuration for chart generation
"""
import os
import sys
import getpass
import paramiko

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

DEFAULT_HOST = "82.158.88.34"
DEFAULT_USER = "root"
VALUESCAN_DIR = "/root/valuescan"

def get_password():
    password = os.environ.get("VALUESCAN_VPS_PASSWORD", "")
    if password:
        return password
    if sys.stdin.isatty():
        try:
            pw = getpass.getpass(f"Enter SSH password for {DEFAULT_USER}@{DEFAULT_HOST}: ")
            return pw.strip() or None
        except Exception:
            pass
    return None

def exec_command(ssh, cmd, description=""):
    if description:
        print(f"\n{'='*60}")
        print(f"[*] {description}")
        print(f"{'='*60}")
    print(f"$ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    exit_code = stdout.channel.recv_exit_status()
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')

    if output:
        print(output)
    if error and exit_code != 0:
        print(f"[ERROR] {error}", file=sys.stderr)

    return exit_code, output, error

def main():
    password = get_password()
    if not password:
        print("[!] No password provided")
        return 1

    print(f"[*] Connecting to {DEFAULT_USER}@{DEFAULT_HOST}...")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(
            hostname=DEFAULT_HOST,
            username=DEFAULT_USER,
            password=password,
            timeout=30,
            banner_timeout=30,
            auth_timeout=30
        )
        print("[+] Connected successfully\n")

        # 1. Install missing Python dependencies
        exec_command(ssh,
            "pip3 install matplotlib mplfinance Pillow -i https://pypi.tuna.tsinghua.edu.cn/simple",
            "1. Installing missing Python dependencies")

        # 2. Verify installation
        exec_command(ssh,
            "pip3 list | grep -E 'matplotlib|mplfinance|Pillow'",
            "2. Verifying installed dependencies")

        # 3. Check if AUTO_DELETE_CHARTS exists
        code, output, _ = exec_command(ssh,
            f"grep -c 'AUTO_DELETE_CHARTS' {VALUESCAN_DIR}/signal_monitor/config.py || echo '0'",
            "3. Checking for AUTO_DELETE_CHARTS in config")

        if output.strip() == '0':
            print("\n[*] AUTO_DELETE_CHARTS not found, adding to config...")
            exec_command(ssh, f"""
sed -i '/ENABLE_PRO_CHART = True/a\\
\\
# 自动删除生成的图表文件\\
# True: 发送后自动删除 (默认)\\
# False: 保留文件 (用于调试)\\
AUTO_DELETE_CHARTS = True' {VALUESCAN_DIR}/signal_monitor/config.py
""", "Adding AUTO_DELETE_CHARTS to config")

        # 4. Verify config changes
        exec_command(ssh,
            f"grep -A 5 'ENABLE_PRO_CHART' {VALUESCAN_DIR}/signal_monitor/config.py",
            "4. Verifying config changes")

        # 5. Restart signal monitor service
        exec_command(ssh,
            "systemctl restart valuescan-signal",
            "5. Restarting signal monitor service")

        # 6. Check service status
        exec_command(ssh,
            "systemctl status valuescan-signal --no-pager -l | head -20",
            "6. Checking service status")

        print("\n[+] VPS dependencies and config fixed successfully!")

    except Exception as e:
        print(f"[!] Error: {e}")
        return 1
    finally:
        ssh.close()

    return 0

if __name__ == "__main__":
    sys.exit(main())

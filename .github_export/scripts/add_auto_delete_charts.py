#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add AUTO_DELETE_CHARTS to VPS config
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
    print(f"$ {cmd[:100]}...")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    exit_code = stdout.channel.recv_exit_status()
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')

    if output:
        print(output[:500])
    if error and exit_code != 0:
        print(f"[ERROR] {error[:500]}", file=sys.stderr)

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

        # Add AUTO_DELETE_CHARTS using Python
        exec_command(ssh, f"""python3 << 'PYEOF'
config_file = '{VALUESCAN_DIR}/signal_monitor/config.py'
with open(config_file, 'r', encoding='utf-8') as f:
    content = f.read()

if 'AUTO_DELETE_CHARTS' not in content:
    # Find the line with ENABLE_PRO_CHART
    lines = content.split('\\n')
    new_lines = []
    for i, line in enumerate(lines):
        new_lines.append(line)
        if 'ENABLE_PRO_CHART = True' in line:
            new_lines.append('')
            new_lines.append('# 自动删除生成的图表文件')
            new_lines.append('# True: 发送后自动删除 (默认)')
            new_lines.append('# False: 保留文件 (用于调试)')
            new_lines.append('AUTO_DELETE_CHARTS = True')

    with open(config_file, 'w', encoding='utf-8') as f:
        f.write('\\n'.join(new_lines))
    print('AUTO_DELETE_CHARTS added successfully')
else:
    print('AUTO_DELETE_CHARTS already exists')
PYEOF
""", "Adding AUTO_DELETE_CHARTS to config")

        # Verify the change
        exec_command(ssh,
            f"grep -A 5 'ENABLE_PRO_CHART' {VALUESCAN_DIR}/signal_monitor/config.py",
            "Verifying config changes")

        # Restart service
        exec_command(ssh,
            "systemctl restart valuescan-signal",
            "Restarting signal monitor service")

        print("\n[+] AUTO_DELETE_CHARTS added successfully!")

    except Exception as e:
        print(f"[!] Error: {e}")
        return 1
    finally:
        ssh.close()

    return 0

if __name__ == "__main__":
    sys.exit(main())

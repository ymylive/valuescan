#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix VPS chart configuration and verify dependencies
"""
import os
import sys
import getpass
import paramiko
from pathlib import Path

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
        print(f"🔧 {description}")
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
        print("❌ No password provided")
        return 1

    print(f"🔌 Connecting to {DEFAULT_USER}@{DEFAULT_HOST}...")

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
        print("✅ Connected successfully\n")

        # 1. Check signal_monitor config.py
        exec_command(ssh,
            f"cat {VALUESCAN_DIR}/signal_monitor/config.py | grep -A 2 'ENABLE_PRO_CHART\\|AUTO_DELETE_CHARTS'",
            "1. Checking signal_monitor config.py for chart settings")

        # 2. Check if chart_pro_v10.py exists
        exec_command(ssh,
            f"ls -lh {VALUESCAN_DIR}/signal_monitor/chart_pro_v*.py",
            "2. Checking chart generator modules")

        # 3. Check Python dependencies
        exec_command(ssh,
            "pip3 list | grep -E 'matplotlib|pandas|mplfinance|numpy|Pillow'",
            "3. Checking Python dependencies for chart generation")

        # 4. Check if config has ENABLE_PRO_CHART
        code, output, _ = exec_command(ssh,
            f"grep -c 'ENABLE_PRO_CHART' {VALUESCAN_DIR}/signal_monitor/config.py || echo '0'",
            "4. Verifying ENABLE_PRO_CHART exists in config")

        if output.strip() == '0':
            print("\n⚠️  ENABLE_PRO_CHART not found in config.py")
            print("📝 Adding ENABLE_PRO_CHART and AUTO_DELETE_CHARTS to config...")

            # Add missing fields
            exec_command(ssh, f"""
cat >> {VALUESCAN_DIR}/signal_monitor/config.py << 'EOF'

# ==================== Pro 图表配置（本地生成） ====================
# 是否启用 Pro 图表（本地生成K线+热力图+资金流）
ENABLE_PRO_CHART = True

# 自动删除生成的图表文件
# True: 发送后自动删除 (默认)
# False: 保留文件 (用于调试)
AUTO_DELETE_CHARTS = True
EOF
""", "Adding chart configuration to config.py")

        # 5. Check API server config reading
        exec_command(ssh,
            f"grep -A 5 'def get_config' {VALUESCAN_DIR}/api/server.py | head -20",
            "5. Checking API server config reading logic")

        # 6. Restart signal monitor service
        print("\n" + "="*60)
        response = input("🔄 Do you want to restart signal monitor service? (y/N): ")
        if response.lower() == 'y':
            exec_command(ssh,
                "systemctl restart valuescan-signal",
                "Restarting signal monitor service")
            exec_command(ssh,
                "systemctl status valuescan-signal --no-pager -l",
                "Checking service status")

        print("\n✅ VPS check and fix completed!")

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    finally:
        ssh.close()

    return 0

if __name__ == "__main__":
    sys.exit(main())

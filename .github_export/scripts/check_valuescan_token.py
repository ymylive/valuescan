#!/usr/bin/env python3
"""
检查 ValueScan token 状态
"""
import os
import sys
import json

try:
    import paramiko
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "paramiko"], check=True)
    import paramiko

VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "")

if not VPS_PASSWORD:
    print("Error: VALUESCAN_VPS_PASSWORD environment variable not set")
    exit(1)

print(f"Connecting to {VPS_HOST}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD)

# 检查 token 文件
print("\n" + "="*60)
print("检查 ValueScan Token 文件")
print("="*60)

token_files = [
    "/root/valuescan/signal_monitor/valuescan_localstorage.json",
    "/root/valuescan/signal_monitor/valuescan_cookies.json",
    "/root/valuescan/signal_monitor/valuescan_sessionstorage.json"
]

for f in token_files:
    stdin, stdout, stderr = ssh.exec_command(f"ls -la {f} 2>/dev/null && cat {f} | head -c 500")
    output = stdout.read().decode()
    if output:
        print(f"\n{f}:")
        print(output)
    else:
        print(f"\n{f}: 文件不存在")

# 检查 config.py 中的 VALUESCAN_TOKEN
print("\n" + "="*60)
print("检查 config.py 中的 VALUESCAN_TOKEN")
print("="*60)
stdin, stdout, stderr = ssh.exec_command("grep -E 'VALUESCAN_TOKEN|account_token' /root/valuescan/signal_monitor/config.py | head -5")
print(stdout.read().decode())

# 检查 start_polling.py 如何读取 token
print("\n" + "="*60)
print("检查 start_polling.py 如何读取 token")
print("="*60)
stdin, stdout, stderr = ssh.exec_command("grep -A5 'account_token' /root/valuescan/signal_monitor/start_polling.py | head -20")
print(stdout.read().decode())

ssh.close()
print("\nDone!")

#!/usr/bin/env python3
"""
上传 ValueScan token 到 VPS
"""
import os
import sys

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

sftp = ssh.open_sftp()

# 上传文件
local_file = "signal_monitor/valuescan_localstorage.json"
remote_file = "/root/valuescan/signal_monitor/valuescan_localstorage.json"

if os.path.exists(local_file):
    print(f"Uploading {local_file} -> {remote_file}")
    sftp.put(local_file, remote_file)
    print("[+] Token file uploaded successfully")
else:
    print(f"[ERROR] File not found: {local_file}")
    sftp.close()
    ssh.close()
    exit(1)

sftp.close()

# 重启token刷新服务
print("\n[*] Restarting valuescan-token-refresher service...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart valuescan-token-refresher")
stdout.channel.recv_exit_status()

import time
time.sleep(3)

# 检查服务状态
print("\n[*] Checking token refresher service status...")
stdin, stdout, stderr = ssh.exec_command("systemctl status valuescan-token-refresher --no-pager -l | head -20")
print(stdout.read().decode())

# 等待几秒看日志
time.sleep(5)
print("\n[*] Latest logs...")
stdin, stdout, stderr = ssh.exec_command("journalctl -u valuescan-token-refresher --no-pager -n 10")
print(stdout.read().decode())

ssh.close()
print("\nDone!")

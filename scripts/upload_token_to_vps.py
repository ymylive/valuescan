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
files_to_upload = [
    ("valuescan_localstorage.json", "/root/valuescan/signal_monitor/valuescan_localstorage.json"),
    ("valuescan_sessionstorage.json", "/root/valuescan/signal_monitor/valuescan_sessionstorage.json"),
    ("valuescan_cookies.json", "/root/valuescan/signal_monitor/valuescan_cookies.json"),
]

for local_file, remote_file in files_to_upload:
    if os.path.exists(local_file):
        print(f"上传 {local_file} -> {remote_file}")
        sftp.put(local_file, remote_file)
    else:
        print(f"文件不存在: {local_file}")

sftp.close()

# 重启信号监测服务
print("\n重启 valuescan-signal 服务...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart valuescan-signal")
stdout.channel.recv_exit_status()

import time
time.sleep(3)

# 检查服务状态
print("\n检查服务状态...")
stdin, stdout, stderr = ssh.exec_command("systemctl status valuescan-signal --no-pager -l | head -20")
print(stdout.read().decode())

# 等待几秒看日志
time.sleep(5)
print("\n最新日志...")
stdin, stdout, stderr = ssh.exec_command("journalctl -u valuescan-signal --no-pager -n 10")
print(stdout.read().decode())

ssh.close()
print("\nDone!")

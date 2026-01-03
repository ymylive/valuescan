#!/usr/bin/env python3
"""上传文件并重启服务"""
import paramiko
import time
import os
from pathlib import Path

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
host = os.environ.get("VALUESCAN_VPS_HOST", "")
user = os.environ.get("VALUESCAN_VPS_USER", "root")
password = os.environ.get("VALUESCAN_VPS_PASSWORD", "")
key_file = (os.environ.get("VALUESCAN_VPS_KEY_FILE") or "").strip()
if not key_file:
    default_key = Path.home() / ".ssh" / "valuescan_vps"
    if default_key.exists():
        key_file = str(default_key)

if not host:
    raise SystemExit("Missing VALUESCAN_VPS_HOST")
if not password and not key_file:
    raise SystemExit("Missing VALUESCAN_VPS_PASSWORD / VALUESCAN_VPS_KEY_FILE")

connect_kwargs = {"hostname": host, "username": user, "timeout": 30}
if password:
    connect_kwargs["password"] = password
else:
    connect_kwargs["key_filename"] = key_file
ssh.connect(**connect_kwargs)

sftp = ssh.open_sftp()

# 上传文件
files = [
    ("e:/project/valuescan/polling_monitor_v2.py", "/opt/valuescan/polling_monitor_v2.py"),
    ("e:/project/valuescan/token_refresher.py", "/opt/valuescan/token_refresher.py"),
    ("e:/project/valuescan/signal_monitor/telegram.py", "/opt/valuescan/signal_monitor/telegram.py"),
    ("e:/project/valuescan/valuescan_watchdog.py", "/opt/valuescan/valuescan_watchdog.py"),
    ("e:/project/valuescan/telegram_copytrade/copytrade_main.py", "/opt/valuescan/telegram_copytrade/copytrade_main.py"),
]

print("📤 上传文件...")
for local, remote in files:
    if os.path.exists(local):
        sftp.put(local, remote)
        print(f"   ✅ {os.path.basename(local)}")
    else:
        print(f"   ❌ 文件不存在: {local}")

sftp.close()

print("\n🔄 重启服务...")
ssh.exec_command("systemctl daemon-reload")
time.sleep(1)
ssh.exec_command("systemctl restart valuescan-signal valuescan-trader valuescan-watchdog valuescan-token-refresher")
time.sleep(5)

print("\n📊 服务状态:")
print("="*80)
stdin, stdout, stderr = ssh.exec_command("systemctl status valuescan-signal valuescan-trader valuescan-watchdog --no-pager -l")
print(stdout.read().decode())

print("\n📋 valuescan-trader 日志 (最近200行):")
print("="*80)
stdin, stdout, stderr = ssh.exec_command("journalctl -u valuescan-trader -n 200 --no-pager")
print(stdout.read().decode())

print("\n📋 valuescan-watchdog 日志 (最近200行):")
print("="*80)
stdin, stdout, stderr = ssh.exec_command("journalctl -u valuescan-watchdog -n 200 --no-pager")
print(stdout.read().decode())

ssh.close()
print("\n✅ 完成!")

#!/usr/bin/env python3
"""
检查信号监测服务状态和日志
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

# 1. 检查服务状态
print("\n" + "="*60)
print("1. 服务状态")
print("="*60)
stdin, stdout, stderr = ssh.exec_command("systemctl status valuescan-signal --no-pager -l | head -20")
print(stdout.read().decode())

# 2. 检查最近的日志
print("\n" + "="*60)
print("2. 最近50行日志")
print("="*60)
stdin, stdout, stderr = ssh.exec_command("journalctl -u valuescan-signal --no-pager -n 50")
print(stdout.read().decode())

# 3. 检查 Telegram 配置
print("\n" + "="*60)
print("3. Telegram 配置")
print("="*60)
stdin, stdout, stderr = ssh.exec_command("grep -E 'TELEGRAM|ENABLE_TELEGRAM' /root/valuescan/signal_monitor/config.py")
print(stdout.read().decode())

# 4. 检查 API 返回的消息数量
print("\n" + "="*60)
print("4. 检查 API 是否有新消息")
print("="*60)
stdin, stdout, stderr = ssh.exec_command("""
cd /root/valuescan/signal_monitor && python3 << 'EOF'
import json
try:
    from config import VALUESCAN_TOKEN
    print(f"Token configured: {'Yes' if VALUESCAN_TOKEN else 'No'}")
    print(f"Token length: {len(VALUESCAN_TOKEN) if VALUESCAN_TOKEN else 0}")
except Exception as e:
    print(f"Error loading config: {e}")
EOF
""")
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err)

# 5. 测试 Telegram 发送
print("\n" + "="*60)
print("5. 测试 Telegram 发送")
print("="*60)
stdin, stdout, stderr = ssh.exec_command("""
cd /root/valuescan/signal_monitor && python3 << 'EOF'
import requests
try:
    from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ENABLE_TELEGRAM
    print(f"ENABLE_TELEGRAM: {ENABLE_TELEGRAM}")
    print(f"BOT_TOKEN configured: {'Yes' if TELEGRAM_BOT_TOKEN else 'No'}")
    print(f"CHAT_ID: {TELEGRAM_CHAT_ID}")
    
    if ENABLE_TELEGRAM and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        # 发送测试消息
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": "🔔 测试消息 - 信号监测服务正常运行",
            "parse_mode": "HTML"
        }
        resp = requests.post(url, json=data, timeout=10)
        print(f"Telegram API response: {resp.status_code}")
        print(resp.json())
    else:
        print("Telegram not enabled or not configured")
except Exception as e:
    print(f"Error: {e}")
EOF
""")
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err)

ssh.close()
print("\nDone!")

#!/usr/bin/env python3
"""清理并重启 Telegram Bot - 确保只有一个实例"""

import paramiko
import time

VPS_HOST = "43.133.12.98"
VPS_USER = "root"
VPS_PASS = "Qq159741"

def main():
    print("Connecting to VPS...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS, timeout=30)

    # 1. 强制杀掉所有 Python 进程中包含 trader/telegram 的
    print("\n[1] Force killing all related processes...")
    stdin, stdout, stderr = client.exec_command(
        "ps aux | grep -E 'telegram_bot|start_trader_bot' | grep -v grep | awk '{print $2}' | xargs -r kill -9 2>/dev/null; sleep 2; echo 'Done'"
    )
    print(f"    {stdout.read().decode().strip()}")

    # 2. 再次确认
    print("[2] Verifying no processes remain...")
    stdin, stdout, stderr = client.exec_command(
        "ps aux | grep -E 'telegram_bot|start_trader_bot' | grep -v grep | wc -l"
    )
    count = stdout.read().decode().strip()
    print(f"    Remaining processes: {count}")

    # 3. 启动单个实例
    print("\n[3] Starting single bot instance...")
    start_cmd = "cd /root/valuescan && nohup python3 start_trader_bot.py > /tmp/trader_bot.log 2>&1 &"
    client.exec_command(start_cmd)
    time.sleep(4)

    # 4. 验证
    print("[4] Verifying...")
    stdin, stdout, stderr = client.exec_command(
        "ps aux | grep -E 'telegram_bot|start_trader_bot' | grep -v grep"
    )
    result = stdout.read().decode().strip()
    lines = [l for l in result.split('\n') if l.strip()]
    print(f"    Process count: {len(lines)}")
    for line in lines[:3]:
        print(f"    {line[:80]}")

    # 5. 显示日志
    print("\n[5] Recent logs:")
    stdin, stdout, stderr = client.exec_command("sleep 2; tail -10 /tmp/trader_bot.log 2>&1")
    print(stdout.read().decode())

    client.close()
    print("\nDone! Test the bot by sending a message.")

if __name__ == "__main__":
    main()

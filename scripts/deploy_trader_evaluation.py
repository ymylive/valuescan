#!/usr/bin/env python3
"""
部署交易员评测功能到 VPS
"""

import os
import sys
import paramiko
import time

VPS_HOST = "43.133.12.98"
VPS_USER = "root"
VPS_PASS = "Qq159741"

LOCAL_PROJECT = r"E:\project\valuescan"
REMOTE_PROJECT = "/root/valuescan"

def main():
    print("=" * 50)
    print("Deploying Trader Evaluation Feature to VPS")
    print("=" * 50)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS, timeout=15)
    sftp = client.open_sftp()

    # 需要上传的文件
    files = [
        "signal_monitor/binance_copytrade_api.py",
        "signal_monitor/trader_analyzer.py",
        "signal_monitor/trader_evaluation_prompt.py",
        "signal_monitor/trader_chart_generator.py",
        "signal_monitor/telegram_bot.py",
        "signal_monitor/config.py",
    ]

    print("\n[1/4] Uploading files...")
    for rel_path in files:
        local_path = os.path.join(LOCAL_PROJECT, rel_path)
        remote_path = f"{REMOTE_PROJECT}/{rel_path}"

        if os.path.exists(local_path):
            print(f"  Uploading: {rel_path}")
            sftp.put(local_path, remote_path)
        else:
            print(f"  [SKIP] {rel_path} not found")

    sftp.close()

    print("\n[2/4] Installing dependencies...")
    stdin, stdout, stderr = client.exec_command(
        "cd /root/valuescan && pip3 install python-telegram-bot --quiet 2>&1 | tail -3"
    )
    print(stdout.read().decode())

    print("\n[3/4] Testing import...")
    test_cmd = """cd /root/valuescan && python3 -c "
from signal_monitor.binance_copytrade_api import BinanceCopyTradeAPI
from signal_monitor.trader_analyzer import TraderAnalyzer
from signal_monitor.telegram_bot import TelegramBotHandler
print('All imports successful!')
" 2>&1"""
    stdin, stdout, stderr = client.exec_command(test_cmd)
    result = stdout.read().decode()
    print(result)

    if "Error" in result or "error" in result.lower():
        print("\n[ERROR] Import test failed!")
        client.close()
        return

    print("\n[4/4] Starting bot in background...")
    # 创建启动脚本
    start_script = '''#!/usr/bin/env python3
import sys
sys.path.insert(0, "/root/valuescan")
from signal_monitor.telegram_bot import start_bot_polling
start_bot_polling()
'''

    stdin, stdout, stderr = client.exec_command(
        f'echo \'{start_script}\' > /root/valuescan/start_trader_bot.py && chmod +x /root/valuescan/start_trader_bot.py'
    )
    stdout.read()

    # 检查是否已有运行的 bot
    stdin, stdout, stderr = client.exec_command("pgrep -f 'start_trader_bot.py' 2>&1")
    existing_pid = stdout.read().decode().strip()

    if existing_pid:
        print(f"  Killing existing bot (PID: {existing_pid})...")
        client.exec_command(f"kill {existing_pid}")
        time.sleep(2)

    # 启动新的 bot
    stdin, stdout, stderr = client.exec_command(
        "cd /root/valuescan && nohup python3 start_trader_bot.py > /tmp/trader_bot.log 2>&1 &"
    )
    time.sleep(3)

    # 检查是否启动成功
    stdin, stdout, stderr = client.exec_command("pgrep -f 'start_trader_bot.py' 2>&1")
    new_pid = stdout.read().decode().strip()

    if new_pid:
        print(f"  Bot started successfully! PID: {new_pid}")
    else:
        print("  [WARNING] Bot may not have started. Check logs.")

    # 显示日志
    print("\n=== Bot Logs ===")
    stdin, stdout, stderr = client.exec_command("tail -10 /tmp/trader_bot.log 2>&1")
    print(stdout.read().decode())

    client.close()

    print("\n" + "=" * 50)
    print("Deployment complete!")
    print("=" * 50)
    print("\nUsage:")
    print("  - Send trader ID directly to the bot")
    print("  - Or use command: /trader <ID>")
    print("\nLogs: /tmp/trader_bot.log")


if __name__ == "__main__":
    main()

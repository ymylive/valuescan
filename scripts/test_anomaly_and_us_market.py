#!/usr/bin/env python3
"""测试异动信号和美股开盘信号"""

import paramiko
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

VPS_HOST = '43.133.12.98'
VPS_USER = 'root'
VPS_PASS = 'Qq159741'

def connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS, timeout=15)
    return client

def test_anomaly_signal(client):
    """测试异动信号"""
    print("\n=== 测试异动信号 ===")

    test_code = '''
import sys
sys.path.insert(0, '/root/valuescan/signal_monitor')
from telegram import send_message_with_async_chart

# 发送测试异动信号
msg = """🟡 BTC 📈 [测试信号]
异动检测系统测试
• 成交量突增 5.2x
• 资金费率: -0.015%
• 独立行情确认"""

send_message_with_async_chart(msg, "BTC")
print("Anomaly signal sent!")
'''

    stdin, stdout, stderr = client.exec_command(f'cd /root/valuescan/signal_monitor && python3 -c "{test_code}"', timeout=60)
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print(f"Errors: {err}")

def test_us_market_signal(client):
    """测试美股开盘信号"""
    print("\n=== 测试美股开盘信号 ===")

    test_code = '''
import sys
sys.path.insert(0, '/root/valuescan/signal_monitor')
from telegram import send_message_with_async_chart

# 发送测试美股开盘信号
msg = """📊 美股开盘5分钟信号 [测试]

SPY: +0.85% 📈
QQQ: +1.12% 📈

市场情绪: 偏多
建议关注: 加密市场可能跟随上涨"""

send_message_with_async_chart(msg, "BTC")
print("US market signal sent!")
'''

    stdin, stdout, stderr = client.exec_command(f'cd /root/valuescan/signal_monitor && python3 -c "{test_code}"', timeout=60)
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print(f"Errors: {err}")

def main():
    print("连接 VPS...")
    client = connect()

    try:
        test_anomaly_signal(client)
        time.sleep(3)
        test_us_market_signal(client)

        print("\n=== 检查最新日志 ===")
        stdin, stdout, stderr = client.exec_command('journalctl -u valuescan-monitor -n 15 --no-pager 2>&1')
        logs = stdout.read().decode()
        for line in logs.split('\n'):
            if 'Telegram' in line or 'chart' in line or 'INFO' in line:
                print(line[-120:])

    finally:
        client.close()

    print("\n✅ 测试完成！请检查 Telegram 是否收到消息。")

if __name__ == '__main__':
    main()

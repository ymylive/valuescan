#!/usr/bin/env python3
"""测试 IPC 信号发送"""
import os
import paramiko
import json
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD'))

# 发送测试信号到 IPC
# 使用真实的币种符号（测试网支持的）
test_signal = {
    'message_type': 110,  # Alpha 信号
    'message_id': f'test_{int(time.time())}',
    'symbol_hint': 'BTC',  # 使用 BTC 作为测试
    'data': {'content': {'symbol': 'BTC'}}
}

print('发送测试 Alpha 信号到 IPC...')
print(f'信号: {test_signal}')

# 通过 Python 发送信号
signal_json = json.dumps(test_signal).replace('"', '\\"')
cmd = f'python3 -c "import socket; s=socket.socket(); s.connect((\'127.0.0.1\', 8765)); s.send(b\'{signal_json}\\n\'); s.close()"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print(f'发送结果: {stdout.read().decode()}')
print(f'错误: {stderr.read().decode()}')

time.sleep(3)

# 检查 trader 日志
print('\n=== Trader 最新日志 ===')
stdin, stdout, stderr = ssh.exec_command('journalctl -u valuescan-trader --no-pager -n 25')
print(stdout.read().decode())

ssh.close()

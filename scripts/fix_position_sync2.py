#!/usr/bin/env python3
"""修复 position_sync.go 中的 NewFuturesTrader 调用"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print("修复 position_sync.go...")

# 查看第 495 行附近的代码
print("\n查看第 495 行附近的代码:")
stdin, stdout, stderr = ssh.exec_command('sed -n "490,500p" /opt/nofx/trader/position_sync.go')
print(stdout.read().decode())

# 使用 Python 修复
modify_script = '''
with open('/opt/nofx/trader/position_sync.go', 'r') as f:
    content = f.read()

# 修复 NewFuturesTrader 调用
old_call = 'return NewFuturesTrader(exchange.APIKey, exchange.SecretKey, config.Trader.UserID), nil'
new_call = 'return NewFuturesTrader(exchange.APIKey, exchange.SecretKey, config.Trader.UserID, exchange.Testnet), nil'

if old_call in content:
    content = content.replace(old_call, new_call)
    with open('/opt/nofx/trader/position_sync.go', 'w') as f:
        f.write(content)
    print("已修复 NewFuturesTrader 调用")
else:
    print("未找到需要修复的代码，可能已经修复")
'''

stdin, stdout, stderr = ssh.exec_command(f"python3 << 'PYEOF'\n{modify_script}\nPYEOF")
print(stdout.read().decode())
print(stderr.read().decode())

# 验证修复
print("\n验证修复:")
stdin, stdout, stderr = ssh.exec_command('grep -n "NewFuturesTrader" /opt/nofx/trader/position_sync.go')
print(stdout.read().decode())

ssh.close()

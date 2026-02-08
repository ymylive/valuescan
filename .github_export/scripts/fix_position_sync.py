#!/usr/bin/env python3
"""修复 position_sync.go 中的 NewFuturesTrader 调用"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print("修复 position_sync.go...")

# 查看当前调用
print("\n当前 NewFuturesTrader 调用:")
stdin, stdout, stderr = ssh.exec_command('grep -n "NewFuturesTrader" /opt/nofx/trader/position_sync.go')
print(stdout.read().decode())

# 修复调用
print("\n修复调用...")
stdin, stdout, stderr = ssh.exec_command('''
sed -i 's/NewFuturesTrader(exchange.APIKey, exchange.SecretKey, exchange.UserID)/NewFuturesTrader(exchange.APIKey, exchange.SecretKey, exchange.UserID, exchange.Testnet)/g' /opt/nofx/trader/position_sync.go
''')
print(stdout.read().decode())
print(stderr.read().decode())

# 验证修复
print("\n验证修复:")
stdin, stdout, stderr = ssh.exec_command('grep -n "NewFuturesTrader" /opt/nofx/trader/position_sync.go')
print(stdout.read().decode())

ssh.close()

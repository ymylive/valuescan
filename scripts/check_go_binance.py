#!/usr/bin/env python3
"""检查 go-binance 库"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

# 查看 go.mod 中的 binance 库
print('go.mod 中的 binance 库:')
stdin, stdout, stderr = ssh.exec_command('grep "binance" /opt/nofx/go.mod')
print(stdout.read().decode())

# 查看 go-binance 库的 futures 包
print('\n查看 go-binance futures 包:')
stdin, stdout, stderr = ssh.exec_command('find /opt/nofx -path "*/go-binance*" -name "*.go" | head -10')
print(stdout.read().decode())

# 查看 auto_trader.go 中的 BinanceTestnet 配置
print('\n查看 auto_trader.go 中的配置结构:')
stdin, stdout, stderr = ssh.exec_command('grep -n -A5 "type AutoTraderConfig" /opt/nofx/trader/auto_trader.go | head -80')
print(stdout.read().decode())

# 查看 auto_trader.go 中如何创建 binance trader
print('\n查看 auto_trader.go 中如何创建 binance trader:')
stdin, stdout, stderr = ssh.exec_command('grep -n -B5 -A20 "case.*binance" /opt/nofx/trader/auto_trader.go | head -60')
print(stdout.read().decode())

ssh.close()

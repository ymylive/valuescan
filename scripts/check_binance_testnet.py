#!/usr/bin/env python3
"""检查 go-binance 库的 testnet 支持"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

# 查看 go-binance 库的 testnet 支持
print('查看 go-binance 库的 testnet 支持:')
stdin, stdout, stderr = ssh.exec_command('grep -rn "testnet\\|Testnet\\|UseTestnet\\|BaseURL" /opt/nofx/go.mod | head -20')
print(stdout.read().decode())

# 查看 binance_futures.go 完整的 NewFuturesTrader 函数
print('\n查看 NewFuturesTrader 函数:')
stdin, stdout, stderr = ssh.exec_command('sed -n "64,100p" /opt/nofx/trader/binance_futures.go')
print(stdout.read().decode())

# 查看 manager 中如何创建 binance trader
print('\n查看 manager 中如何创建 binance trader:')
stdin, stdout, stderr = ssh.exec_command('grep -n -B5 -A15 "binance\\|Binance" /opt/nofx/manager/trader_manager.go | head -80')
print(stdout.read().decode())

ssh.close()

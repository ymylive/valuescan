#!/usr/bin/env python3
"""检查 NOFX 后端 testnet 支持"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

# 查看 trader 目录下的所有 go 文件
print('trader 目录下的 go 文件:')
stdin, stdout, stderr = ssh.exec_command('ls -la /opt/nofx/trader/*.go')
print(stdout.read().decode())

# 搜索 testnet 相关代码
print('\n搜索 testnet 相关代码:')
stdin, stdout, stderr = ssh.exec_command('grep -rn "testnet\\|Testnet\\|UseTestnet" /opt/nofx/trader/')
print(stdout.read().decode() or '(未找到)')

# 查看 go-binance 库的 testnet 支持
print('\n查看 binance_futures.go 中的客户端创建:')
stdin, stdout, stderr = ssh.exec_command('grep -n -A10 "NewFuturesTrader\\|NewClient" /opt/nofx/trader/binance_futures.go | head -30')
print(stdout.read().decode())

# 查看 manager 中的交易所创建
print('\n查看 manager 中的交易所创建:')
stdin, stdout, stderr = ssh.exec_command('grep -rn "testnet\\|Testnet" /opt/nofx/manager/')
print(stdout.read().decode() or '(未找到)')

# 查看 api 中的交易所配置
print('\n查看 api 中的交易所配置:')
stdin, stdout, stderr = ssh.exec_command('grep -rn "testnet\\|Testnet" /opt/nofx/api/')
print(stdout.read().decode() or '(未找到)')

ssh.close()

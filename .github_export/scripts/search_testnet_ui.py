#!/usr/bin/env python3
"""搜索 NOFX testnet UI 相关代码"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

# 搜索 testnet 相关的 UI 代码
print('搜索 testnet 相关的 UI 代码:')
stdin, stdout, stderr = ssh.exec_command('grep -n -B2 -A5 "testnet" /opt/nofx/web/src/components/traders/ExchangeConfigModal.tsx | head -100')
print(stdout.read().decode())

# 查看 i18n 翻译中是否有 testnet
print('\n\n搜索 i18n 中的 testnet:')
stdin, stdout, stderr = ssh.exec_command('grep -n "testnet" /opt/nofx/web/src/i18n/translations.ts')
print(stdout.read().decode() or '(未找到)')

# 查看后端 binance_futures.go 中的 testnet 支持
print('\n\n搜索后端 testnet 支持:')
stdin, stdout, stderr = ssh.exec_command('grep -n -B2 -A5 "testnet\\|Testnet\\|TESTNET" /opt/nofx/trader/binance_futures.go | head -50')
print(stdout.read().decode() or '(未找到)')

ssh.close()

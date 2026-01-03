#!/usr/bin/env python3
"""读取 NOFX 交易所配置模态框开头"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

# 读取交易所配置模态框开头
print('ExchangeConfigModal.tsx (前300行):')
stdin, stdout, stderr = ssh.exec_command('head -300 /opt/nofx/web/src/components/traders/ExchangeConfigModal.tsx')
print(stdout.read().decode())

# 搜索 testnet 相关代码
print('\n\n搜索 testnet 相关代码:')
stdin, stdout, stderr = ssh.exec_command('grep -n "testnet" /opt/nofx/web/src/components/traders/ExchangeConfigModal.tsx')
print(stdout.read().decode() or '(未找到 testnet)')

ssh.close()

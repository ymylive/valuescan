#!/usr/bin/env python3
"""读取 NOFX 交易所配置模态框"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

# 读取交易所配置模态框
print('ExchangeConfigModal.tsx:')
stdin, stdout, stderr = ssh.exec_command('cat /opt/nofx/web/src/components/traders/ExchangeConfigModal.tsx')
print(stdout.read().decode())

ssh.close()

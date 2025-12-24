#!/usr/bin/env python3
"""读取 NOFX 关键文件"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

files_to_read = [
    '/opt/nofx/web/src/lib/config.ts',
    '/opt/nofx/web/src/types.ts',
    '/opt/nofx/trader/binance_futures.go',
    '/opt/nofx/store/exchange.go',
]

for f in files_to_read:
    print(f'\n{"="*60}')
    print(f'文件: {f}')
    print('='*60)
    stdin, stdout, stderr = ssh.exec_command(f'head -100 {f}')
    print(stdout.read().decode())

ssh.close()

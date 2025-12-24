#!/usr/bin/env python3
"""读取 NOFX 前端交易所配置相关文件"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

# 查找交易所配置相关组件
print('查找交易所配置相关组件:')
stdin, stdout, stderr = ssh.exec_command('find /opt/nofx/web/src -name "*.tsx" | xargs grep -l -i "exchange\\|binance\\|testnet" 2>/dev/null | head -20')
print(stdout.read().decode())

# 查看 App.tsx 中的交易所相关部分
print('\n查看 App.tsx 中的交易所配置:')
stdin, stdout, stderr = ssh.exec_command('grep -n -A5 -B5 "exchange\\|testnet" /opt/nofx/web/src/App.tsx | head -100')
print(stdout.read().decode())

# 查看 types.ts 中的交易所类型
print('\n查看 types.ts 中的交易所类型:')
stdin, stdout, stderr = ssh.exec_command('grep -n -A10 "Exchange" /opt/nofx/web/src/types.ts | head -50')
print(stdout.read().decode())

ssh.close()

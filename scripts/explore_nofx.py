#!/usr/bin/env python3
"""探索 NOFX 项目结构"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

# 查看 NOFX 项目结构
print('NOFX 项目结构:')
stdin, stdout, stderr = ssh.exec_command('ls -la /opt/nofx/')
print(stdout.read().decode())

print('\nNOFX web 源码结构:')
stdin, stdout, stderr = ssh.exec_command('ls -la /opt/nofx/web/src/')
print(stdout.read().decode())

print('\nNOFX 配置相关文件:')
stdin, stdout, stderr = ssh.exec_command('find /opt/nofx -name "*.ts" -path "*/config*" -o -name "*config*.ts" | head -20')
print(stdout.read().decode())

print('\nNOFX 交易所相关文件:')
stdin, stdout, stderr = ssh.exec_command('find /opt/nofx -name "*exchange*" -o -name "*binance*" | head -20')
print(stdout.read().decode())

print('\nNOFX constants 目录:')
stdin, stdout, stderr = ssh.exec_command('ls -la /opt/nofx/web/src/constants/ 2>/dev/null || echo "目录不存在"')
print(stdout.read().decode())

print('\nNOFX services 目录:')
stdin, stdout, stderr = ssh.exec_command('ls -la /opt/nofx/web/src/services/ 2>/dev/null || echo "目录不存在"')
print(stdout.read().decode())

ssh.close()

#!/usr/bin/env python3
"""检查 token_refresher 服务配置"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print('=' * 60)
print('检查 token_refresher 服务配置')
print('=' * 60)

# 1. 检查服务文件
print('\n1. 检查服务文件:')
stdin, stdout, stderr = ssh.exec_command('cat /etc/systemd/system/valuescan-token-refresher.service')
print(stdout.read().decode())

# 2. 检查 token_refresher.py 位置
print('\n2. 检查 token_refresher.py 位置:')
stdin, stdout, stderr = ssh.exec_command('ls -la /opt/valuescan/token_refresher.py /root/valuescan/signal_monitor/token_refresher.py 2>&1')
print(stdout.read().decode())

# 3. 检查 /root/valuescan 和 /opt/valuescan 的关系
print('\n3. 检查目录结构:')
stdin, stdout, stderr = ssh.exec_command('ls -la /opt/valuescan 2>&1 | head -5; echo "---"; ls -la /root/valuescan 2>&1 | head -5')
print(stdout.read().decode())

# 4. 手动运行 token_refresher.py 测试
print('\n4. 手动测试 token_refresher.py (使用 --once):')
stdin, stdout, stderr = ssh.exec_command('''
cd /root/valuescan/signal_monitor
VALUESCAN_EMAIL=ymy_live@outlook.com VALUESCAN_PASSWORD=Qq159741. python3.9 token_refresher.py --once 2>&1 | head -50
''', timeout=120)
print(stdout.read().decode())
print(stderr.read().decode())

ssh.close()

#!/usr/bin/env python3
"""检查 ValueScan 登录错误"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print('=' * 60)
print('检查 ValueScan API 服务状态和日志')
print('=' * 60)

# 1. 检查 API 服务状态
print('\n1. valuescan-api 服务状态:')
stdin, stdout, stderr = ssh.exec_command('systemctl status valuescan-api --no-pager | head -20')
print(stdout.read().decode())

# 2. 检查最近的 API 日志
print('\n2. 最近的 API 日志:')
stdin, stdout, stderr = ssh.exec_command('journalctl -u valuescan-api -n 50 --no-pager')
print(stdout.read().decode())

# 3. 检查登录脚本
print('\n3. 检查登录脚本:')
stdin, stdout, stderr = ssh.exec_command('ls -la /root/valuescan/signal_monitor/http_api_login.py /root/valuescan/signal_monitor/token_refresher.py 2>&1')
print(stdout.read().decode())

# 4. 检查 Python 版本
print('\n4. Python 版本:')
stdin, stdout, stderr = ssh.exec_command('which python3.9 python3; python3 --version')
print(stdout.read().decode())

# 5. 测试登录端点
print('\n5. 测试登录端点 (使用测试账号):')
stdin, stdout, stderr = ssh.exec_command('curl -s -X POST http://127.0.0.1:5000/api/valuescan/login -H "Content-Type: application/json" -d \'{"email":"test@test.com","password":"test"}\' 2>&1')
print(stdout.read().decode())

# 6. 检查 http_api_login.py 内容
print('\n6. 检查 http_api_login.py 是否可执行:')
stdin, stdout, stderr = ssh.exec_command('head -20 /root/valuescan/signal_monitor/http_api_login.py 2>&1')
print(stdout.read().decode())

# 7. 手动测试 http_api_login.py
print('\n7. 手动测试 http_api_login.py:')
stdin, stdout, stderr = ssh.exec_command('cd /root/valuescan/signal_monitor && python3 http_api_login.py test@test.com testpass 2>&1 | head -30')
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err:
    print("STDERR:", err)

ssh.close()

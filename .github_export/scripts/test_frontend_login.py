#!/usr/bin/env python3
"""测试前端登录端点"""

import paramiko
import os
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print('=' * 60)
print('测试前端登录端点')
print('=' * 60)

# 1. 测试 /api/valuescan/login 端点
print('\n1. 测试 /api/valuescan/login 端点 (这是前端调用的):')
print('   (这可能需要 2-3 分钟，因为会尝试浏览器登录)')

start_time = time.time()
stdin, stdout, stderr = ssh.exec_command('''
curl -s -X POST http://127.0.0.1:5000/api/valuescan/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ymy_live@outlook.com","password":"Qq159741."}' \
  --max-time 200 \
  2>&1
''', timeout=210)
result = stdout.read().decode()
elapsed = time.time() - start_time
print(f'   耗时: {elapsed:.1f}秒')
print(f'   结果: {result[:500]}')

# 2. 检查当前 token 状态
print('\n2. 检查当前 token 状态:')
stdin, stdout, stderr = ssh.exec_command('curl -s http://127.0.0.1:5000/api/valuescan/token/status')
print(stdout.read().decode())

# 3. 检查 API 日志
print('\n3. 检查最近的 API 日志:')
stdin, stdout, stderr = ssh.exec_command('journalctl -u valuescan-api -n 20 --no-pager')
print(stdout.read().decode())

ssh.close()

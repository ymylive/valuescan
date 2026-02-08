#!/usr/bin/env python3
"""验证 token 状态"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print('=' * 60)
print('验证 ValueScan Token 状态')
print('=' * 60)

# 1. 检查 token 文件
print('\n1. 检查 token 文件:')
stdin, stdout, stderr = ssh.exec_command('cat /root/valuescan/signal_monitor/valuescan_localstorage.json 2>/dev/null')
print(stdout.read().decode() or '(文件不存在)')

# 2. 检查浏览器 profile 中的 token
print('\n2. 检查浏览器 profile 中的 localStorage:')
stdin, stdout, stderr = ssh.exec_command('''
# 查找 localStorage 文件
find /root/valuescan/signal_monitor/chrome-debug-profile -name "*.localstorage*" -o -name "Local Storage" 2>/dev/null | head -5
''')
print(stdout.read().decode() or '(未找到)')

# 3. 检查 API token 状态
print('\n3. 检查 API token 状态:')
stdin, stdout, stderr = ssh.exec_command('curl -s http://127.0.0.1:5000/api/valuescan/token/status')
print(stdout.read().decode())

# 4. 检查 artifacts
print('\n4. 检查 artifacts:')
stdin, stdout, stderr = ssh.exec_command('curl -s http://127.0.0.1:5000/api/valuescan/artifacts | python3 -m json.tool 2>/dev/null | head -30')
print(stdout.read().decode())

# 5. 尝试使用 token 调用 API
print('\n5. 尝试使用 token 调用 ValueScan API:')
stdin, stdout, stderr = ssh.exec_command('''
TOKEN=$(cat /root/valuescan/signal_monitor/valuescan_localstorage.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('account_token',''))" 2>/dev/null)
if [ -n "$TOKEN" ]; then
    echo "Token found: ${TOKEN:0:20}..."
    curl -s "https://api.valuescan.io/api/account/message/getWarnMessage" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        2>&1 | head -c 300
else
    echo "No token found"
fi
''')
print(stdout.read().decode())

# 6. 检查 signal_monitor 服务状态
print('\n\n6. 检查 signal_monitor 服务状态:')
stdin, stdout, stderr = ssh.exec_command('systemctl status valuescan-signal --no-pager | head -15')
print(stdout.read().decode())

ssh.close()

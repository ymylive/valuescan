#!/usr/bin/env python3
"""调试 ValueScan 登录问题"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print('=' * 60)
print('调试 ValueScan 登录问题')
print('=' * 60)

# 1. 检查当前的 token 状态
print('\n1. 检查当前 token 状态:')
stdin, stdout, stderr = ssh.exec_command('curl -s http://127.0.0.1:5000/api/valuescan/token/status')
print(stdout.read().decode())

# 2. 检查 valuescan_localstorage.json 内容
print('\n2. 检查 valuescan_localstorage.json:')
stdin, stdout, stderr = ssh.exec_command('cat /root/valuescan/signal_monitor/valuescan_localstorage.json 2>/dev/null | head -20')
print(stdout.read().decode() or '(文件不存在或为空)')

# 3. 检查 valuescan_cookies.json 内容
print('\n3. 检查 valuescan_cookies.json:')
stdin, stdout, stderr = ssh.exec_command('cat /root/valuescan/signal_monitor/valuescan_cookies.json 2>/dev/null | head -20')
print(stdout.read().decode() or '(文件不存在或为空)')

# 4. 检查环境变量配置
print('\n4. 检查 valuescan.env 配置:')
stdin, stdout, stderr = ssh.exec_command('cat /root/valuescan/config/valuescan.env 2>/dev/null')
print(stdout.read().decode() or '(文件不存在)')

# 5. 测试 API 直接登录
print('\n5. 测试 ValueScan API 直接登录:')
stdin, stdout, stderr = ssh.exec_command('''
curl -s -X POST "https://api.valuescan.io/api/account/login" \
  -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  -H "Origin: https://www.valuescan.io" \
  -H "Referer: https://www.valuescan.io/login" \
  -d '{"account":"ymy_live@outlook.com","password":"Qq159741.","language":"en-US"}' \
  2>&1 | head -c 500
''')
print(stdout.read().decode())

# 6. 检查 DrissionPage 是否正常工作
print('\n6. 检查 DrissionPage 安装:')
stdin, stdout, stderr = ssh.exec_command('python3.9 -c "from DrissionPage import ChromiumPage; print(\'DrissionPage OK\')" 2>&1')
print(stdout.read().decode())

# 7. 检查 Chromium 浏览器
print('\n7. 检查 Chromium 浏览器:')
stdin, stdout, stderr = ssh.exec_command('which chromium-browser; chromium-browser --version 2>&1')
print(stdout.read().decode())

# 8. 检查是否有正在运行的 Chromium 进程
print('\n8. 检查 Chromium 进程:')
stdin, stdout, stderr = ssh.exec_command('ps aux | grep -i chromium | grep -v grep')
print(stdout.read().decode() or '(无 Chromium 进程)')

# 9. 尝试清理并重新登录
print('\n9. 清理旧的登录锁文件:')
stdin, stdout, stderr = ssh.exec_command('rm -f /tmp/valuescan_login_refresh.lock; echo "已清理"')
print(stdout.read().decode())

ssh.close()
print('\n' + '=' * 60)
print('诊断完成')
print('=' * 60)

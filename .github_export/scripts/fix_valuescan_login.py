#!/usr/bin/env python3
"""修复 ValueScan 登录问题"""

import paramiko
import os
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print('=' * 60)
print('修复 ValueScan 登录问题')
print('=' * 60)

# 1. 杀掉所有卡住的 Chromium 进程
print('\n1. 清理卡住的 Chromium 进程...')
stdin, stdout, stderr = ssh.exec_command('pkill -9 -f chromium; sleep 2; echo "已清理"')
print(stdout.read().decode())

# 2. 清理锁文件
print('\n2. 清理锁文件...')
stdin, stdout, stderr = ssh.exec_command('rm -f /tmp/valuescan_login*.lock; echo "已清理"')
print(stdout.read().decode())

# 3. 测试不同的 API 端点
print('\n3. 测试不同的 ValueScan API 端点...')

endpoints = [
    # 新的可能端点
    "https://api.valuescan.io/api/v1/account/login",
    "https://api.valuescan.io/api/v1/login",
    "https://api.valuescan.io/api/v1/auth/login",
    "https://api.valuescan.io/api/v2/account/login",
    "https://api.valuescan.io/v1/account/login",
    "https://api.valuescan.io/v1/login",
    "https://api.valuescan.io/login",
    "https://www.valuescan.io/api/v1/login",
    "https://www.valuescan.io/api/v1/account/login",
]

for endpoint in endpoints:
    cmd = f'''curl -s -X POST "{endpoint}" \
      -H "Content-Type: application/json" \
      -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
      -H "Origin: https://www.valuescan.io" \
      -H "Referer: https://www.valuescan.io/login" \
      -d '{{"account":"test@test.com","password":"test","language":"en-US"}}' \
      -w "\\nHTTP_CODE:%{{http_code}}" \
      2>&1 | tail -c 300'''
    stdin, stdout, stderr = ssh.exec_command(cmd)
    result = stdout.read().decode().strip()
    print(f"\n{endpoint}:")
    print(f"  {result}")

# 4. 检查 valuescan.io 网站的实际 API 调用
print('\n\n4. 检查 valuescan.io 首页获取的信息...')
stdin, stdout, stderr = ssh.exec_command('''
curl -s "https://www.valuescan.io/" -H "User-Agent: Mozilla/5.0" 2>&1 | grep -oE 'api[^"]*login[^"]*' | head -5
''')
print(stdout.read().decode() or '(未找到 API 端点)')

# 5. 尝试使用浏览器登录（清理后重试）
print('\n5. 尝试使用浏览器登录...')
print('   (这可能需要 2-3 分钟)')

# 先创建 valuescan.env 文件
stdin, stdout, stderr = ssh.exec_command('''
mkdir -p /root/valuescan/config
cat > /root/valuescan/config/valuescan.env << 'EOF'
VALUESCAN_EMAIL=ymy_live@outlook.com
VALUESCAN_PASSWORD=Qq159741.
VALUESCAN_LOGIN_METHOD=browser
VALUESCAN_AUTO_RELOGIN=1
EOF
echo "已创建 valuescan.env"
''')
print(stdout.read().decode())

# 重启 token-refresher 服务
print('\n6. 重启 token-refresher 服务...')
stdin, stdout, stderr = ssh.exec_command('systemctl restart valuescan-token-refresher; sleep 3; systemctl status valuescan-token-refresher --no-pager | head -15')
print(stdout.read().decode())

# 等待一会儿让登录完成
print('\n7. 等待登录完成 (30秒)...')
time.sleep(30)

# 检查登录状态
print('\n8. 检查登录状态:')
stdin, stdout, stderr = ssh.exec_command('curl -s http://127.0.0.1:5000/api/valuescan/token/status')
print(stdout.read().decode())

# 检查 token 文件
print('\n9. 检查 token 文件:')
stdin, stdout, stderr = ssh.exec_command('cat /root/valuescan/signal_monitor/valuescan_localstorage.json 2>/dev/null | head -10')
print(stdout.read().decode() or '(文件不存在)')

# 检查 token-refresher 日志
print('\n10. 检查 token-refresher 日志:')
stdin, stdout, stderr = ssh.exec_command('journalctl -u valuescan-token-refresher -n 30 --no-pager')
print(stdout.read().decode())

ssh.close()
print('\n' + '=' * 60)
print('修复完成')
print('=' * 60)

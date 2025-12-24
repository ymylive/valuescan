#!/usr/bin/env python3
"""设置 ValueScan 凭据并配置自动登录"""

import paramiko
import os
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print('=' * 60)
print('设置 ValueScan 凭据并配置自动登录')
print('=' * 60)

# 1. 创建 valuescan.env 文件
print('\n1. 创建 valuescan.env 文件...')
stdin, stdout, stderr = ssh.exec_command('''
mkdir -p /root/valuescan/config
cat > /root/valuescan/config/valuescan.env << 'EOF'
# ValueScan 登录凭据
VALUESCAN_EMAIL=ymy_live@outlook.com
VALUESCAN_PASSWORD=Qq159741.

# 登录方式: auto (先尝试 HTTP，失败后用浏览器), browser (只用浏览器), http (只用 HTTP)
VALUESCAN_LOGIN_METHOD=browser

# 自动重新登录
VALUESCAN_AUTO_RELOGIN=1
VALUESCAN_AUTO_RELOGIN_USE_BROWSER=1
VALUESCAN_AUTO_RELOGIN_COOLDOWN=300
EOF
echo "已创建 valuescan.env"
cat /root/valuescan/config/valuescan.env
''')
print(stdout.read().decode())

# 2. 更新 token-refresher 服务配置
print('\n2. 更新 token-refresher 服务配置...')
stdin, stdout, stderr = ssh.exec_command('''
cat > /etc/systemd/system/valuescan-token-refresher.service << 'EOF'
[Unit]
Description=ValueScan Token Auto Refresher
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/valuescan/signal_monitor
EnvironmentFile=/root/valuescan/config/valuescan.env
ExecStart=/usr/bin/python3.9 /root/valuescan/signal_monitor/token_refresher.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
echo "已更新服务配置"
''')
print(stdout.read().decode())

# 3. 更新 signal 服务配置
print('\n3. 更新 signal 服务配置...')
stdin, stdout, stderr = ssh.exec_command('''
cat > /etc/systemd/system/valuescan-signal.service << 'EOF'
[Unit]
Description=ValueScan Signal Polling Monitor
After=network.target
Documentation=https://github.com/ymylive/valuescan

[Service]
Type=simple
User=root
WorkingDirectory=/root/valuescan/signal_monitor
EnvironmentFile=/root/valuescan/config/valuescan.env
ExecStart=/usr/bin/python3.9 /root/valuescan/signal_monitor/start_polling.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
echo "已更新服务配置"
''')
print(stdout.read().decode())

# 4. 更新 API 服务配置
print('\n4. 更新 API 服务配置...')
stdin, stdout, stderr = ssh.exec_command('''
cat > /etc/systemd/system/valuescan-api.service << 'EOF'
[Unit]
Description=ValueScan API Server
After=network.target
Documentation=https://github.com/ymylive/valuescan

[Service]
Type=simple
User=root
WorkingDirectory=/root/valuescan/api
EnvironmentFile=/root/valuescan/config/valuescan.env
ExecStart=/usr/bin/python3.9 -m gunicorn -w 2 -b 127.0.0.1:5000 --timeout 600 server:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
echo "已更新服务配置"
''')
print(stdout.read().decode())

# 5. 杀掉所有卡住的 Chromium 进程
print('\n5. 清理卡住的 Chromium 进程...')
stdin, stdout, stderr = ssh.exec_command('pkill -9 -f chromium; sleep 2; echo "已清理"')
print(stdout.read().decode())

# 6. 重启所有服务
print('\n6. 重启所有服务...')
stdin, stdout, stderr = ssh.exec_command('''
systemctl restart valuescan-api valuescan-signal valuescan-token-refresher
sleep 5
systemctl status valuescan-api valuescan-signal valuescan-token-refresher --no-pager | grep -E "(●|Active:)"
''')
print(stdout.read().decode())

# 7. 等待 token-refresher 完成登录
print('\n7. 等待 token-refresher 完成登录 (最多 60 秒)...')
for i in range(12):
    time.sleep(5)
    stdin, stdout, stderr = ssh.exec_command('curl -s http://127.0.0.1:5000/api/valuescan/token/status')
    result = stdout.read().decode()
    print(f'   [{(i+1)*5}秒] {result}')
    if '"token_valid":true' in result:
        print('\n   ✓ Token 已有效!')
        break

# 8. 最终状态检查
print('\n8. 最终状态检查:')
stdin, stdout, stderr = ssh.exec_command('curl -s http://127.0.0.1:5000/api/valuescan/token/status')
print(stdout.read().decode())

ssh.close()
print('\n' + '=' * 60)
print('配置完成!')
print('=' * 60)
print('''
说明:
1. 账号密码已保存到 /root/valuescan/config/valuescan.env
2. token-refresher 服务会自动使用浏览器登录并刷新 token
3. 你不需要在前端点击"登录"按钮
4. 只需要在前端的"服务器环境变量"区域保存账号密码即可

如果 token 仍然无效，请等待几分钟让 token-refresher 完成登录。
''')

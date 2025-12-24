#!/usr/bin/env python3
"""构建 NOFX 前端"""

import paramiko
import os
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print("构建 NOFX 前端...")

# 等待 Go 编译完成
print("\n等待 Go 编译完成...")
for i in range(30):
    stdin, stdout, stderr = ssh.exec_command('ps aux | grep "go build" | grep -v grep | wc -l')
    count = stdout.read().decode().strip()
    if count == '0':
        print("Go 编译已完成")
        break
    print(f"Go 编译进行中... ({i+1}/30)")
    time.sleep(10)

# 检查 Go 编译结果
print("\n检查 Go 编译结果:")
stdin, stdout, stderr = ssh.exec_command('ls -la /opt/nofx/nofx 2>/dev/null || echo "编译文件不存在"')
print(stdout.read().decode())

# 构建前端
print("\n构建 NOFX 前端...")
stdin, stdout, stderr = ssh.exec_command('cd /opt/nofx/web && NODE_OPTIONS="--max-old-space-size=2048" npx vite build --base /nofx/', timeout=900)
print(stdout.read().decode())
print(stderr.read().decode())

# 验证前端构建
print("\n验证前端构建:")
stdin, stdout, stderr = ssh.exec_command('ls -la /opt/nofx/web/dist/ | head -10')
print(stdout.read().decode())

ssh.close()

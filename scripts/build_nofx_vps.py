#!/usr/bin/env python3
"""在 VPS 上构建 NOFX 前端"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

cmd = 'cd /opt/nofx/web && NODE_OPTIONS="--max-old-space-size=2048" npx vite build --base /nofx/'
print(f"执行: {cmd}")

stdin, stdout, stderr = ssh.exec_command(cmd, timeout=900)
print(stdout.read().decode())
print(stderr.read().decode())

# 验证构建结果
stdin, stdout, stderr = ssh.exec_command('ls -la /opt/nofx/web/dist/ 2>/dev/null | head -15')
print("\n构建结果:")
print(stdout.read().decode())

ssh.close()

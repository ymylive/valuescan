#!/usr/bin/env python3
"""使用 systemd 重启 NOFX 服务"""

import paramiko
import os
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print("使用 systemd 重启 NOFX 服务...")

# 停止现有进程
print("\n1. 停止现有进程...")
stdin, stdout, stderr = ssh.exec_command('pkill -f "/opt/nofx/nofx" 2>/dev/null || true')
stdout.read()
time.sleep(2)

# 启动 systemd 服务
print("\n2. 启动 systemd 服务...")
stdin, stdout, stderr = ssh.exec_command('systemctl start nofx')
print(stdout.read().decode())
print(stderr.read().decode())
time.sleep(3)

# 检查状态
print("\n3. 检查服务状态:")
stdin, stdout, stderr = ssh.exec_command('systemctl status nofx --no-pager')
print(stdout.read().decode())

# 检查日志
print("\n4. 检查日志:")
stdin, stdout, stderr = ssh.exec_command('journalctl -u nofx -n 30 --no-pager')
print(stdout.read().decode())

# 测试 API
print("\n5. 测试 API:")
stdin, stdout, stderr = ssh.exec_command('curl -s --max-time 5 http://127.0.0.1:8080/api/config')
result = stdout.read().decode()
print(result if result else "(无响应)")

# 如果 API 无响应，检查端口
if not result:
    print("\n6. 检查端口:")
    stdin, stdout, stderr = ssh.exec_command('ss -tlnp | grep 8080')
    print(stdout.read().decode() or "(端口未监听)")

ssh.close()

#!/usr/bin/env python3
"""调试 NOFX 启动问题"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print("调试 NOFX 启动问题...")

# 直接运行看错误
print("\n1. 直接运行 NOFX 看错误:")
stdin, stdout, stderr = ssh.exec_command('cd /opt/nofx && ./nofx 2>&1 &', timeout=10)
import time
time.sleep(5)

# 检查日志
print("\n2. 检查最新日志:")
stdin, stdout, stderr = ssh.exec_command('tail -50 /var/log/nofx.log')
print(stdout.read().decode())

# 检查 .env 是否被正确加载
print("\n3. 检查环境变量:")
stdin, stdout, stderr = ssh.exec_command('cd /opt/nofx && source .env 2>/dev/null; echo "RSA_PRIVATE_KEY 长度: ${#RSA_PRIVATE_KEY}"')
print(stdout.read().decode())

# 尝试用 env 文件启动
print("\n4. 使用 env 文件启动:")
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/nofx
pkill -f "/opt/nofx/nofx" 2>/dev/null || true
sleep 1

# 导出环境变量
export $(grep -v '^#' .env | xargs)

# 启动
./nofx 2>&1 | head -30 &
sleep 5
''', timeout=15)
print(stdout.read().decode())
print(stderr.read().decode())

# 检查进程
print("\n5. 检查进程:")
stdin, stdout, stderr = ssh.exec_command('ps aux | grep nofx | grep -v grep')
print(stdout.read().decode() or "(无进程)")

# 检查端口
print("\n6. 检查端口:")
stdin, stdout, stderr = ssh.exec_command('netstat -tlnp | grep 8080 || ss -tlnp | grep 8080 || echo "端口未监听"')
print(stdout.read().decode())

ssh.close()

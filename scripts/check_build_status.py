#!/usr/bin/env python3
"""检查编译状态"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print("检查编译状态...")

# 检查是否有 go 进程在运行
print("\n检查 go 进程:")
stdin, stdout, stderr = ssh.exec_command('ps aux | grep -E "go build|go mod" | grep -v grep')
print(stdout.read().decode() or "(无 go 进程)")

# 检查编译结果
print("\n检查编译结果:")
stdin, stdout, stderr = ssh.exec_command('ls -la /opt/nofx/nofx 2>/dev/null || echo "编译文件不存在"')
print(stdout.read().decode())

# 检查 go mod 状态
print("\n检查 go.mod:")
stdin, stdout, stderr = ssh.exec_command('head -10 /opt/nofx/go.mod')
print(stdout.read().decode())

ssh.close()

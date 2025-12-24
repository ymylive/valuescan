#!/usr/bin/env python3
"""编译 NOFX Go 后端"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print("编译 NOFX Go 后端...")

# 查找 go 命令
print("\n查找 go 命令:")
stdin, stdout, stderr = ssh.exec_command('which go || find /usr -name "go" -type f 2>/dev/null | head -5')
print(stdout.read().decode() or "(未找到)")

# 检查是否安装了 go
print("\n检查 go 版本:")
stdin, stdout, stderr = ssh.exec_command('/usr/local/go/bin/go version 2>/dev/null || /root/go/bin/go version 2>/dev/null || echo "Go 未安装"')
print(stdout.read().decode())

# 尝试编译
print("\n尝试编译:")
stdin, stdout, stderr = ssh.exec_command('''
export PATH=$PATH:/usr/local/go/bin:/root/go/bin
cd /opt/nofx
go build -o /tmp/nofx_test . 2>&1
''', timeout=300)
result = stdout.read().decode()
err = stderr.read().decode()
print(result if result else "编译成功!")
if err:
    print("错误:", err)

ssh.close()

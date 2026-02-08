#!/usr/bin/env python3
"""使用 curl 安装 Go 并编译 NOFX"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print("使用 curl 安装 Go 并编译 NOFX...")

# 安装 Go
print("\n1. 安装 Go...")
stdin, stdout, stderr = ssh.exec_command('''
# 检查是否已安装
if [ -f /usr/local/go/bin/go ]; then
    echo "Go 已安装"
    /usr/local/go/bin/go version
    exit 0
fi

# 下载并安装 Go 1.21
cd /tmp
curl -sLO https://go.dev/dl/go1.21.5.linux-amd64.tar.gz
rm -rf /usr/local/go
tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz
rm go1.21.5.linux-amd64.tar.gz

# 验证安装
/usr/local/go/bin/go version
''', timeout=300)
print(stdout.read().decode())
print(stderr.read().decode())

# 编译 NOFX
print("\n2. 编译 NOFX...")
stdin, stdout, stderr = ssh.exec_command('''
export PATH=$PATH:/usr/local/go/bin
export GOPATH=/root/go
cd /opt/nofx
go build -o nofx . 2>&1
''', timeout=600)
result = stdout.read().decode()
err = stderr.read().decode()
if result:
    print(result)
if err:
    print("错误:", err)

# 验证编译结果
print("\n3. 验证编译结果:")
stdin, stdout, stderr = ssh.exec_command('ls -la /opt/nofx/nofx 2>/dev/null || echo "编译文件不存在"')
print(stdout.read().decode())

ssh.close()

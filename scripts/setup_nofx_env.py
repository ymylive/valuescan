#!/usr/bin/env python3
"""配置 NOFX 环境变量"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print("配置 NOFX 环境变量...")

# 检查现有 .env 文件
print("\n1. 检查现有 .env 文件:")
stdin, stdout, stderr = ssh.exec_command('cat /opt/nofx/.env 2>/dev/null || echo "文件不存在"')
print(stdout.read().decode())

# 检查 .env.example
print("\n2. 检查 .env.example:")
stdin, stdout, stderr = ssh.exec_command('cat /opt/nofx/.env.example 2>/dev/null | head -50')
print(stdout.read().decode())

# 生成 RSA 密钥对并配置
print("\n3. 生成 RSA 密钥对...")
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/nofx

# 检查是否已有 .env
if [ ! -f .env ]; then
    cp .env.example .env 2>/dev/null || touch .env
fi

# 检查是否已有 RSA 密钥
if ! grep -q "RSA_PRIVATE_KEY" .env 2>/dev/null; then
    # 生成 RSA 密钥对
    openssl genrsa -out /tmp/nofx_private.pem 2048 2>/dev/null
    openssl rsa -in /tmp/nofx_private.pem -pubout -out /tmp/nofx_public.pem 2>/dev/null
    
    # 将私钥转换为单行格式
    PRIVATE_KEY=$(cat /tmp/nofx_private.pem | tr '\\n' '|' | sed 's/|$//')
    PUBLIC_KEY=$(cat /tmp/nofx_public.pem | tr '\\n' '|' | sed 's/|$//')
    
    # 添加到 .env
    echo "" >> .env
    echo "# RSA Keys for encryption" >> .env
    echo "RSA_PRIVATE_KEY=$PRIVATE_KEY" >> .env
    echo "RSA_PUBLIC_KEY=$PUBLIC_KEY" >> .env
    
    # 清理临时文件
    rm -f /tmp/nofx_private.pem /tmp/nofx_public.pem
    
    echo "RSA 密钥已生成并添加到 .env"
else
    echo "RSA 密钥已存在"
fi
''')
print(stdout.read().decode())
print(stderr.read().decode())

# 重新启动 NOFX
print("\n4. 重新启动 NOFX...")
stdin, stdout, stderr = ssh.exec_command('''
pkill -f "/opt/nofx/nofx" 2>/dev/null || true
sleep 1
cd /opt/nofx
nohup ./nofx > /var/log/nofx.log 2>&1 &
sleep 3
ps aux | grep nofx | grep -v grep
''')
print(stdout.read().decode())

# 检查日志
print("\n5. 检查启动日志:")
stdin, stdout, stderr = ssh.exec_command('tail -30 /var/log/nofx.log')
print(stdout.read().decode())

# 测试 API
print("\n6. 测试 API:")
stdin, stdout, stderr = ssh.exec_command('curl -s --max-time 5 http://127.0.0.1:8080/api/config | head -c 300')
print(stdout.read().decode() or "(无响应)")

ssh.close()

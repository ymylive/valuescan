#!/usr/bin/env python3
"""修复 RSA 密钥格式"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print("修复 RSA 密钥格式...")

# 重新生成 RSA 密钥并正确格式化
print("\n1. 重新生成 RSA 密钥...")
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/nofx

# 生成 RSA 密钥
openssl genrsa -out /tmp/nofx_rsa.pem 2048 2>/dev/null

# 读取私钥内容
PRIVATE_KEY_CONTENT=$(cat /tmp/nofx_rsa.pem)

# 生成 JWT secret
JWT_SECRET=$(openssl rand -base64 32)

# 生成 AES key
AES_KEY=$(openssl rand -base64 32)

# 创建 .env 文件 - 使用 heredoc 保持多行格式
cat > /opt/nofx/.env << 'ENVEOF'
# NOFX Configuration
NOFX_BACKEND_PORT=8080
NOFX_FRONTEND_PORT=3000
NOFX_TIMEZONE=Asia/Shanghai

# JWT Secret
JWT_SECRET=PLACEHOLDER_JWT

# Data Encryption Key
DATA_ENCRYPTION_KEY=PLACEHOLDER_AES

# Transport Encryption (set to false for HTTP)
TRANSPORT_ENCRYPTION=false

# RSA Private Key (multi-line PEM format)
ENVEOF

# 追加 RSA 密钥
echo "RSA_PRIVATE_KEY='$PRIVATE_KEY_CONTENT'" >> /opt/nofx/.env

# 替换占位符
sed -i "s|PLACEHOLDER_JWT|$JWT_SECRET|g" /opt/nofx/.env
sed -i "s|PLACEHOLDER_AES|$AES_KEY|g" /opt/nofx/.env

# 清理
rm -f /tmp/nofx_rsa.pem

echo "完成"
''')
print(stdout.read().decode())
print(stderr.read().decode())

# 验证 .env
print("\n2. 验证 .env:")
stdin, stdout, stderr = ssh.exec_command('cat /opt/nofx/.env')
print(stdout.read().decode())

# 重启服务
print("\n3. 重启服务...")
stdin, stdout, stderr = ssh.exec_command('systemctl restart nofx')
print(stdout.read().decode())
print(stderr.read().decode())

import time
time.sleep(3)

# 检查状态
print("\n4. 检查状态:")
stdin, stdout, stderr = ssh.exec_command('systemctl status nofx --no-pager | head -15')
print(stdout.read().decode())

# 检查日志
print("\n5. 检查日志:")
stdin, stdout, stderr = ssh.exec_command('journalctl -u nofx -n 20 --no-pager')
print(stdout.read().decode())

ssh.close()

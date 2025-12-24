#!/usr/bin/env python3
"""修复 NOFX .env 配置"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print("修复 NOFX .env 配置...")

# 查看当前 .env
print("\n1. 当前 .env 内容:")
stdin, stdout, stderr = ssh.exec_command('cat /opt/nofx/.env')
print(stdout.read().decode())

# 重新生成正确格式的 .env
print("\n2. 重新生成 .env...")
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/nofx

# 生成 RSA 密钥
openssl genrsa -out /tmp/nofx_rsa.pem 2048 2>/dev/null

# 读取私钥并转换为单行（用 \\n 替换换行）
PRIVATE_KEY=$(cat /tmp/nofx_rsa.pem | sed ':a;N;$!ba;s/\\n/\\\\n/g')

# 生成 JWT secret
JWT_SECRET=$(openssl rand -base64 32)

# 生成 AES key
AES_KEY=$(openssl rand -base64 32)

# 创建 .env 文件
cat > /opt/nofx/.env << EOF
# NOFX Configuration
NOFX_BACKEND_PORT=8080
NOFX_FRONTEND_PORT=3000
NOFX_TIMEZONE=Asia/Shanghai

# JWT Secret
JWT_SECRET=$JWT_SECRET

# Data Encryption Key
DATA_ENCRYPTION_KEY=$AES_KEY

# RSA Private Key
RSA_PRIVATE_KEY=$PRIVATE_KEY

# Transport Encryption (set to false for HTTP)
TRANSPORT_ENCRYPTION=false
EOF

# 清理
rm -f /tmp/nofx_rsa.pem

echo ".env 已重新生成"
''')
print(stdout.read().decode())
print(stderr.read().decode())

# 验证 .env
print("\n3. 验证 .env (前20行):")
stdin, stdout, stderr = ssh.exec_command('head -20 /opt/nofx/.env')
print(stdout.read().decode())

# 重启 NOFX
print("\n4. 重启 NOFX...")
stdin, stdout, stderr = ssh.exec_command('''
pkill -f "/opt/nofx/nofx" 2>/dev/null || true
sleep 1
cd /opt/nofx
nohup ./nofx > /var/log/nofx.log 2>&1 &
sleep 3
''')
stdout.read()

# 检查进程
print("检查进程:")
stdin, stdout, stderr = ssh.exec_command('ps aux | grep nofx | grep -v grep')
print(stdout.read().decode() or "(无进程)")

# 检查日志
print("\n5. 检查日志:")
stdin, stdout, stderr = ssh.exec_command('tail -30 /var/log/nofx.log')
print(stdout.read().decode())

# 测试 API
print("\n6. 测试 API:")
stdin, stdout, stderr = ssh.exec_command('curl -s --max-time 5 http://127.0.0.1:8080/api/config')
print(stdout.read().decode() or "(无响应)")

ssh.close()

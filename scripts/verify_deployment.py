#!/usr/bin/env python3
"""验证 VPS 部署状态"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print("=" * 60)
print("验证 VPS 部署状态")
print("=" * 60)

# 1. 检查 NOFX 目录
print("\n1. NOFX 目录结构:")
stdin, stdout, stderr = ssh.exec_command('ls -la /opt/nofx/web/dist/')
print(stdout.read().decode())

# 2. 检查 Nginx 配置
print("\n2. Nginx NOFX 配置:")
stdin, stdout, stderr = ssh.exec_command('grep -A5 "location.*nofx" /etc/nginx/conf.d/*.conf')
print(stdout.read().decode())

# 3. 测试 Nginx
print("\n3. Nginx 配置测试:")
stdin, stdout, stderr = ssh.exec_command('nginx -t')
print(stdout.read().decode())
print(stderr.read().decode())

# 4. 检查服务状态
print("\n4. ValueScan 服务状态:")
stdin, stdout, stderr = ssh.exec_command('systemctl status valuescan-api valuescan-monitor valuescan-signal --no-pager | grep -E "(●|Active:)"')
print(stdout.read().decode())

# 5. 测试 API
print("\n5. API 测试:")
stdin, stdout, stderr = ssh.exec_command('curl -s --max-time 5 http://127.0.0.1:5000/api/valuescan/token/status | head -c 300')
print(stdout.read().decode() or "(无响应)")

# 6. 测试 NOFX 页面
print("\n6. NOFX 页面测试:")
stdin, stdout, stderr = ssh.exec_command('curl -s --max-time 5 -I http://127.0.0.1/nofx/ | head -5')
print(stdout.read().decode())

# 7. 检查 valuescan.env
print("\n7. 环境变量文件:")
stdin, stdout, stderr = ssh.exec_command('cat /root/valuescan/config/valuescan.env 2>/dev/null || echo "(文件不存在)"')
print(stdout.read().decode())

print("\n" + "=" * 60)
print("验证完成")
print("=" * 60)

ssh.close()

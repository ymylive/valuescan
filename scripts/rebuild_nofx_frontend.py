#!/usr/bin/env python3
"""重新构建 NOFX 前端并重启服务"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print("=" * 60)
print("重新构建 NOFX 前端并重启服务")
print("=" * 60)

# 1. 构建前端
print("\n1. 构建 NOFX 前端...")
stdin, stdout, stderr = ssh.exec_command('cd /opt/nofx/web && NODE_OPTIONS="--max-old-space-size=2048" npx vite build --base /nofx/', timeout=300)
print(stdout.read().decode())
print(stderr.read().decode())

# 2. 验证前端构建
print("\n2. 验证前端构建:")
stdin, stdout, stderr = ssh.exec_command('ls -la /opt/nofx/web/dist/ | head -10')
print(stdout.read().decode())

# 3. 检查 NOFX 是否有 systemd 服务
print("\n3. 检查 NOFX 服务:")
stdin, stdout, stderr = ssh.exec_command('systemctl list-units --type=service | grep -i nofx || echo "无 NOFX systemd 服务"')
print(stdout.read().decode())

# 4. 启动 NOFX 后端（后台运行）
print("\n4. 启动 NOFX 后端...")
# 先停止可能存在的进程
stdin, stdout, stderr = ssh.exec_command('pkill -f "/opt/nofx/nofx" 2>/dev/null || true')
stdout.read()

# 后台启动
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/nofx
nohup ./nofx > /var/log/nofx.log 2>&1 &
sleep 2
ps aux | grep nofx | grep -v grep
''')
print(stdout.read().decode())

# 5. 检查日志
print("\n5. 检查启动日志:")
stdin, stdout, stderr = ssh.exec_command('tail -20 /var/log/nofx.log 2>/dev/null || echo "日志文件不存在"')
print(stdout.read().decode())

# 6. 测试 API
print("\n6. 测试 NOFX API:")
stdin, stdout, stderr = ssh.exec_command('curl -s --max-time 5 http://127.0.0.1:8080/api/config 2>/dev/null | head -c 200 || echo "API 未响应"')
print(stdout.read().decode())

print("\n" + "=" * 60)
print("完成!")
print("=" * 60)
print("\nNOFX 访问地址: https://cornna.abrdns.com/nofx/")

ssh.close()

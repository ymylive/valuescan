#!/usr/bin/env python3
"""验证 NOFX 运行状态"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print("=" * 60)
print("验证 NOFX 运行状态")
print("=" * 60)

# 1. 检查进程
print("\n1. 检查进程:")
stdin, stdout, stderr = ssh.exec_command('ps aux | grep nofx | grep -v grep')
print(stdout.read().decode() or "(无进程)")

# 2. 检查端口
print("\n2. 检查端口:")
stdin, stdout, stderr = ssh.exec_command('ss -tlnp | grep 8080')
print(stdout.read().decode() or "(端口未监听)")

# 3. 测试 API
print("\n3. 测试 API:")
stdin, stdout, stderr = ssh.exec_command('curl -s --max-time 5 http://127.0.0.1:8080/api/config')
print(stdout.read().decode() or "(无响应)")

# 4. 检查日志
print("\n4. 检查最新日志:")
stdin, stdout, stderr = ssh.exec_command('tail -20 /var/log/nofx.log')
print(stdout.read().decode())

# 5. 测试通过 Nginx 访问
print("\n5. 测试通过 Nginx 访问 NOFX:")
stdin, stdout, stderr = ssh.exec_command('curl -s --max-time 5 http://127.0.0.1/nofx/ | head -20')
print(stdout.read().decode() or "(无响应)")

# 6. 创建 systemd 服务文件
print("\n6. 创建 systemd 服务文件...")
service_content = '''[Unit]
Description=NOFX AI Trading System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/nofx
EnvironmentFile=/opt/nofx/.env
ExecStart=/opt/nofx/nofx
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
'''

sftp = ssh.open_sftp()
with sftp.open('/etc/systemd/system/nofx.service', 'w') as f:
    f.write(service_content)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('systemctl daemon-reload && systemctl enable nofx')
print(stdout.read().decode())
print(stderr.read().decode())

print("\n" + "=" * 60)
print("NOFX 部署完成!")
print("=" * 60)
print("\n访问地址: https://cornna.abrdns.com/nofx/")
print("管理命令:")
print("  启动: systemctl start nofx")
print("  停止: systemctl stop nofx")
print("  状态: systemctl status nofx")
print("  日志: journalctl -u nofx -f")

ssh.close()

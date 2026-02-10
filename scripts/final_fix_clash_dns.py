#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import paramiko
import sys
import codecs
import time

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password="Qq159741",
           look_for_keys=False, allow_agent=False)

print("最终修复方案：")
print("1. 停止Clash...")
stdin, stdout, stderr = ssh.exec_command("systemctl stop clash")
stdout.channel.recv_exit_status()

print("2. 备份配置...")
stdin, stdout, stderr = ssh.exec_command("cp /etc/clash/config.yaml /etc/clash/config.yaml.backup")
stdout.channel.recv_exit_status()

print("3. 移除DNS配置...")
cmd = """python3 << 'EOF'
import yaml
with open('/etc/clash/config.yaml', 'r') as f:
    config = yaml.safe_load(f)
if 'dns' in config:
    del config['dns']
with open('/etc/clash/config.yaml', 'w') as f:
    yaml.dump(config, f, allow_unicode=True)
print("DNS removed")
EOF
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
result = stdout.read().decode('utf-8', errors='ignore')
print(f"   {result}")

print("4. 启动Clash...")
stdin, stdout, stderr = ssh.exec_command("systemctl start clash")
stdout.channel.recv_exit_status()

print("5. 等待20秒...")
time.sleep(20)

print("6. 检查状态...")
stdin, stdout, stderr = ssh.exec_command("systemctl is-active clash")
status = stdout.read().decode('utf-8', errors='ignore').strip()
print(f"   Clash状态: {status}")

print("7. 检查端口...")
stdin, stdout, stderr = ssh.exec_command("netstat -tuln | grep 7890")
ports = stdout.read().decode('utf-8', errors='ignore')
if ports:
    print("   ✅ 端口7890已监听")
else:
    print("   ❌ 端口未监听")

ssh.close()
print("\n完成！")

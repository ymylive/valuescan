#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import paramiko
import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password="Qq159741",
           look_for_keys=False, allow_agent=False)

print("1. 检查Clash是否已安装...")
stdin, stdout, stderr = ssh.exec_command("which clash")
clash_path = stdout.read().decode('utf-8', errors='ignore').strip()
if clash_path:
    print(f"✅ Clash已安装: {clash_path}")
else:
    print("❌ Clash未安装")

print("\n2. 检查Clash服务状态...")
stdin, stdout, stderr = ssh.exec_command("systemctl status clash --no-pager | head -10")
status = stdout.read().decode('utf-8', errors='ignore')
print(status if status else "Clash服务未配置")

print("\n3. 检查当前代理配置...")
stdin, stdout, stderr = ssh.exec_command("cat /root/.config/clash/config.yaml 2>/dev/null | head -30")
config = stdout.read().decode('utf-8', errors='ignore')
print(config if config else "配置文件不存在")

ssh.close()

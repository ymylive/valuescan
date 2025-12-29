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

print("1. 等待Clash初始化（15秒）...")
time.sleep(15)

print("\n2. 检查Clash状态...")
stdin, stdout, stderr = ssh.exec_command("systemctl status clash --no-pager | head -10")
status = stdout.read().decode('utf-8', errors='ignore')
print(status)

print("\n3. 检查代理端口...")
stdin, stdout, stderr = ssh.exec_command("netstat -tuln | grep -E '7890|7891'")
ports = stdout.read().decode('utf-8', errors='ignore')
if ports:
    print("✅ 端口已监听:")
    print(ports)
else:
    print("❌ 端口未监听")

ssh.close()

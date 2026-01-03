#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整修复Clash并测试图表生成
"""
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

print("=" * 60)
print("完整修复方案")
print("=" * 60)

print("\n步骤1: 停止Clash...")
stdin, stdout, stderr = ssh.exec_command("systemctl stop clash")
stdout.channel.recv_exit_status()
print("✅ 已停止")

print("\n步骤2: 检查配置文件...")
stdin, stdout, stderr = ssh.exec_command("head -20 /etc/clash/config.yaml")
config = stdout.read().decode('utf-8', errors='ignore')
print(config)

print("\n步骤3: 启动Clash...")
stdin, stdout, stderr = ssh.exec_command("systemctl start clash")
stdout.channel.recv_exit_status()
print("✅ 已启动")

print("\n步骤4: 等待30秒初始化...")
time.sleep(30)

print("\n步骤5: 检查端口...")
stdin, stdout, stderr = ssh.exec_command("netstat -tuln | grep 7890")
ports = stdout.read().decode('utf-8', errors='ignore')
if ports:
    print("✅ 端口7890已监听")
    print(ports)
else:
    print("❌ 端口7890未监听")
    print("\n检查Clash错误...")
    stdin, stdout, stderr = ssh.exec_command("journalctl -u clash -n 10 --no-pager")
    logs = stdout.read().decode('utf-8', errors='ignore')
    print(logs[-500:])

ssh.close()
print("\n" + "=" * 60)

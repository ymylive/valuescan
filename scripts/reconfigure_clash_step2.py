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

print("1. 修改DNS配置...")
# 完全禁用DNS
fix_cmd = """
sed -i '/^dns:/,/^[a-z]/{ /^dns:/d; /^  /d; }' /etc/clash/config.yaml
"""
stdin, stdout, stderr = ssh.exec_command(fix_cmd)
stdout.channel.recv_exit_status()
print("✅ DNS已禁用")

print("\n2. 启动Clash...")
stdin, stdout, stderr = ssh.exec_command("systemctl start clash")
stdout.channel.recv_exit_status()
print("✅ 已启动")

ssh.close()

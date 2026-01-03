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

print("1. 修改Clash配置，禁用DNS...")

# 修改配置文件，禁用DNS
fix_script = """
sed -i 's/^dns:/# dns:/g' /etc/clash/config.yaml
sed -i 's/^  enable: true/  # enable: true/g' /etc/clash/config.yaml
sed -i 's/^  listen:/  # listen:/g' /etc/clash/config.yaml
sed -i 's/^  enhanced-mode:/  # enhanced-mode:/g' /etc/clash/config.yaml
"""

stdin, stdout, stderr = ssh.exec_command(fix_script)
stdout.channel.recv_exit_status()
print("✅ DNS配置已禁用")

ssh.close()

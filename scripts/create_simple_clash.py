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

print("1. 创建简化的Clash配置...")

# 创建一个最简单的配置，只保留必要的代理设置
simple_config = """port: 7890
socks-port: 7891
allow-lan: false
mode: rule
log-level: info
external-controller: 127.0.0.1:9090

proxies:

proxy-groups:
  - name: PROXY
    type: select
    proxies:
      - DIRECT

rules:
  - MATCH,PROXY
"""

sftp = ssh.open_sftp()
with sftp.open('/tmp/simple_clash.yaml', 'w') as f:
    f.write(simple_config)
sftp.close()

print("✅ 简化配置已创建")

ssh.close()

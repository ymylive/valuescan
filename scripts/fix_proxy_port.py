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

print("1. 修改config.py使用7891端口...")
stdin, stdout, stderr = ssh.exec_command(
    'sed -i \'s/SOCKS5_PROXY = "socks5:\\/\\/127.0.0.1:7890"/SOCKS5_PROXY = "socks5:\\/\\/127.0.0.1:7891"/g\' '
    '/root/valuescan/signal_monitor/config.py'
)
stdout.channel.recv_exit_status()

# 验证修改
stdin, stdout, stderr = ssh.exec_command('grep SOCKS5_PROXY /root/valuescan/signal_monitor/config.py | head -1')
result = stdout.read().decode('utf-8', errors='ignore')
print(f"   {result.strip()}")

print("\n2. 重启valuescan-signal服务...")
stdin, stdout, stderr = ssh.exec_command('systemctl restart valuescan-signal')
stdout.channel.recv_exit_status()
print("   ✅ 服务已重启")

ssh.close()
print("\n完成！")

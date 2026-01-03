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

print("搜索图表生成后的所有日志（包括错误和警告）...")
stdin, stdout, stderr = ssh.exec_command(
    "journalctl -u valuescan-signal --since '10 minutes ago' | "
    "grep -A 5 '生成图表 v10: RAVEUSDT'"
)
output = stdout.read().decode('utf-8', errors='ignore')
print(output)

print("\n" + "="*60)
print("搜索是否有图表相关的错误或警告...")
stdin, stdout, stderr = ssh.exec_command(
    "journalctl -u valuescan-signal --since '10 minutes ago' | "
    "grep -E 'Pro图表|编辑消息|edit.*photo' -i"
)
output2 = stdout.read().decode('utf-8', errors='ignore')
print(output2 if output2 else "未找到相关日志")

ssh.close()

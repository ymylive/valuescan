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

print("检查ETH图表生成的完整日志（包括超时和错误）...")
stdin, stdout, stderr = ssh.exec_command(
    "journalctl --since '5 minutes ago' | "
    "grep -E '20251225_065701_260746|ETH.*图表|超时|异常|traceback' -A 5 | tail -100"
)
output = stdout.read().decode('utf-8', errors='ignore')
print(output if output else "未找到相关日志")

ssh.close()

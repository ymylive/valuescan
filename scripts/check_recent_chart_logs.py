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

print("检查最近2分钟的完整日志（包含所有图表相关信息）...")
stdin, stdout, stderr = ssh.exec_command(
    "journalctl --since '2 minutes ago' | "
    "grep -E 'BTC|图表|chart|编辑|超时|异常|traceback' -i | tail -50"
)
output = stdout.read().decode('utf-8', errors='ignore')
print(output if output else "未找到相关日志")

ssh.close()

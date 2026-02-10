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

print("等待5秒让图表生成完成...")
time.sleep(5)

# 检查最近的日志，查看图表生成情况
stdin, stdout, stderr = ssh.exec_command(
    "journalctl -u valuescan-signal -n 50 --since '1 minute ago' | grep -E '图表|chart|编辑|edit'"
)

output = stdout.read().decode('utf-8', errors='ignore')
print("\n=== 图表生成日志 ===")
print(output if output else "未找到图表相关日志")

ssh.close()

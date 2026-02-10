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

print("检查测试脚本的标准输出...")
stdin, stdout, stderr = ssh.exec_command(
    "journalctl --since '5 minutes ago' | grep -E '测试|图表|编辑|✅|❌' | tail -30"
)
output = stdout.read().decode('utf-8', errors='ignore')
print(output if output else "未找到相关日志")

print("\n检查是否有Python错误...")
stdin, stdout, stderr = ssh.exec_command(
    "journalctl --since '5 minutes ago' | grep -i 'error\\|exception\\|traceback' | tail -20"
)
errors = stdout.read().decode('utf-8', errors='ignore')
if errors:
    print(errors)
else:
    print("未发现错误")

ssh.close()

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

print("检查VPS上的测试脚本执行情况...")
stdin, stdout, stderr = ssh.exec_command(
    "ps aux | grep test_chart"
)
print(stdout.read().decode('utf-8', errors='ignore'))

print("\n检查最近的日志...")
stdin, stdout, stderr = ssh.exec_command(
    "tail -50 /root/valuescan/signal_monitor/logs/*.log 2>/dev/null || echo '日志文件不存在'"
)
print(stdout.read().decode('utf-8', errors='ignore'))

ssh.close()

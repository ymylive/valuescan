#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import paramiko
import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password="Qq159741", look_for_keys=False, allow_agent=False)

# 检查send_message_with_async_chart函数的实现
stdin, stdout, stderr = ssh.exec_command("grep -A 50 'def send_message_with_async_chart' /root/valuescan/signal_monitor/telegram.py")
print(stdout.read().decode('utf-8', errors='ignore'))

ssh.close()

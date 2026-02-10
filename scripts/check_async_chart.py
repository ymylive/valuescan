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

# 检查telegram.py中的异步图表函数
stdin, stdout, stderr = ssh.exec_command("grep -A 20 'def send_message_and_generate_chart_async' /root/valuescan/signal_monitor/telegram.py | head -25")
print(stdout.read().decode('utf-8', errors='ignore'))

ssh.close()

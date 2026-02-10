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

# 检查message_handler.py中的图表生成逻辑
stdin, stdout, stderr = ssh.exec_command("grep -n 'ENABLE_PRO_CHART\\|generate_chart\\|异步图表' /root/valuescan/signal_monitor/message_handler.py | head -30")
print(stdout.read().decode('utf-8', errors='ignore'))

ssh.close()

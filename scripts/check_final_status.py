#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import paramiko
import time
import sys

# 修复Windows控制台编码
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password="Qq159741", look_for_keys=False, allow_agent=False)

time.sleep(3)

stdin, stdout, stderr = ssh.exec_command("systemctl status valuescan-signal --no-pager -n 30")
print(stdout.read().decode('utf-8', errors='ignore'))

ssh.close()

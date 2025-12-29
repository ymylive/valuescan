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

# 检查最近所有日志
stdin, stdout, stderr = ssh.exec_command(
    "journalctl -u valuescan-signal --since '2 minutes ago' -n 100"
)

output = stdout.read().decode('utf-8', errors='ignore')
print(output)

ssh.close()

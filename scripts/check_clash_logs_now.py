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

print("检查Clash详细日志...")
stdin, stdout, stderr = ssh.exec_command(
    "journalctl -u clash --since '2 minutes ago' --no-pager | tail -30"
)
logs = stdout.read().decode('utf-8', errors='ignore')
print(logs)

ssh.close()

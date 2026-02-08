#!/usr/bin/env python3
import os
import paramiko

HOST = "82.158.88.34"
USER = "root"
PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "Qq159741")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD)

# Get more logs with Gemini context
stdin, stdout, stderr = ssh.exec_command('journalctl -u nofx -n 500 --no-pager | tail -200')
logs = stdout.read().decode()

# Filter for relevant lines
keywords = ['Gemini', 'SafeFallback', 'JSON', 'decision', 'Content preview', 'gemini']
for line in logs.split('\n'):
    for kw in keywords:
        if kw.lower() in line.lower():
            print(line)
            break

ssh.close()

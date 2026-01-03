#!/usr/bin/env python3
import os
import paramiko

HOST = "82.158.88.34"
USER = "root"
PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "Qq159741")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD)

# Check logs for model queries
cmd = "journalctl -u nofx -n 300 --no-pager"
stdin, stdout, stderr = ssh.exec_command(cmd)
output = stdout.read().decode()

print("=== Looking for model-related logs ===")
for line in output.split('\n'):
    if 'Model' in line or 'model' in line or 'FileUpload' in line:
        print(line)

ssh.close()

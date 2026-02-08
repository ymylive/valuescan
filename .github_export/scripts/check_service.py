#!/usr/bin/env python3
import os
import paramiko

HOST = "82.158.88.34"
USER = "root"
PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "Qq159741")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD)

# Check which binary the service uses
commands = [
    "cat /etc/systemd/system/nofx.service",
    "ls -la /opt/nofx/nofx* | head -5",
    "md5sum /opt/nofx/store/ai_model.go",
]

for cmd in commands:
    print(f"\n=== {cmd} ===")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print(stdout.read().decode())

ssh.close()

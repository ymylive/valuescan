#!/usr/bin/env python3
import os
import paramiko

HOST = "82.158.88.34"
USER = "root"
PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "Qq159741")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD)

# Check VPS nofx directory structure
commands = [
    "ls -la /opt/nofx/",
    "ls -la /opt/nofx/store/ 2>/dev/null || echo 'store dir not found'",
    "ls -la /opt/nofx/api/ 2>/dev/null || echo 'api dir not found'",
    "ls -la /opt/nofx/decision/ 2>/dev/null || echo 'decision dir not found'",
    "find /opt/nofx -name '*.go' -type f | head -30",
]

for cmd in commands:
    print(f"\n=== {cmd} ===")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print(f"STDERR: {err}")

ssh.close()

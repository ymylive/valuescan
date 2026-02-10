#!/usr/bin/env python3
"""Check NOFX logs for Gemini response issues."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password='Qq159741', timeout=30)

# Find NOFX data directory and recent decision files
commands = [
    'ls -la /opt/nofx/data/',
    'find /opt/nofx/data -name "decision*.json" -mmin -120 | head -5',
    'cat $(find /opt/nofx/data -name "decision*.json" -mmin -120 | head -1) 2>/dev/null | head -200',
]

for cmd in commands:
    print(f"\n=== {cmd} ===")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out[:5000])
    if err:
        print(f"STDERR: {err[:500]}")

ssh.close()

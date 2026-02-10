#!/usr/bin/env python3
"""Check recent NOFX logs."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password='Qq159741', timeout=30)

# Get recent logs
stdin, stdout, stderr = ssh.exec_command('journalctl -u nofx --no-pager -n 100')
output = stdout.read().decode()
print(output[-5000:] if len(output) > 5000 else output)

ssh.close()

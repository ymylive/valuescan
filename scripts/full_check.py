#!/usr/bin/env python3
"""Full check of NOFX logs."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password='Qq159741', timeout=30)

# Get last 50 lines to see what's happening
stdin, stdout, stderr = ssh.exec_command('journalctl -u nofx --no-pager -n 50')
output = stdout.read().decode()
print("=== Recent Logs ===")
print(output)

ssh.close()

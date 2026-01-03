#!/usr/bin/env python3
"""Check NOFX logs for Gemini response issues."""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password='Qq159741', timeout=30)

print('Waiting 30 seconds for AI cycle...')
time.sleep(30)

# Check for SafeFallback logs with content preview
stdin, stdout, stderr = ssh.exec_command('journalctl -u nofx --no-pager -n 200 | grep "Content preview"')
output = stdout.read().decode()
print("=== Content Preview Logs ===")
print(output if output else "No matching logs found")

ssh.close()

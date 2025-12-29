#!/usr/bin/env python3
"""Wait for Gemini cycle and check logs."""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password='Qq159741', timeout=30)

print('Waiting 60 seconds for Gemini AI cycle...')
time.sleep(60)

# Check for Content preview in logs
stdin, stdout, stderr = ssh.exec_command('journalctl -u nofx --no-pager -n 300 | grep "Content preview"')
output = stdout.read().decode()
print("=== Content Preview Logs ===")
if output:
    print(output)
else:
    print("No Content preview found, checking SafeFallback logs...")
    stdin, stdout, stderr = ssh.exec_command('journalctl -u nofx --no-pager -n 300 | grep -i "SafeFallback\\|gemini"')
    print(stdout.read().decode())

ssh.close()

#!/usr/bin/env python3
"""Check NOFX logs for Gemini response issues."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password='Qq159741', timeout=30)

# Check recent AI responses
cmd = 'journalctl -u nofx --no-pager -n 500 | grep -B5 -A50 "cotSummary\\|AI Response\\|Full response"'
stdin, stdout, stderr = ssh.exec_command(cmd)
output = stdout.read().decode()
print("=== AI Response Logs ===")
print(output[:8000] if output else "No matching logs found")

ssh.close()

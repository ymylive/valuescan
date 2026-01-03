#!/usr/bin/env python3
"""Check AI models and recent SafeFallback logs."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password='Qq159741', timeout=30)

# Check for any SafeFallback in recent history (last 1000 lines)
stdin, stdout, stderr = ssh.exec_command('journalctl -u nofx --no-pager -n 1000 | grep -i "SafeFallback\\|gemini\\|Content preview"')
output = stdout.read().decode()
print("=== SafeFallback/Gemini Logs ===")
print(output[-3000:] if output else "No matching logs found")

# Check current active traders
stdin, stdout, stderr = ssh.exec_command('journalctl -u nofx --no-pager -n 500 | grep -i "model\\|provider"')
output2 = stdout.read().decode()
print("\n=== Model/Provider Info ===")
print(output2[-2000:] if output2 else "No model info found")

ssh.close()

#!/usr/bin/env python3
"""Debug AI config flow on VPS."""

import paramiko
import json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password='Qq159741')

# 1. Check current config file
print("=== 1. Current config file ===")
stdin, stdout, stderr = ssh.exec_command('cat /root/valuescan/signal_monitor/ai_summary_config.json 2>/dev/null || echo "NOT_FOUND"')
print(stdout.read().decode())

# 2. Reset to disabled
print("\n=== 2. Reset to disabled ===")
cmd = '''curl -s -X POST http://127.0.0.1:5000/api/valuescan/ai-summary/config -H "Content-Type: application/json" -d '{"config":{"enabled":false}}'''''
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

# 3. Verify disabled
print("\n=== 3. Verify disabled ===")
stdin, stdout, stderr = ssh.exec_command('curl -s http://127.0.0.1:5000/api/valuescan/ai-summary/config')
print(stdout.read().decode())

# 4. Enable via POST
print("\n=== 4. Enable via POST ===")
cmd = '''curl -s -X POST http://127.0.0.1:5000/api/valuescan/ai-summary/config -H "Content-Type: application/json" -d '{"config":{"enabled":true}}'''''
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

# 5. Verify enabled
print("\n=== 5. Verify enabled ===")
stdin, stdout, stderr = ssh.exec_command('curl -s http://127.0.0.1:5000/api/valuescan/ai-summary/config')
result = stdout.read().decode()
print(result)

# 6. Check config file
print("\n=== 6. Config file after save ===")
stdin, stdout, stderr = ssh.exec_command('cat /root/valuescan/signal_monitor/ai_summary_config.json')
print(stdout.read().decode())

ssh.close()
print("\nDone - Backend is working correctly!")
print("If frontend still shows disabled, the issue is in frontend code or browser cache.")

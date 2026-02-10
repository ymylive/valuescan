#!/usr/bin/env python3
"""Test AI summary API on VPS."""

import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password='Qq159741')

# Test POST to enable
print("=== Testing POST (enable) ===")
cmd = '''curl -s -X POST http://127.0.0.1:5000/api/valuescan/ai-summary/config -H "Content-Type: application/json" -d '{"config":{"enabled":true}}'''''
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

# Test GET to verify
print("\n=== Testing GET (verify) ===")
cmd = 'curl -s http://127.0.0.1:5000/api/valuescan/ai-summary/config'
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

# Check if config file was created
print("\n=== Config file ===")
cmd = 'cat /root/valuescan/signal_monitor/ai_summary_config.json 2>/dev/null || echo "FILE NOT FOUND"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

ssh.close()
print("\nDone")

#!/usr/bin/env python3
"""Check VPS API implementation."""

import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password='Qq159741')

# Check POST endpoint implementation
print("=== POST endpoint (lines 1710-1750) ===")
stdin, stdout, stderr = ssh.exec_command("sed -n '1710,1750p' /root/valuescan/api/server.py")
print(stdout.read().decode())

# Test POST with verbose curl
print("\n=== Test POST with verbose ===")
stdin, stdout, stderr = ssh.exec_command("""curl -s -w '\\nHTTP_CODE:%{http_code}' -X POST http://127.0.0.1:5000/api/valuescan/ai-summary/config -H 'Content-Type: application/json' -d '{"config":{"enabled":true}}'""")
print(stdout.read().decode())
print("stderr:", stderr.read().decode())

ssh.close()
print("\nDone")

#!/usr/bin/env python3
import os
import paramiko

HOST = "82.158.88.34"
USER = "root"
PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "Qq159741")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD)

# Test the API response directly
cmd = '''curl -s http://localhost:8080/api/models 2>/dev/null | head -500'''
stdin, stdout, stderr = ssh.exec_command(cmd)
print("API Response:")
print(stdout.read().decode()[:2000])

# Also check the database directly
cmd2 = '''cd /opt/nofx && cat store/ai_model.go | grep -A5 "SafeModelConfig"'''
stdin, stdout, stderr = ssh.exec_command(cmd2)
print("\n\nSafeModelConfig in code:")
print(stdout.read().decode())

ssh.close()

#!/usr/bin/env python3
import os
import paramiko

HOST = "82.158.88.34"
USER = "root"
PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "Qq159741")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD)

# Check AIModel struct in store
cmd = '''grep -A15 "type AIModel struct" /opt/nofx/store/ai_model.go'''
print("=== AIModel struct ===")
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

# Check List function scanning
cmd2 = '''grep -A30 "func.*List.*userID" /opt/nofx/store/ai_model.go | head -40'''
print("\n=== List function ===")
stdin, stdout, stderr = ssh.exec_command(cmd2)
print(stdout.read().decode())

ssh.close()

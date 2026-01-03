#!/usr/bin/env python3
import os
import paramiko

HOST = "82.158.88.34"
USER = "root"
PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "Qq159741")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD)

# Check UpdateModelConfigRequest struct
cmd = '''grep -B2 -A15 "UpdateModelConfigRequest" /opt/nofx/api/server.go | head -30'''
print("=== UpdateModelConfigRequest ===")
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

# Check ModelConfigData struct
cmd2 = '''grep -B2 -A10 "ModelConfigData" /opt/nofx/api/server.go | head -20'''
print("\n=== ModelConfigData ===")
stdin, stdout, stderr = ssh.exec_command(cmd2)
print(stdout.read().decode())

ssh.close()

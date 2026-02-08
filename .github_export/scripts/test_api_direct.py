#!/usr/bin/env python3
"""Test API response directly from VPS"""
import os
import paramiko
import json

HOST = "82.158.88.34"
USER = "root"
PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "Qq159741")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD)

# Get a valid JWT token first (we'll use a test approach)
# Check what the API returns for models by looking at logs after a page refresh
print("Checking recent API calls...")
cmd = "journalctl -u nofx -n 100 --no-pager | grep -E '(GET.*models|Found.*AI model)'"
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

# Check the actual JSON being returned by looking at the code
print("\n\nChecking JSON tags in SafeModelConfig...")
cmd2 = 'grep -A1 "UseFileUpload" /opt/nofx/api/server.go | head -10'
stdin, stdout, stderr = ssh.exec_command(cmd2)
print(stdout.read().decode())

ssh.close()

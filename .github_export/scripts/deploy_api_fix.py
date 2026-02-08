#!/usr/bin/env python3
"""
Deploy the api/server.py fix to VPS
"""
import os
import sys

try:
    import paramiko
except ImportError:
    print("Installing paramiko...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "paramiko"], check=True)
    import paramiko

VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "")

if not VPS_PASSWORD:
    print("Error: VALUESCAN_VPS_PASSWORD environment variable not set")
    exit(1)

print(f"Connecting to {VPS_HOST}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD)

# Upload the fixed api/server.py
print("Uploading api/server.py...")
sftp = ssh.open_sftp()

local_path = "api/server.py"
remote_path = "/root/valuescan/api/server.py"

sftp.put(local_path, remote_path)
print(f"Uploaded {local_path} -> {remote_path}")

sftp.close()

# Restart the API service
print("\nRestarting valuescan-api service...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart valuescan-api")
stdout.channel.recv_exit_status()

import time
time.sleep(2)

# Check status
print("\nChecking service status...")
stdin, stdout, stderr = ssh.exec_command("systemctl status valuescan-api --no-pager -l | head -20")
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err)

ssh.close()
print("\nDone!")

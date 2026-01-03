#!/usr/bin/env python3
"""
Check VPS services status
"""
import os
import sys

try:
    import paramiko
except ImportError:
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

services = ['valuescan-signal', 'valuescan-trader', 'valuescan-api']

for service in services:
    print(f"\n{'='*60}")
    print(f"Service: {service}")
    print('='*60)
    stdin, stdout, stderr = ssh.exec_command(f"systemctl status {service} --no-pager -l | head -15")
    print(stdout.read().decode())

ssh.close()

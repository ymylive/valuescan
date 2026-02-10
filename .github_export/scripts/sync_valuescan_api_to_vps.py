#!/usr/bin/env python3
"""Sync valuescan_api module to VPS"""
import paramiko
import os
from pathlib import Path

LOCAL_DIR = Path(__file__).parent.parent / "valuescan_api"
REMOTE_DIR = "/root/valuescan/valuescan_api"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password="Qq159741")

# Create remote directory
ssh.exec_command(f"mkdir -p {REMOTE_DIR}")

sftp = ssh.open_sftp()

# Upload all Python files
for f in LOCAL_DIR.glob("*.py"):
    remote_path = f"{REMOTE_DIR}/{f.name}"
    print(f"Uploading {f.name}...")
    sftp.put(str(f), remote_path)

# Upload JSON files if any
for f in LOCAL_DIR.glob("*.json"):
    remote_path = f"{REMOTE_DIR}/{f.name}"
    print(f"Uploading {f.name}...")
    sftp.put(str(f), remote_path)

sftp.close()

# Verify
stdin, stdout, stderr = ssh.exec_command(f"ls -la {REMOTE_DIR}/")
print("\nUploaded files:")
print(stdout.read().decode())

ssh.close()
print("Done!")

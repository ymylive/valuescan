#!/usr/bin/env python3
"""Sync token from VPS"""
import paramiko
import json
from pathlib import Path

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password="Qq159741")

sftp = ssh.open_sftp()
local = Path(__file__).parent.parent / "valuescan_localstorage.json"
sftp.get("/root/valuescan/signal_monitor/valuescan_localstorage.json", str(local))
sftp.close()
ssh.close()

data = json.loads(local.read_text(encoding="utf-8"))
token = data.get("account_token", "")
print(f"Token: {token[:50]}..." if token else "No token!")
print(f"Saved to {local}")

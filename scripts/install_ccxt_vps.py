#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Install CCXT on VPS (Python 3.9).
Uses VALUESCAN_VPS_PASSWORD env var.
"""
import os
import sys
import codecs

import paramiko

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

host = os.environ.get("VALUESCAN_VPS_HOST", "82.158.88.34")
user = os.environ.get("VALUESCAN_VPS_USER", "root")
password = os.environ.get("VALUESCAN_VPS_PASSWORD", "")
port = int(os.environ.get("VALUESCAN_VPS_PORT", "22"))

if not password:
    raise SystemExit("Missing VALUESCAN_VPS_PASSWORD env var.")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password, port=port, look_for_keys=False, allow_agent=False)

print("Installing ccxt on VPS...")
stdin, stdout, stderr = ssh.exec_command("python3.9 -m pip install -U ccxt")
exit_status = stdout.channel.recv_exit_status()
output = stdout.read().decode("utf-8", errors="ignore")
error = stderr.read().decode("utf-8", errors="ignore")

if exit_status == 0:
    print("✅ ccxt installed")
else:
    print("❌ ccxt install failed")
    print(output)
    print(error)

ssh.close()

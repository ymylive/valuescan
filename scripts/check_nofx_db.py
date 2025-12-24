#!/usr/bin/env python3
import os
import paramiko

HOST = "82.158.88.34"
USER = "root"
PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "Qq159741")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD)

# Check AI models table schema and data
commands = [
    ("PRAGMA table_info(ai_models)", "Table schema"),
    ("SELECT id, name, provider, use_file_upload FROM ai_models", "AI Models"),
    ("SELECT * FROM ai_models LIMIT 1", "Full row example"),
]

for sql, desc in commands:
    print(f"\n=== {desc} ===")
    cmd = f'cd /opt/nofx && sqlite3 data/data.db "{sql};"'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out)
    if err:
        print(f"Error: {err}")

ssh.close()

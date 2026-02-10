#!/usr/bin/env python3
import os
import paramiko

HOST = "82.158.88.34"
USER = "root"
PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "Qq159741")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD)

# Add logging to API to see what's returned
cmd = """grep -n 'c.JSON.*safeModels' /opt/nofx/api/server.go"""
print("=== API response line ===")
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

# Check recent logs for model queries
cmd2 = "journalctl -u nofx -n 30 --no-pager | grep -i 'model config'"
print("\n=== Recent model config logs ===")
stdin, stdout, stderr = ssh.exec_command(cmd2)
print(stdout.read().decode())

# Check if use_file_upload column has data
cmd3 = "cd /opt/nofx && echo '.mode column' '.headers on' 'SELECT id, provider, use_file_upload FROM ai_models LIMIT 10;' | cat - | xargs -I {} echo {}"
print("\n=== Database query attempt ===")
stdin, stdout, stderr = ssh.exec_command(cmd3)
print(stdout.read().decode())
print(stderr.read().decode())

ssh.close()

#!/usr/bin/env python3
import paramiko
import json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password='Qq159741')

stdin, stdout, stderr = ssh.exec_command('curl -s http://127.0.0.1:5000/api/config')
data = json.loads(stdout.read().decode())

signal = data.get('signal', {})
ai_keys = [k for k in signal.keys() if 'ai_summary' in k]
print("AI keys in signal config:", ai_keys)
for k in ai_keys:
    print(f"  {k}: {signal[k]}")

ssh.close()

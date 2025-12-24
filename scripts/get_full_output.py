#!/usr/bin/env python3
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password='Qq159741')

stdin, stdout, stderr = ssh.exec_command('cat /tmp/ai_output.txt')
output = stdout.read().decode()
print(output)
ssh.close()

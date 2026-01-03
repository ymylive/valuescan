#!/usr/bin/env python3
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password='Qq159741')

# Check polling monitor code
stdin, stdout, stderr = ssh.exec_command('sed -n "690,710p" /root/valuescan/signal_monitor/polling_monitor.py')
print('Polling monitor code (lines 690-710):')
print(stdout.read().decode())

# Check recent logs
stdin, stdout, stderr = ssh.exec_command('journalctl -u valuescan-signal --no-pager -n 50')
print('\nRecent signal monitor logs:')
print(stdout.read().decode())

ssh.close()

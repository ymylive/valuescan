#!/usr/bin/env python3
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password='Qq159741', timeout=30)

# Trigger AI analysis with Telegram
stdin, stdout, stderr = ssh.exec_command('cd /root/valuescan/signal_monitor && python3 -c "from ai_market_summary import generate_market_summary; generate_market_summary(force=True)" 2>&1')
print(stdout.read().decode())

ssh.close()

#!/usr/bin/env python3
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password='Qq159741', timeout=30)

# Check nginx config
print('=== Nginx Config ===')
stdin, stdout, stderr = ssh.exec_command('cat /etc/nginx/conf.d/valuescan.conf', timeout=10)
print(stdout.read().decode())

# Check dist files
print('\n=== Dist files ===')
stdin, stdout, stderr = ssh.exec_command('ls -la /root/valuescan/web/dist/', timeout=10)
print(stdout.read().decode())

# Check if AI sections exist in source
print('\n=== AI sections in source ===')
stdin, stdout, stderr = ssh.exec_command("grep -c 'AI Signal' /root/valuescan/web/src/components/valuescan/SignalMonitorConfigSection.tsx", timeout=10)
print(f"AI Signal mentions: {stdout.read().decode().strip()}")

stdin, stdout, stderr = ssh.exec_command("grep -c 'AI Market' /root/valuescan/web/src/components/valuescan/SignalMonitorConfigSection.tsx", timeout=10)
print(f"AI Market mentions: {stdout.read().decode().strip()}")

# Check built JS for AI
print('\n=== Check built JS ===')
stdin, stdout, stderr = ssh.exec_command("strings /root/valuescan/web/dist/assets/*.js | grep -c 'AI Signal'", timeout=10)
print(f"AI Signal in built JS: {stdout.read().decode().strip()}")

ssh.close()

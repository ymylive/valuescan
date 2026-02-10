#!/usr/bin/env python3
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password='Qq159741', timeout=30)

# Check cornna.abrdns.com nginx config
print('=== cornna.abrdns.com.conf ===')
stdin, stdout, stderr = ssh.exec_command('cat /etc/nginx/conf.d/cornna.abrdns.com.conf', timeout=10)
print(stdout.read().decode())

# Check if frontend is being served from correct path
print('\n=== Check web dist ===')
stdin, stdout, stderr = ssh.exec_command('ls -la /root/valuescan/web/dist/assets/', timeout=10)
print(stdout.read().decode())

# Reload nginx
print('\n=== Reload nginx ===')
stdin, stdout, stderr = ssh.exec_command('nginx -t && systemctl reload nginx && echo "Nginx reloaded"', timeout=10)
print(stdout.read().decode())
print(stderr.read().decode())

ssh.close()

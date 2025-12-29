#!/usr/bin/env python3
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password='Qq159741', timeout=30)

# Check all nginx configs
print('=== All nginx configs ===')
stdin, stdout, stderr = ssh.exec_command('ls -la /etc/nginx/conf.d/ /etc/nginx/sites-enabled/ 2>/dev/null', timeout=10)
print(stdout.read().decode())

# Check nginx main config
print('\n=== Nginx main config ===')
stdin, stdout, stderr = ssh.exec_command('cat /etc/nginx/nginx.conf | head -60', timeout=10)
print(stdout.read().decode())

# Check sites-available
print('\n=== Sites available ===')
stdin, stdout, stderr = ssh.exec_command('ls -la /etc/nginx/sites-available/ 2>/dev/null', timeout=10)
print(stdout.read().decode())

# Check for cornna domain config
print('\n=== Search for cornna config ===')
stdin, stdout, stderr = ssh.exec_command('grep -r "cornna" /etc/nginx/ 2>/dev/null | head -10', timeout=10)
print(stdout.read().decode() or 'No cornna config found')

# Check listening ports
print('\n=== Nginx listening ===')
stdin, stdout, stderr = ssh.exec_command('ss -tlnp | grep nginx', timeout=10)
print(stdout.read().decode())

ssh.close()

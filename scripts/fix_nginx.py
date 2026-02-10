#!/usr/bin/env python3
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password='Qq159741', timeout=30)

# Check current /var/www/valuescan content
print('=== Current /var/www/valuescan ===')
stdin, stdout, stderr = ssh.exec_command('ls -la /var/www/valuescan/ 2>/dev/null || echo "Directory does not exist"', timeout=10)
print(stdout.read().decode())

# Copy dist files to /var/www/valuescan
print('\n=== Copying dist files ===')
stdin, stdout, stderr = ssh.exec_command('rm -rf /var/www/valuescan/* && cp -r /root/valuescan/web/dist/* /var/www/valuescan/ && echo "Files copied"', timeout=30)
print(stdout.read().decode())
print(stderr.read().decode())

# Verify
print('\n=== Verify /var/www/valuescan ===')
stdin, stdout, stderr = ssh.exec_command('ls -la /var/www/valuescan/', timeout=10)
print(stdout.read().decode())

# Check assets
print('\n=== Assets ===')
stdin, stdout, stderr = ssh.exec_command('ls -la /var/www/valuescan/assets/', timeout=10)
print(stdout.read().decode())

ssh.close()
print('\nDone!')

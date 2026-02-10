#!/usr/bin/env python3
"""VPS deployment script for frontend optimization"""
import paramiko
import time

HOST = '82.158.88.34'
USER = 'root'
PASSWORD = 'Qq159741'

def run_ssh_command(ssh, cmd, timeout=60):
    """Run SSH command and return output"""
    print(f'>>> {cmd}')
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out)
    if err:
        print(f'STDERR: {err}')
    return exit_code, out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f'Connecting to {HOST}...')
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    print('Connected!')
    
    # Check if files were synced
    run_ssh_command(ssh, 'ls -la /root/valuescan/web/src/components/ui/')
    
    # Check if node/npm is available
    run_ssh_command(ssh, 'which node && node --version')
    run_ssh_command(ssh, 'which npm && npm --version')
    
    # Check if dist exists
    run_ssh_command(ssh, 'ls -la /root/valuescan/web/dist/ 2>/dev/null | head -5 || echo "No dist folder"')
    
    # Try to build - run in background with longer wait
    print('\nStarting frontend build...')
    run_ssh_command(ssh, 'cd /root/valuescan/web && npm run build > /tmp/build.log 2>&1', timeout=300)
    
    # Check build result
    run_ssh_command(ssh, 'cat /tmp/build.log | tail -30')
    
    # Check dist after build
    run_ssh_command(ssh, 'ls -la /root/valuescan/web/dist/ 2>/dev/null | head -10')
    
    # Copy dist to /var/www/valuescan (nginx serving path)
    print('\nCopying dist to /var/www/valuescan...')
    run_ssh_command(ssh, 'rm -rf /var/www/valuescan/* && cp -r /root/valuescan/web/dist/* /var/www/valuescan/')

    # Restart nginx to serve new files
    print('\nRestarting nginx...')
    run_ssh_command(ssh, 'systemctl restart nginx && systemctl status nginx --no-pager | head -10')
    
    ssh.close()
    print('\nDeployment complete!')

if __name__ == '__main__':
    main()

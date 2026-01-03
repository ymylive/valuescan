#!/usr/bin/env python3
"""Check VPS dependencies for browser login"""
import os
import paramiko

def main():
    password = os.environ.get('VALUESCAN_VPS_PASSWORD')
    if not password:
        print("Missing VALUESCAN_VPS_PASSWORD env var")
        return
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('82.158.88.34', username='root', password=password)
    
    commands = [
        'which chromium-browser chromium google-chrome 2>/dev/null || echo "No browser found"',
        'python3.9 -c "import DrissionPage; print(DrissionPage.__version__)" 2>&1',
    ]
    
    for cmd in commands:
        print(f"Running: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print("STDOUT:", stdout.read().decode())
        print("STDERR:", stderr.read().decode())
        print()
    
    ssh.close()

if __name__ == "__main__":
    main()

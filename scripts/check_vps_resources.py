#!/usr/bin/env python3
"""Check VPS resources"""
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
    
    # Check system resources
    stdin, stdout, stderr = ssh.exec_command('free -h; echo "---"; df -h /; echo "---"; ps aux | grep -E "chrom|python" | head -20')
    print(stdout.read().decode())
    ssh.close()

if __name__ == "__main__":
    main()

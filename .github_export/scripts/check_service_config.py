#!/usr/bin/env python3
"""Check service configuration on VPS"""
import os
import paramiko

def main():
    password = os.environ.get('VALUESCAN_VPS_PASSWORD')
    if not password:
        print("Missing VALUESCAN_VPS_PASSWORD env var")
        return
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('82.158.88.34', username='root', password=password, timeout=30)
    
    print("=== valuescan-signal.service ===")
    stdin, stdout, stderr = ssh.exec_command('cat /etc/systemd/system/valuescan-signal.service')
    print(stdout.read().decode())
    
    print("\n=== Check if chromium is running ===")
    stdin, stdout, stderr = ssh.exec_command('ps aux | grep -E "chromium|chrome" | grep -v grep')
    print(stdout.read().decode() or "No chromium processes running")
    
    ssh.close()

if __name__ == "__main__":
    main()

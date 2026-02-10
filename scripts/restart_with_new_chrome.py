#!/usr/bin/env python3
"""Restart signal monitor with new Chrome instance that has --remote-allow-origins=*"""
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
    
    # Kill all chromium processes and restart signal monitor
    print("Killing all chromium processes...")
    stdin, stdout, stderr = ssh.exec_command('pkill -9 chromium; pkill -9 chrome; sleep 2')
    print(stdout.read().decode())
    
    print("Restarting signal monitor...")
    stdin, stdout, stderr = ssh.exec_command('systemctl restart valuescan-signal && sleep 10 && systemctl status valuescan-signal --no-pager | head -25')
    print(stdout.read().decode())
    
    # Check if chromium is running with the new flag
    print("\nChecking chromium arguments...")
    stdin, stdout, stderr = ssh.exec_command('ps aux | grep chromium | grep -v grep | head -3')
    output = stdout.read().decode()
    print(output)
    
    if '--remote-allow-origins' in output:
        print("\n✅ Chromium is running with --remote-allow-origins=*")
    else:
        print("\n⚠️ Chromium may not have --remote-allow-origins=* flag")
    
    ssh.close()

if __name__ == "__main__":
    main()

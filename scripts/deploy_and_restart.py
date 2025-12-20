#!/usr/bin/env python3
"""Deploy updated files and restart signal monitor"""
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
    
    # Upload updated files
    sftp = ssh.open_sftp()
    
    files_to_upload = [
        ('signal_monitor/kill_chrome.py', '/root/valuescan/signal_monitor/kill_chrome.py'),
        ('signal_monitor/api_monitor.py', '/root/valuescan/signal_monitor/api_monitor.py'),
    ]
    
    for local, remote in files_to_upload:
        print(f"Uploading {local} -> {remote}")
        sftp.put(local, remote)
    
    sftp.close()
    
    # Restart signal monitor
    print("\nRestarting signal monitor...")
    stdin, stdout, stderr = ssh.exec_command('systemctl restart valuescan-signal && sleep 5 && systemctl status valuescan-signal --no-pager | head -20')
    print(stdout.read().decode())
    
    ssh.close()
    print("Done!")

if __name__ == "__main__":
    main()

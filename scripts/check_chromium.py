#!/usr/bin/env python3
"""Check chromium status on VPS"""
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
    
    commands = [
        "chromium-browser --version",
        "which chromium-browser",
        "free -m",
        "cat /etc/os-release | head -5",
        "pip3.9 show DrissionPage | grep Version",
        # Try to run chromium directly
        "timeout 10 chromium-browser --headless --no-sandbox --disable-gpu --dump-dom https://example.com 2>&1 | head -20",
    ]
    
    for cmd in commands:
        print(f"\n=== {cmd} ===")
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
        print(stdout.read().decode())
        err = stderr.read().decode()
        if err:
            print(f"STDERR: {err}")
    
    ssh.close()

if __name__ == "__main__":
    main()

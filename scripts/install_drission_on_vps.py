#!/usr/bin/env python3
"""Install DrissionPage on VPS."""
import paramiko

HOST = "82.158.88.34"
USER = "root"
PASSWORD = "Qq159741"

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {HOST}...")
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    print("Connected!")
    
    commands = [
        "pip3 install DrissionPage --break-system-packages",
        "which chromium-browser || which chromium || which google-chrome",
    ]
    
    for cmd in commands:
        print(f"\nRunning: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=300)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode()
        err = stderr.read().decode()
        if out: print(out)
        if err: print(f"STDERR: {err}")
        print(f"Exit code: {exit_code}")
    
    ssh.close()
    print("\nDone!")

if __name__ == "__main__":
    main()

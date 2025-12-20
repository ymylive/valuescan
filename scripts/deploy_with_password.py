#!/usr/bin/env python3
"""Deploy to VPS with password authentication using paramiko."""
import paramiko
import sys

HOST = "82.158.88.34"
USER = "root"
PASSWORD = "Qq159741"

def run_ssh_command(ssh, cmd, desc):
    print(f"\n[{desc}] Running: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=300)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out: print(out)
    if err: print(f"STDERR: {err}")
    return exit_code == 0

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"Connecting to {HOST}...")
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    print("Connected!")
    
    commands = [
        ("cd /root/valuescan && git fetch origin && git reset --hard origin/master", "Git pull"),
        ("cd /root/valuescan/web && npm run build", "Build frontend"),
        ("systemctl restart valuescan-api", "Restart API"),
    ]
    
    for cmd, desc in commands:
        if not run_ssh_command(ssh, cmd, desc):
            print(f"Warning: {desc} may have failed")
    
    ssh.close()
    print("\nDeployment complete!")

if __name__ == "__main__":
    main()

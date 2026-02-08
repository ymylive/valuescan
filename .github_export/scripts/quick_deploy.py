#!/usr/bin/env python3
"""Quick deploy to VPS - git pull and restart API only."""
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
        ("cd /root/valuescan && git fetch origin && git reset --hard origin/master", "Git pull"),
        ("systemctl restart valuescan-api", "Restart API"),
    ]
    
    for cmd, desc in commands:
        print(f"\n[{desc}] Running: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode()
        err = stderr.read().decode()
        if out: print(out)
        if err: print(f"STDERR: {err}")
    
    ssh.close()
    print("\nDone!")

if __name__ == "__main__":
    main()

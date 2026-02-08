#!/usr/bin/env python3
"""Find Python 3.9 on VPS."""
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
        "which python3.9",
        "ls -la /usr/local/bin/python*",
        "ls -la /usr/bin/python*",
        "/usr/local/bin/python3.9 --version 2>/dev/null || echo 'not found'",
        "python3.9 -c 'import DrissionPage; print(DrissionPage.__version__)' 2>&1",
    ]
    
    for cmd in commands:
        print(f"\nRunning: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode()
        err = stderr.read().decode()
        if out: print(f"OUT: {out}")
        if err: print(f"ERR: {err}")
    
    ssh.close()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Test login with python3.9 on VPS."""
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
    
    # Test with python3.9
    cmd = '''cd /root/valuescan/signal_monitor && /usr/bin/python3.9 http_login.py ymy_live@outlook.com "Qq159741." 2>&1'''
    print(f"\nRunning: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=180)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode()
    print(f"Output:\n{out}")
    print(f"Exit code: {exit_code}")
    
    # Check if tokens were saved
    print("\nChecking tokens...")
    stdin, stdout, stderr = ssh.exec_command("cat /root/valuescan/signal_monitor/valuescan_localstorage.json 2>&1")
    out = stdout.read().decode()
    print(f"Tokens: {out[:200]}...")
    
    ssh.close()

if __name__ == "__main__":
    main()

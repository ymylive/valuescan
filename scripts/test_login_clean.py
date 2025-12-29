#!/usr/bin/env python3
"""Test login after stopping monitor service."""
import paramiko
import time

HOST = "82.158.88.34"
USER = "root"
PASSWORD = "Qq159741"

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {HOST}...")
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    print("Connected!")
    
    # Stop monitor service to free Chrome
    print("\nStopping monitor service...")
    ssh.exec_command("systemctl stop valuescan-monitor")
    time.sleep(2)
    
    # Kill any existing Chrome processes
    print("Killing Chrome processes...")
    ssh.exec_command("pkill -f chromium || pkill -f chrome")
    time.sleep(2)
    
    # Clear old tokens
    print("Clearing old tokens...")
    ssh.exec_command("rm -f /root/valuescan/signal_monitor/valuescan_*.json")
    
    # Test login
    cmd = '''cd /root/valuescan/signal_monitor && /usr/bin/python3.9 http_login.py ymy_live@outlook.com "Qq159741." 2>&1'''
    print(f"\nRunning login: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=180)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode()
    print(f"Output:\n{out}")
    print(f"Exit code: {exit_code}")
    
    # Check tokens
    print("\nChecking tokens...")
    stdin, stdout, stderr = ssh.exec_command("cat /root/valuescan/signal_monitor/valuescan_localstorage.json 2>&1")
    out = stdout.read().decode()
    print(f"Tokens: {out[:300]}...")
    
    ssh.close()

if __name__ == "__main__":
    main()

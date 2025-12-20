#!/usr/bin/env python3
"""Restart valuescan-trader service on VPS"""
import os
import paramiko

VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "")

def main():
    if not VPS_PASSWORD:
        print("Error: VALUESCAN_VPS_PASSWORD not set")
        return 1
    
    print(f"Connecting to {VPS_USER}@{VPS_HOST}...")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=30)
        print("Connected!")
        
        # Restart trader service
        print("\n=== Restarting valuescan-trader service ===")
        stdin, stdout, stderr = ssh.exec_command(
            "systemctl restart valuescan-trader && sleep 3 && systemctl status valuescan-trader --no-pager -l | head -40"
        )
        print(stdout.read().decode())
        err = stderr.read().decode()
        if err:
            print(f"STDERR: {err}")
        
        # Check recent logs
        print("\n=== Recent trader logs ===")
        stdin, stdout, stderr = ssh.exec_command(
            "journalctl -u valuescan-trader -n 30 --no-pager"
        )
        print(stdout.read().decode())
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        ssh.close()
    
    return 0

if __name__ == "__main__":
    exit(main())

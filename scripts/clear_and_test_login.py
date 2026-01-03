#!/usr/bin/env python3
"""Clear tokens and test login via API."""
import paramiko
import requests
import json

HOST = "82.158.88.34"
USER = "root"
PASSWORD = "Qq159741"

def main():
    # Clear tokens on VPS
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {HOST}...")
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    print("Connected!")
    
    print("\nClearing tokens...")
    ssh.exec_command("rm -f /root/valuescan/signal_monitor/valuescan_*.json")
    ssh.close()
    print("Tokens cleared!")
    
    # Test login via API
    print("\nTesting login via API...")
    try:
        resp = requests.post(
            f"http://{HOST}/api/valuescan/login",
            json={"email": "ymy_live@outlook.com", "password": "Qq159741."},
            timeout=200
        )
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

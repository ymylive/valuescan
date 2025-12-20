#!/usr/bin/env python3
"""Test ValueScan API login directly on VPS"""
import os
import paramiko

def main():
    password = os.environ.get('VALUESCAN_VPS_PASSWORD')
    if not password:
        print("Missing VALUESCAN_VPS_PASSWORD env var")
        return
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('82.158.88.34', username='root', password=password)
    
    # Test API endpoint
    test_script = '''
import requests
import json

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Origin": "https://www.valuescan.io",
    "Referer": "https://www.valuescan.io/login",
})

# Try the main login endpoint
resp = session.post("https://api.valuescan.io/api/account/login", json={
    "account": "test@test.com",
    "password": "testpassword",
    "language": "en-US"
}, timeout=30)

print("Status:", resp.status_code)
print("Response:", resp.text[:1000] if resp.text else "empty")
'''
    
    stdin, stdout, stderr = ssh.exec_command(f'python3.9 -c \'{test_script}\'')
    print("STDOUT:", stdout.read().decode())
    print("STDERR:", stderr.read().decode())
    ssh.close()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Save ValueScan tokens to VPS."""
import paramiko
import json

HOST = "82.158.88.34"
USER = "root"
PASSWORD = "Qq159741"

# Tokens from browser login
tokens = {
    "account_token": "eyJhbGciOiJIUzUxMiJ9.eyJlbmRwb2ludCI6MSwiY3JlYXRlZCI6MTc2NTk1ODQ5NTUwNywic2Vzc2lvbklkIjoiNDlhNDNmODFmNmFiNDI2Y2I0NTQzNGZjZGQxNDBjYmIiLCJ0eXBlIjoiYWNjb3VudF90b2tlbiIsImV4cCI6MTc2NTk2MjA5NSwidXNlcklkIjozMzQ1NSwiYWNjb3VudCI6InlteV9saXZlQG91dGxvb2suY29tIn0.pR3M-PHT87Gz6ePC0gEB5m3v-0k0eFVtcUbgaxfYHEoVklfgqUhHXZJsP8e30QRPu-Q9SEwj0P7Kiwr2EbjtdA",
    "refresh_token": "eyJhbGciOiJIUzUxMiJ9.eyJlbmRwb2ludCI6MSwiY3JlYXRlZCI6MTc2NTk1ODQ5NTUwNywic2Vzc2lvbklkIjoiNDlhNDNmODFmNmFiNDI2Y2I0NTQzNGZjZGQxNDBjYmIiLCJ0eXBlIjoicmVmcmVzaF90b2tlbiIsImV4cCI6MTc2NjIxNzY5NSwidXNlcklkIjozMzQ1NSwiYWNjb3VudCI6InlteV9saXZlQG91dGxvb2suY29tIn0.ukvqtOMAxIqaNbmgBdIWTDd4_46B9dFtNHXDDAuWGSBrvQetpfU9pwQ8IFco3onV8Pl46L1eBCfN4QQufJYfkw"
}

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {HOST}...")
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    print("Connected!")
    
    # Save tokens
    token_json = json.dumps(tokens, indent=2)
    cmd = f"echo '{token_json}' > /root/valuescan/signal_monitor/valuescan_localstorage.json"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    stdout.channel.recv_exit_status()
    print("Saved tokens to VPS!")
    
    # Verify
    stdin, stdout, stderr = ssh.exec_command("cat /root/valuescan/signal_monitor/valuescan_localstorage.json")
    print("Verification:", stdout.read().decode()[:100])
    
    ssh.close()
    print("Done!")

if __name__ == "__main__":
    main()

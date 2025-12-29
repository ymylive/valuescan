#!/usr/bin/env python3
"""Check token status on VPS"""
import os
import paramiko

def main():
    password = os.environ.get('VALUESCAN_VPS_PASSWORD')
    if not password:
        print("Missing VALUESCAN_VPS_PASSWORD env var")
        return
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('82.158.88.34', username='root', password=password, timeout=30)
    
    commands = [
        "cat /root/valuescan/signal_monitor/valuescan_localstorage.json 2>/dev/null | python3.9 -c \"import sys,json; d=json.load(sys.stdin); t=d.get('account_token',''); print(f'Token exists: {bool(t)}'); print(f'Token length: {len(t)}'); import base64,time; parts=t.split('.'); payload=json.loads(base64.urlsafe_b64decode(parts[1]+'==')) if len(parts)>1 else {}; exp=payload.get('exp',0); now=int(time.time()); print(f'Expires: {exp}'); print(f'Now: {now}'); print(f'Valid: {exp>now}'); print(f'Remaining: {exp-now}s = {(exp-now)/3600:.1f}h')\"",
        "cat /root/valuescan/signal_monitor/valuescan_credentials.json 2>/dev/null || echo 'No credentials file'",
        "systemctl status valuescan-signal --no-pager | head -15",
    ]
    
    for cmd in commands:
        print(f"\n=== Command ===")
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
        print(stdout.read().decode())
        err = stderr.read().decode()
        if err:
            print(f"STDERR: {err}")
    
    ssh.close()

if __name__ == "__main__":
    main()

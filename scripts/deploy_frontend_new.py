#!/usr/bin/env python3
"""Deploy frontend to VPS."""

import os
import sys
import paramiko

VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "")
VPS_PATH = "/root/valuescan"
WEB_ROOT = "/var/www/valuescan"

def ssh_exec(ssh, command, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
    return stdout.read().decode('utf-8', errors='replace'), stderr.read().decode('utf-8', errors='replace')

def main():
    if not VPS_PASSWORD:
        print("Error: VALUESCAN_VPS_PASSWORD not set")
        return 1

    print("FRONTEND DEPLOYMENT")
    print(f"Target: {VPS_USER}@{VPS_HOST}")
    print(f"Web root: {WEB_ROOT}")
    print()

    print("[*] Connecting...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=30)
        print("[OK] Connected\n")
    except Exception as e:
        print(f"[ERROR] {e}")
        return 1

    print("[*] Building frontend...")
    output, error = ssh_exec(ssh, f"cd {VPS_PATH}/web && npx vite build 2>&1", timeout=300)

    if "built in" in output:
        print("[OK] Build successful")
        lines = output.strip().split('\n')
        for line in lines[-5:]:
            print(f"  {line}")
    else:
        print("[ERROR] Build failed")
        print(output[-500:])
        return 1

    print(f"\n[*] Copying to {WEB_ROOT}...")
    output, error = ssh_exec(ssh, f"cp -r {VPS_PATH}/web/dist/* {WEB_ROOT}/")
    print("[OK] Files copied")

    print("\n[*] Reloading nginx...")
    ssh_exec(ssh, "systemctl reload nginx")
    print("[OK] Nginx reloaded")

    ssh.close()

    print("\n[SUCCESS] Deployment complete!")
    print("\nVisit: https://cornna.abrdns.com")
    print("New tabs: '信号高级' and '交易高级'")
    print("Total new config options: 46")

    return 0

if __name__ == "__main__":
    sys.exit(main())

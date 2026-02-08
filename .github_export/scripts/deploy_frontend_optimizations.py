#!/usr/bin/env python3
"""
Deploy all frontend optimizations to VPS
"""

import paramiko
from scp import SCPClient
import sys

VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = "Qq159741"
VPS_PATH = "/root/valuescan"

# Files to deploy
FILES = [
    # Backend validation
    "api/config_validator.py",
    "api/server.py",

    # Frontend hooks and components
    "web/src/hooks/useDebounce.ts",
    "web/src/components/common/Toggle.tsx",
    "web/src/components/common/Skeleton.tsx",
    "web/src/components/valuescan/ConfigFieldGroup.tsx",
    "web/src/pages/SettingsPage.tsx",

    # Config files
    "web/tsconfig.json",
    "web/tsconfig.node.json",
    "web/tailwind.config.js",
]

def main():
    print("=" * 60)
    print("  Deploying Frontend Optimizations to VPS")
    print("=" * 60)
    print(f"\nVPS: {VPS_USER}@{VPS_HOST}")
    print(f"Path: {VPS_PATH}\n")

    try:
        # Connect to VPS
        print("Connecting to VPS...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, port=22, username=VPS_USER, password=VPS_PASSWORD)
        print("Connected!\n")

        # Upload files
        print("Uploading files...")
        with SCPClient(ssh.get_transport()) as scp:
            for f in FILES:
                try:
                    print(f"  {f}...")
                    scp.put(f, f"{VPS_PATH}/{f}")
                    print(f"    OK")
                except Exception as e:
                    print(f"    FAILED: {e}")

        # Rebuild frontend
        print("\nRebuilding frontend...")
        stdin, stdout, stderr = ssh.exec_command(
            f"cd {VPS_PATH}/web && npm run build 2>&1"
        )

        output = stdout.read().decode('utf-8', errors='ignore')
        exit_code = stdout.channel.recv_exit_status()

        if exit_code == 0:
            print("  Build successful!")
        else:
            print(f"  Build failed with exit code {exit_code}")
            # Show last 30 lines of output
            lines = output.split('\n')
            print("\nLast 30 lines of build output:")
            for line in lines[-30:]:
                if line.strip():
                    print(f"  {line}")

        # Restart services
        print("\nRestarting services...")
        ssh.exec_command("systemctl restart valuescan-api")
        print("  API restarted")
        ssh.exec_command("systemctl restart valuescan-signal")
        print("  Signal monitor restarted")

        # Check status
        print("\nChecking service status...")
        stdin, stdout, stderr = ssh.exec_command(
            "systemctl is-active valuescan-api valuescan-signal"
        )
        status = stdout.read().decode('utf-8', errors='ignore')
        print(f"  {status}")

        ssh.close()

        print("\n" + "=" * 60)
        print("  Deployment Complete!")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())

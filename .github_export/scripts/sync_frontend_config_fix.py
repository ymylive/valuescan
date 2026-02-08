#!/usr/bin/env python3
"""Sync frontend config fixes to VPS."""

import os
import sys
import paramiko
from pathlib import Path

VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "")
VPS_PATH = "/root/valuescan"

FILES_TO_SYNC = [
    "web/src/components/valuescan/AdvancedTraderConfigSection.tsx",
    "web/src/components/valuescan/AdvancedSignalMonitorConfigSection.tsx",
    "web/src/pages/SettingsPage.tsx",
    "FRONTEND_CONFIG_FIX_REPORT.md",
]

def ssh_exec(ssh, command, timeout=30):
    """Execute SSH command."""
    stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
    return stdout.read().decode('utf-8', errors='replace'), stderr.read().decode('utf-8', errors='replace')

def upload_file(sftp, local_path, remote_path):
    """Upload file via SFTP."""
    try:
        # Create remote directory
        remote_dir = str(Path(remote_path).parent)
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            # Create directory recursively
            dirs = []
            while remote_dir and remote_dir != '/':
                dirs.append(remote_dir)
                remote_dir = str(Path(remote_dir).parent)

            dirs.reverse()
            for d in dirs:
                try:
                    sftp.stat(d)
                except FileNotFoundError:
                    sftp.mkdir(d)

        # Upload file
        sftp.put(local_path, remote_path)
        return True
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

def main():
    if not VPS_PASSWORD:
        print("Error: VALUESCAN_VPS_PASSWORD not set")
        return 1

    print("=" * 80)
    print("FRONTEND CONFIG FIX - VPS SYNC")
    print("=" * 80)
    print(f"Target: {VPS_USER}@{VPS_HOST}:{VPS_PATH}")
    print()

    # Connect
    print("[*] Connecting to VPS...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=30)
        print("[+] Connected\n")
    except Exception as e:
        print(f"[ERROR] {e}")
        return 1

    sftp = ssh.open_sftp()

    # Sync files
    print("=" * 80)
    print("SYNCING FILES")
    print("=" * 80)

    success = 0
    skip = 0
    fail = 0

    for file in FILES_TO_SYNC:
        if not Path(file).exists():
            print(f"[SKIP] {file}")
            skip += 1
            continue

        remote_path = f"{VPS_PATH}/{file}"
        print(f"[SYNC] {file}...", end=" ")

        if upload_file(sftp, str(file), remote_path):
            print("[OK]")
            success += 1
        else:
            print("[FAIL]")
            fail += 1

    print()
    print("=" * 80)
    print("REBUILDING FRONTEND")
    print("=" * 80)

    print("[*] Building frontend...")
    output, error = ssh_exec(ssh, f"cd {VPS_PATH}/web && npm run build", timeout=180)

    if "built in" in output:
        print("[OK] Frontend built successfully")
    else:
        print("[WARN] Build may have failed")
        if error:
            print(f"Error: {error[:500]}")

    print()
    print("=" * 80)
    print("RESTARTING API SERVER")
    print("=" * 80)

    print("[*] Restarting API server...")
    ssh_exec(ssh, "systemctl restart valuescan-api")
    print("[OK] API server restarted")

    print()
    print("=" * 80)
    print("CHECKING SERVICE STATUS")
    print("=" * 80)

    output, _ = ssh_exec(ssh, "systemctl is-active valuescan-api")
    status = output.strip()
    if status == "active":
        print(f"[OK] API Server: {status}")
    else:
        print(f"[WARN] API Server: {status}")

    # Close
    sftp.close()
    ssh.close()

    print()
    print("=" * 80)
    print("SYNC SUMMARY")
    print("=" * 80)
    print(f"Success: {success}")
    print(f"Skipped: {skip}")
    print(f"Failed: {fail}")
    print()

    if fail > 0:
        print("[WARNING] Some files failed to sync")
        return 1
    else:
        print("[SUCCESS] All files synced successfully")
        print()
        print("Next steps:")
        print("1. Visit the web interface")
        print("2. Go to Settings > Config")
        print("3. Check the new '信号高级' and '交易高级' tabs")
        print("4. Verify all new configuration options are visible")
        return 0

if __name__ == "__main__":
    sys.exit(main())

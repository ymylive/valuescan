#!/usr/bin/env python3
"""Direct sync to VPS using paramiko."""

import os
import sys
import paramiko
from pathlib import Path, PurePosixPath

# VPS Configuration
VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "")
VPS_PATH = "/root/valuescan"

# Files to sync
FILES_TO_SYNC = [
    # Core Python modules
    "signal_monitor/ai_market_summary.py",
    "signal_monitor/polling_monitor.py",
    "signal_monitor/message_handler.py",
    "signal_monitor/telegram.py",
    "signal_monitor/logger.py",
    "signal_monitor/database.py",

    # AI modules
    "signal_monitor/ai_signal_analysis.py",
    "signal_monitor/ai_pattern_drawer.py",
    "signal_monitor/ai_market_analysis.py",
    "signal_monitor/auxiliary_line_drawer.py",
    "signal_monitor/chart_pro_v10.py",
    "signal_monitor/data_providers.py",

    # Config files
    "signal_monitor/ai_summary_config.json",
    "signal_monitor/ai_signal_config.json",
    "signal_monitor/ai_key_levels_config.json",
    "signal_monitor/ai_overlays_config.json",

    # API server
    "api/server.py",

    # Trading bot
    "binance_trader/trading_signal_processor.py",

    # Frontend config UI
    "web/src/App.tsx",
    "web/src/pages/SettingsPage.tsx",
    "web/src/components/valuescan/SignalMonitorConfigSection.tsx",

    # Scripts
    "scripts/test_complete_flow_simple.py",
]

def ssh_exec(ssh, command, timeout=30):
    """Execute SSH command."""
    stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
    return stdout.read().decode('utf-8', errors='replace'), stderr.read().decode('utf-8', errors='replace')

def upload_file(sftp, local_path, remote_path):
    """Upload file via SFTP."""
    try:
        # Create remote directory if needed
        remote_dir = str(PurePosixPath(remote_path).parent)
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            # Create directory recursively
            dirs = []
            while remote_dir and remote_dir != '/':
                dirs.append(remote_dir)
                remote_dir = str(PurePosixPath(remote_dir).parent)

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
        print(f"  [ERROR] Failed to upload {local_path}: {e}")
        return False

def main():
    if not VPS_PASSWORD:
        print("Error: VALUESCAN_VPS_PASSWORD not set")
        return 1

    print("=" * 80)
    print("VALUESCAN VPS SYNC TOOL")
    print("=" * 80)
    print(f"Target: {VPS_USER}@{VPS_HOST}:{VPS_PATH}")
    print()

    # Connect to VPS
    print("[*] Connecting to VPS...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=30)
        print("[+] Connected successfully\n")
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return 1

    # Open SFTP session
    sftp = ssh.open_sftp()

    # Sync files
    print("=" * 80)
    print("SYNCING FILES")
    print("=" * 80)

    success_count = 0
    skip_count = 0
    fail_count = 0

    for file in FILES_TO_SYNC:
        local_path = Path(file)
        if not local_path.exists():
            print(f"[SKIP] {file} (not found)")
            skip_count += 1
            continue

        remote_path = f"{VPS_PATH}/{file}"
        print(f"[SYNC] {file}...", end=" ")

        if upload_file(sftp, str(local_path), remote_path):
            print("[OK]")
            success_count += 1
        else:
            print("[FAIL]")
            fail_count += 1

    print()
    print("=" * 80)
    print("RESTARTING SERVICES")
    print("=" * 80)

    # Restart services
    services = [
        ("valuescan-signal", "Signal Monitor"),
        ("valuescan-api", "API Server"),
    ]

    for service, name in services:
        print(f"[*] Restarting {name}...")
        output, error = ssh_exec(ssh, f"systemctl restart {service}")
        if error:
            print(f"  [WARN] {error.strip()}")
        else:
            print(f"  [OK] {name} restarted")

    print()
    print("=" * 80)
    print("CHECKING SERVICE STATUS")
    print("=" * 80)

    for service, name in services:
        output, _ = ssh_exec(ssh, f"systemctl is-active {service}")
        status = output.strip()
        if status == "active":
            print(f"[OK] {name}: {status}")
        else:
            print(f"[WARN] {name}: {status}")

    # Close connections
    sftp.close()
    ssh.close()

    print()
    print("=" * 80)
    print("SYNC SUMMARY")
    print("=" * 80)
    print(f"Success: {success_count}")
    print(f"Skipped: {skip_count}")
    print(f"Failed: {fail_count}")
    print()

    if fail_count > 0:
        print("[WARNING] Some files failed to sync")
        return 1
    else:
        print("[SUCCESS] All files synced successfully")
        return 0

if __name__ == "__main__":
    sys.exit(main())

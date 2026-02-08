#!/usr/bin/env python3
"""
Quick VPS sync tool - syncs valuescan updates to VPS
"""

import os
import sys
import subprocess
from pathlib import Path

# VPS Configuration
VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PORT = "22"
VPS_PATH = "/root/valuescan"
VPS_PASSWORD = "Qq159741"

# Files to sync
FILES_TO_SYNC = [
    # AI Config files
    "signal_monitor/ai_summary_config.json",
    "signal_monitor/ai_market_summary_config.json",
    "signal_monitor/ai_key_levels_config.json",
    "signal_monitor/ai_overlays_config.json",

    # Python code
    "signal_monitor/ai_market_summary.py",
    "signal_monitor/chart_pro_v10.py",
    "signal_monitor/ai_signal_analysis.py",
    "signal_monitor/ai_key_levels_config.py",

    # Frontend files
    "web/src/components/valuescan/SignalMonitorConfigSection.tsx",
    "web/src/components/valuescan/TraderConfigSection.tsx",
    "web/src/components/valuescan/CopyTradeConfigSection.tsx",
    "web/src/components/valuescan/AdvancedSignalMonitorConfigSection.tsx",
    "web/src/components/valuescan/AdvancedTraderConfigSection.tsx",
    "web/src/types/config.ts",
    "web/src/utils/configValidation.ts",
]

def run_scp(local_file, remote_path):
    """Use scp to copy file to VPS"""
    cmd = [
        "scp",
        "-P", VPS_PORT,
        local_file,
        f"{VPS_USER}@{VPS_HOST}:{remote_path}"
    ]

    print(f"  Copying {local_file}...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"    ERROR: {result.stderr}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"    ERROR: Timeout")
        return False
    except Exception as e:
        print(f"    ERROR: {e}")
        return False

def main():
    """Main sync function"""
    print("=" * 60)
    print("  ValueScan VPS Sync Tool")
    print("=" * 60)
    print(f"\nVPS: {VPS_USER}@{VPS_HOST}:{VPS_PORT}")
    print(f"Path: {VPS_PATH}\n")

    # Confirm
    response = input("Continue sync? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled")
        return 0

    success_count = 0
    fail_count = 0

    # Sync files
    print("\n[1/3] Syncing AI config files...")
    for file in FILES_TO_SYNC[:4]:
        if not Path(file).exists():
            print(f"  SKIP: {file} (not found)")
            continue

        remote_path = f"{VPS_PATH}/{file}"
        if run_scp(file, remote_path):
            success_count += 1
        else:
            fail_count += 1

    print("\n[2/3] Syncing Python code...")
    for file in FILES_TO_SYNC[4:8]:
        if not Path(file).exists():
            print(f"  SKIP: {file} (not found)")
            continue

        remote_path = f"{VPS_PATH}/{file}"
        if run_scp(file, remote_path):
            success_count += 1
        else:
            fail_count += 1

    print("\n[3/3] Syncing frontend files...")
    for file in FILES_TO_SYNC[8:]:
        if not Path(file).exists():
            print(f"  SKIP: {file} (not found)")
            continue

        remote_path = f"{VPS_PATH}/{file}"
        if run_scp(file, remote_path):
            success_count += 1
        else:
            fail_count += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"  Sync Complete")
    print("=" * 60)
    print(f"\nSuccess: {success_count} files")
    print(f"Failed: {fail_count} files")

    if fail_count > 0:
        print("\nNote: Some files failed to sync. Please check:")
        print("1. SSH connection to VPS")
        print("2. File permissions")
        print("3. Network connectivity")
        return 1

    print("\nNext steps:")
    print("1. Rebuild frontend: ssh root@82.158.88.34 'cd /root/valuescan/web && npm run build'")
    print("2. Restart services: ssh root@82.158.88.34 'systemctl restart valuescan-api valuescan-signal'")

    return 0

if __name__ == '__main__':
    sys.exit(main())

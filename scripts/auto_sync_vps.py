#!/usr/bin/env python3
"""
Auto sync to VPS without password prompt
"""

import os
import sys
import subprocess
from pathlib import Path

# VPS Configuration
VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = "Qq159741"
VPS_PORT = "22"
VPS_PATH = "/root/valuescan"

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

def run_scp_with_password(local_file, remote_path):
    """Use plink/pscp (PuTTY) to copy file with password"""
    # Try pscp (PuTTY SCP) first
    cmd = [
        "pscp",
        "-P", VPS_PORT,
        "-pw", VPS_PASSWORD,
        "-batch",
        local_file,
        f"{VPS_USER}@{VPS_HOST}:{remote_path}"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return True

        # If pscp not found, try scp with expect
        print(f"    pscp failed, trying alternative method...")
        return run_scp_alternative(local_file, remote_path)
    except FileNotFoundError:
        # pscp not installed, try alternative
        return run_scp_alternative(local_file, remote_path)
    except Exception as e:
        print(f"    ERROR: {e}")
        return False

def run_scp_alternative(local_file, remote_path):
    """Alternative method using pexpect or plain scp"""
    try:
        import pexpect
        cmd = f"scp -P {VPS_PORT} {local_file} {VPS_USER}@{VPS_HOST}:{remote_path}"
        child = pexpect.spawn(cmd, timeout=30)
        child.expect("password:")
        child.sendline(VPS_PASSWORD)
        child.expect(pexpect.EOF)
        child.close()
        return child.exitstatus == 0
    except ImportError:
        # pexpect not available, use paramiko
        return run_scp_paramiko(local_file, remote_path)
    except Exception as e:
        print(f"    ERROR: {e}")
        return False

def run_scp_paramiko(local_file, remote_path):
    """Use paramiko for SCP"""
    try:
        import paramiko
        from scp import SCPClient

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, port=int(VPS_PORT), username=VPS_USER, password=VPS_PASSWORD)

        with SCPClient(ssh.get_transport()) as scp:
            scp.put(local_file, remote_path)

        ssh.close()
        return True
    except ImportError:
        print(f"    ERROR: No suitable SCP method available")
        print(f"    Please install: pip install paramiko scp")
        return False
    except Exception as e:
        print(f"    ERROR: {e}")
        return False

def main():
    """Main sync function"""
    print("=" * 60)
    print("  ValueScan VPS Auto Sync")
    print("=" * 60)
    print(f"\nVPS: {VPS_USER}@{VPS_HOST}:{VPS_PORT}")
    print(f"Path: {VPS_PATH}\n")

    success_count = 0
    fail_count = 0
    skip_count = 0

    # Sync files
    print("[1/3] Syncing AI config files...")
    for file in FILES_TO_SYNC[:4]:
        if not Path(file).exists():
            print(f"  SKIP: {file}")
            skip_count += 1
            continue

        print(f"  Copying {file}...")
        remote_path = f"{VPS_PATH}/{file}"
        if run_scp_with_password(file, remote_path):
            print(f"    OK")
            success_count += 1
        else:
            print(f"    FAILED")
            fail_count += 1

    print("\n[2/3] Syncing Python code...")
    for file in FILES_TO_SYNC[4:8]:
        if not Path(file).exists():
            print(f"  SKIP: {file}")
            skip_count += 1
            continue

        print(f"  Copying {file}...")
        remote_path = f"{VPS_PATH}/{file}"
        if run_scp_with_password(file, remote_path):
            print(f"    OK")
            success_count += 1
        else:
            print(f"    FAILED")
            fail_count += 1

    print("\n[3/3] Syncing frontend files...")
    for file in FILES_TO_SYNC[8:]:
        if not Path(file).exists():
            print(f"  SKIP: {file}")
            skip_count += 1
            continue

        print(f"  Copying {file}...")
        remote_path = f"{VPS_PATH}/{file}"
        if run_scp_with_password(file, remote_path):
            print(f"    OK")
            success_count += 1
        else:
            print(f"    FAILED")
            fail_count += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"  Sync Complete")
    print("=" * 60)
    print(f"\nSuccess: {success_count} files")
    print(f"Failed: {fail_count} files")
    print(f"Skipped: {skip_count} files")

    if fail_count > 0:
        return 1

    print("\nSync successful!")
    return 0

if __name__ == '__main__':
    sys.exit(main())

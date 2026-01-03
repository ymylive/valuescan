#!/usr/bin/env python3
"""Test complete information flow from signal monitoring to trading execution."""

import os
import sys
import paramiko
import json
from datetime import datetime

def ssh_exec(ssh, command):
    """Execute SSH command and return output."""
    stdin, stdout, stderr = ssh.exec_command(command, timeout=30)
    return stdout.read().decode('utf-8', errors='replace'), stderr.read().decode('utf-8', errors='replace')

def main():
    host = "82.158.88.34"
    user = "root"
    password = os.environ.get("VALUESCAN_VPS_PASSWORD", "")

    if not password:
        print("Error: VALUESCAN_VPS_PASSWORD not set")
        return 1

    print("=" * 80)
    print("VALUESCAN COMPLETE FLOW TEST REPORT")
    print("=" * 80)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"VPS Host: {host}")
    print()

    # Connect to VPS
    print("[*] Connecting to VPS...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(host, username=user, password=password, timeout=30)
        print("[+] Connected successfully\n")
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return 1

    # 1. Token Refresher Status
    print("=" * 80)
    print("1. TOKEN REFRESHER STATUS")
    print("=" * 80)

    output, _ = ssh_exec(ssh, "systemctl is-active valuescan-token-refresher")
    status = output.strip()
    print(f"Service Status: {status}")

    if status == "active":
        print("[OK] Token refresher is running")
    else:
        print("[WARNING] Token refresher is not active")

    # Check token file
    output, _ = ssh_exec(ssh, "cat /root/valuescan/signal_monitor/valuescan_localstorage.json")
    try:
        token_data = json.loads(output)
        token_length = len(token_data.get('account_token', ''))
        print(f"Token Length: {token_length} characters")
        if token_length > 0:
            print("[OK] Token exists and is valid")
        else:
            print("[ERROR] Token is missing or empty")
    except Exception as e:
        print(f"[ERROR] Failed to parse token file: {e}")

    print()

    # 2. Signal Monitor Status
    print("=" * 80)
    print("2. SIGNAL MONITOR STATUS")
    print("=" * 80)

    output, _ = ssh_exec(ssh, "systemctl is-active valuescan-signal")
    status = output.strip()
    print(f"Service Status: {status}")

    if status == "active":
        print("[OK] Signal monitor is running")
    else:
        print("[WARNING] Signal monitor is not active")

    # Check process
    output, _ = ssh_exec(ssh, "ps aux | grep polling_monitor | grep -v grep | wc -l")
    process_count = output.strip()
    print(f"Process Count: {process_count}")

    if int(process_count) > 0:
        print("[OK] Polling monitor process is running")
    else:
        print("[WARNING] Polling monitor process not found")

    print()

    # 3. API Connectivity
    print("=" * 80)
    print("3. API CONNECTIVITY")
    print("=" * 80)

    # Test ValueScan API
    output, _ = ssh_exec(ssh, "curl -s -o /dev/null -w '%{http_code}' https://api.valuescan.io/api/v1/message/aiMessagePage")
    http_code = output.strip()
    print(f"ValueScan API HTTP Code: {http_code}")

    if http_code in ["200", "201", "400", "401", "500"]:
        print("[OK] API is reachable")
    else:
        print("[WARNING] API may not be reachable")

    print()

    # 4. IPC Connection
    print("=" * 80)
    print("4. IPC CONNECTION (Signal Forwarding)")
    print("=" * 80)

    output, _ = ssh_exec(ssh, "netstat -an | grep 8765 | wc -l")
    connection_count = output.strip()
    print(f"Port 8765 Connections: {connection_count}")

    if int(connection_count) > 0:
        print("[OK] IPC socket is active")
    else:
        print("[INFO] No active IPC connections (normal if trader is not listening)")

    print()

    # 5. Trading Bot Status
    print("=" * 80)
    print("5. TRADING BOT STATUS")
    print("=" * 80)

    output, _ = ssh_exec(ssh, "systemctl is-active valuescan-trader")
    status = output.strip()
    print(f"Service Status: {status}")

    if status == "active":
        print("[OK] Trading bot is running")
    else:
        print("[INFO] Trading bot is not active (may be intentional)")

    # Check process
    output, _ = ssh_exec(ssh, "ps aux | grep futures_main | grep -v grep | wc -l")
    process_count = output.strip()
    print(f"Process Count: {process_count}")

    print()

    # 6. Telegram Configuration
    print("=" * 80)
    print("6. TELEGRAM NOTIFICATION")
    print("=" * 80)

    output, _ = ssh_exec(ssh, "cat /root/valuescan/signal_monitor/config.py | grep ENABLE_TELEGRAM")
    telegram_enabled = "True" in output
    print(f"Telegram Enabled: {telegram_enabled}")

    if telegram_enabled:
        print("[OK] Telegram notifications are enabled")
    else:
        print("[INFO] Telegram notifications are disabled")

    output, _ = ssh_exec(ssh, "cat /root/valuescan/signal_monitor/config.py | grep TELEGRAM_BOT_TOKEN | head -1")
    has_token = "TELEGRAM_BOT_TOKEN" in output and len(output.strip()) > 30
    print(f"Bot Token Configured: {has_token}")

    print()

    # 7. Database Status
    print("=" * 80)
    print("7. DATABASE STATUS")
    print("=" * 80)

    output, _ = ssh_exec(ssh, "ls -lh /root/valuescan/signal_monitor/valuescan.db 2>&1")
    if "No such file" in output:
        print("[WARNING] Database file not found")
    else:
        print("[OK] Database file exists")
        # Get file size
        parts = output.split()
        if len(parts) >= 5:
            print(f"Database Size: {parts[4]}")

    print()

    # 8. Recent Activity
    print("=" * 80)
    print("8. RECENT ACTIVITY (Last 5 minutes)")
    print("=" * 80)

    output, _ = ssh_exec(ssh, "journalctl -u valuescan-signal --since '5 minutes ago' --no-pager | wc -l")
    log_lines = output.strip()
    print(f"Signal Monitor Log Lines: {log_lines}")

    if int(log_lines) > 0:
        print("[OK] Signal monitor is actively logging")
    else:
        print("[WARNING] No recent logs from signal monitor")

    print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("""
Information Flow:
1. Token Refresher -> Maintains fresh authentication token
2. Signal Monitor -> Polls ValueScan API every 10 seconds
3. Message Handler -> Processes and deduplicates signals
4. Telegram Bot -> Sends notifications to Telegram channel
5. IPC Socket -> Forwards signals to trading bot (if enabled)
6. Trading Bot -> Executes trades on Binance (if enabled)

Current Status:
- Token Refresher: Check status above
- Signal Monitor: Check status above
- API Connectivity: Check status above
- Telegram: Check configuration above
- Trading Bot: Check status above

Next Steps:
- If any component shows [ERROR], investigate the logs
- If [WARNING], review configuration
- Monitor logs: journalctl -u valuescan-signal -f
- Check Telegram channel for notifications
    """)

    ssh.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Verify deployment on VPS."""

import os
import paramiko

DEFAULT_HOST = "82.158.88.34"
DEFAULT_USER = "root"

def _exec(ssh, cmd, timeout=30):
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="ignore")
        err = stderr.read().decode("utf-8", errors="ignore")
        return (out + ("\n" + err if err else "")).strip()
    except Exception as exc:
        return f"[error] {exc}"

def main():
    host = os.environ.get("VALUESCAN_VPS_HOST", DEFAULT_HOST)
    user = os.environ.get("VALUESCAN_VPS_USER", DEFAULT_USER)
    password = os.environ.get("VALUESCAN_VPS_PASSWORD", "")
    
    if not password:
        raise SystemExit("VALUESCAN_VPS_PASSWORD required")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"Connecting to {user}@{host}...")
    ssh.connect(hostname=host, username=user, password=password, timeout=30)
    
    print("\n=== Service Status ===")
    print(_exec(ssh, "systemctl is-active valuescan-api valuescan-trader valuescan-signal --no-pager 2>/dev/null || true"))
    
    print("\n=== API Health Check ===")
    print(_exec(ssh, "curl -s --max-time 5 http://127.0.0.1:5000/api/valuescan/status | head -c 500"))
    
    print("\n=== Major Coin Config in config.example.py ===")
    print(_exec(ssh, "grep -E 'MAJOR_COIN_LEVERAGE|MAJOR_COIN_MAX_POSITION_PERCENT' /root/valuescan/binance_trader/config.example.py | head -10"))
    
    print("\n=== Risk Manager Check ===")
    print(_exec(ssh, "grep -E 'major_coin_max_position_percent|major_coins' /root/valuescan/binance_trader/risk_manager.py | head -10"))
    
    print("\n=== Futures Main Check ===")
    print(_exec(ssh, "grep -E '_get_leverage|MAJOR_COIN_LEVERAGE' /root/valuescan/binance_trader/futures_main.py | head -10"))
    
    ssh.close()
    print("\nVerification complete!")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
部署优化后的异动检测系统到 VPS
"""

import os
import sys
import paramiko

VPS_HOST = "43.133.12.98"
VPS_USER = "root"
VPS_PASS = "Qq159741"

LOCAL_PROJECT = r"E:\project\valuescan"
REMOTE_PROJECT = "/root/valuescan"

def main():
    print("=" * 50)
    print("Deploying Optimized Anomaly Detector to VPS")
    print("=" * 50)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS, timeout=15)
    sftp = client.open_sftp()

    # 需要上传的文件
    files = [
        "signal_monitor/ccxt_data.py",
        "signal_monitor/ai_signal_analysis.py",
        "signal_monitor/market_alert.py",
        "signal_monitor/anomaly_detector/config.py",
        "signal_monitor/anomaly_detector/detector.py",
        "signal_monitor/anomaly_detector/data/__init__.py",
        "signal_monitor/anomaly_detector/data/provider.py",
        "signal_monitor/anomaly_detector/features/__init__.py",
        "signal_monitor/anomaly_detector/features/engine.py",
        "signal_monitor/anomaly_detector/features/volume_price.py",
        "signal_monitor/anomaly_detector/features/derivatives.py",
        "signal_monitor/anomaly_detector/features/correlation.py",
        "signal_monitor/anomaly_detector/features/dynamic_threshold.py",
        "signal_monitor/anomaly_detector/features/orderbook.py",
        "signal_monitor/anomaly_detector/features/scorer.py",
    ]

    print("\n[1/3] Uploading files...")
    for rel_path in files:
        local_path = os.path.join(LOCAL_PROJECT, rel_path)
        remote_path = f"{REMOTE_PROJECT}/{rel_path}"

        if os.path.exists(local_path):
            print(f"  Uploading: {rel_path}")
            sftp.put(local_path, remote_path)
        else:
            print(f"  [SKIP] {rel_path} not found")

    sftp.close()

    print("\n[2/3] Restarting service...")
    stdin, stdout, stderr = client.exec_command("systemctl restart valuescan-monitor")
    stdout.read()

    import time
    time.sleep(3)

    print("\n[3/3] Checking service status...")
    stdin, stdout, stderr = client.exec_command("systemctl status valuescan-monitor --no-pager | head -15")
    print(stdout.read().decode())

    # 检查日志
    print("\n=== Recent Logs ===")
    stdin, stdout, stderr = client.exec_command("journalctl -u valuescan-monitor -n 10 --no-pager 2>&1")
    logs = stdout.read().decode()
    for line in logs.split('\n')[-10:]:
        if line.strip():
            print(line[-120:])

    client.close()

    print("\n" + "=" * 50)
    print("Deployment complete!")
    print("=" * 50)

if __name__ == "__main__":
    main()

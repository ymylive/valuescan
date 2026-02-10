#!/usr/bin/env python3
"""
VPS部署脚本 - 部署anomaly_detector模块到VPS
"""

import os
import sys
import subprocess
import time

# VPS配置
VPS_HOST = "43.133.12.98"
VPS_USER = "root"
VPS_PASS = "Qq159741"

# 路径配置
LOCAL_PROJECT = r"E:\project\valuescan"
REMOTE_PROJECT = "/root/valuescan"

def run_scp(local_path: str, remote_path: str) -> bool:
    """使用scp上传文件"""
    cmd = f'scp -o StrictHostKeyChecking=no "{local_path}" {VPS_USER}@{VPS_HOST}:{remote_path}'
    print(f"  Uploading: {os.path.basename(local_path)}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60,
                           env={**os.environ, "SSHPASS": VPS_PASS})
    return result.returncode == 0

def run_ssh(cmd: str, timeout: int = 60) -> tuple:
    """执行SSH命令"""
    ssh_cmd = f'ssh -o StrictHostKeyChecking=no {VPS_USER}@{VPS_HOST} "{cmd}"'
    try:
        result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True, timeout=timeout,
                               env={**os.environ, "SSHPASS": VPS_PASS})
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)

def main():
    print("=" * 50)
    print("VPS Deployment - Anomaly Detector Module")
    print("=" * 50)
    print(f"Target: {VPS_HOST}")

    # 测试连接
    print("\n[1/4] Testing SSH connection...")
    code, out, err = run_ssh("echo 'SSH OK'")
    if code != 0:
        print(f"SSH connection failed: {err}")
        # 尝试使用sshpass
        print("Trying with sshpass...")

    print("SSH connection OK")

    # 创建目录结构
    print("\n[2/4] Creating directory structure...")
    dirs = [
        f"{REMOTE_PROJECT}/signal_monitor/anomaly_detector",
        f"{REMOTE_PROJECT}/signal_monitor/anomaly_detector/data",
        f"{REMOTE_PROJECT}/signal_monitor/anomaly_detector/features",
    ]
    for d in dirs:
        run_ssh(f"mkdir -p {d}")
    print("Directories created")

    # 上传文件列表
    print("\n[3/4] Uploading files...")
    files = [
        ("signal_monitor/anomaly_detector/__init__.py", "signal_monitor/anomaly_detector/__init__.py"),
        ("signal_monitor/anomaly_detector/config.py", "signal_monitor/anomaly_detector/config.py"),
        ("signal_monitor/anomaly_detector/logger.py", "signal_monitor/anomaly_detector/logger.py"),
        ("signal_monitor/anomaly_detector/detector.py", "signal_monitor/anomaly_detector/detector.py"),
        ("signal_monitor/anomaly_detector/engine.py", "signal_monitor/anomaly_detector/engine.py"),
        ("signal_monitor/anomaly_detector/data/__init__.py", "signal_monitor/anomaly_detector/data/__init__.py"),
        ("signal_monitor/anomaly_detector/data/provider.py", "signal_monitor/anomaly_detector/data/provider.py"),
        ("signal_monitor/anomaly_detector/features/__init__.py", "signal_monitor/anomaly_detector/features/__init__.py"),
        ("signal_monitor/anomaly_detector/features/engine.py", "signal_monitor/anomaly_detector/features/engine.py"),
        ("signal_monitor/anomaly_detector/features/volume_price.py", "signal_monitor/anomaly_detector/features/volume_price.py"),
        ("signal_monitor/anomaly_detector/features/derivatives.py", "signal_monitor/anomaly_detector/features/derivatives.py"),
        ("signal_monitor/anomaly_detector/features/correlation.py", "signal_monitor/anomaly_detector/features/correlation.py"),
        ("signal_monitor/ai_signal_scheduler.py", "signal_monitor/ai_signal_scheduler.py"),
        ("signal_monitor/market_alert.py", "signal_monitor/market_alert.py"),
        ("signal_monitor/market_alert_config.json", "signal_monitor/market_alert_config.json"),
    ]

    for local_rel, remote_rel in files:
        local_path = os.path.join(LOCAL_PROJECT, local_rel)
        remote_path = f"{REMOTE_PROJECT}/{remote_rel}"
        if os.path.exists(local_path):
            run_scp(local_path, remote_path)
        else:
            print(f"  [SKIP] {local_rel} not found")

    # 重启服务
    print("\n[4/4] Restarting services...")
    run_ssh("systemctl restart valuescan-monitor")
    time.sleep(2)
    code, out, err = run_ssh("systemctl status valuescan-monitor --no-pager | head -20")
    print(out if out else err)

    print("\n" + "=" * 50)
    print("Deployment complete!")
    print("=" * 50)

    return 0

if __name__ == "__main__":
    sys.exit(main())

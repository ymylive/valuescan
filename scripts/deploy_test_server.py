#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署到测试服务器 43.133.12.98
"""
import os
import sys
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("错误: 未安装 paramiko 库")
    print("请运行: pip install paramiko")
    sys.exit(1)

# 测试服务器配置
VPS_HOST = "43.133.12.98"
VPS_USER = "root"
VPS_PORT = 22
VPS_PASSWORD = "Qq159741"
VPS_PATH = "/root/valuescan"

LOCAL_ROOT = Path(__file__).resolve().parent.parent

def run_ssh_command(ssh, command, show_output=True):
    """执行 SSH 命令"""
    try:
        stdin, stdout, stderr = ssh.exec_command(command, timeout=300)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode("utf-8", errors="ignore")
        error = stderr.read().decode("utf-8", errors="ignore")
        if show_output:
            if output:
                print(output)
            if error and "WARNING" not in error:
                print(error, file=sys.stderr)
        return exit_status == 0
    except Exception as e:
        print(f"执行失败: {e}")
        return False

def main():
    print(f"连接到测试服务器 {VPS_HOST}...")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(VPS_HOST, port=VPS_PORT, username=VPS_USER, password=VPS_PASSWORD, timeout=30)
        print("[OK] SSH 连接成功")
    except Exception as e:
        print(f"[FAIL] SSH 连接失败: {e}")
        return False

    # 1. 检查目录是否存在
    print("\n[1/5] 检查远程目录...")
    run_ssh_command(ssh, f"ls -la {VPS_PATH}")

    # 2. 拉取最新代码
    print("\n[2/5] 拉取最新代码...")
    run_ssh_command(ssh, f"cd {VPS_PATH} && git fetch origin && git reset --hard origin/master")

    # 3. 上传本地修改的文件
    print("\n[3/5] 上传本地修改的文件...")
    sftp = ssh.open_sftp()

    files_to_upload = [
        "signal_monitor/ai_signal_analysis.py",
        "signal_monitor/ai_signal_scheduler.py",
        "signal_monitor/ai_market_analysis.py",
        "signal_monitor/ai_market_summary.py",
        "signal_monitor/macro_event_monitor.py",
        "signal_monitor/valuescan_api.py",
    ]

    for file_path in files_to_upload:
        local_path = LOCAL_ROOT / file_path
        remote_path = f"{VPS_PATH}/{file_path}"
        if local_path.exists():
            try:
                # 确保远程目录存在
                remote_dir = os.path.dirname(remote_path)
                run_ssh_command(ssh, f"mkdir -p {remote_dir}", show_output=False)
                sftp.put(str(local_path), remote_path)
                print(f"  [OK] {file_path}")
            except Exception as e:
                print(f"  [FAIL] {file_path}: {e}")
        else:
            print(f"  [SKIP] {file_path} (本地不存在)")

    sftp.close()

    # 4. 重启信号监控服务
    print("\n[4/5] 重启信号监控服务...")
    run_ssh_command(ssh, "systemctl restart valuescan-monitor || systemctl restart valuescan-signal || echo 'Service restart skipped'")

    # 5. 检查服务状态
    print("\n[5/5] 检查服务状态...")
    run_ssh_command(ssh, "systemctl status valuescan-monitor --no-pager -l || systemctl status valuescan-signal --no-pager -l || echo 'Status check skipped'")

    ssh.close()
    print("\n[DONE] 部署完成!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

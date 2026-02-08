#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署异步图表+AI主力位+AI简评修复
"""
import os
import sys
import tempfile
import tarfile
import time
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("安装 paramiko...")
    os.system("pip install paramiko -q")
    import paramiko

# VPS 配置
VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = "Qq159741"
VPS_PORT = 22
VPS_PATH = "/root/valuescan"

LOCAL_ROOT = Path(__file__).resolve().parent.parent

# 需要部署的文件
DEPLOY_FILES = [
    "signal_monitor/telegram.py",
    "signal_monitor/message_handler.py",
    "signal_monitor/ai_signal_config.json",
    "signal_monitor/ai_key_levels_config.json",
    "signal_monitor/ai_overlays_config.json",
    "signal_monitor/ai_market_summary_config.json",
]

def run_ssh_command(ssh, command, show_output=True):
    """执行 SSH 命令"""
    try:
        stdin, stdout, stderr = ssh.exec_command(command, timeout=120)
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

def upload_files(ssh):
    """上传修改的文件"""
    temp_dir = Path(tempfile.mkdtemp(prefix="valuescan_fix_"))
    archive_path = temp_dir / "fix_upload.tar.gz"
    
    print("打包文件...")
    with tarfile.open(archive_path, "w:gz") as tar:
        for file_path in DEPLOY_FILES:
            abs_path = LOCAL_ROOT / file_path
            if abs_path.exists():
                tar.add(abs_path, arcname=file_path)
                print(f"  + {file_path}")
            else:
                print(f"  ! 文件不存在: {file_path}")
    
    print("\n上传到VPS...")
    remote_archive = f"/tmp/fix_upload_{int(time.time())}.tar.gz"
    sftp = ssh.open_sftp()
    try:
        sftp.put(str(archive_path), remote_archive)
    finally:
        sftp.close()
    
    print("解压文件...")
    if not run_ssh_command(ssh, f"tar -xzf {remote_archive} -C {VPS_PATH}"):
        return False
    run_ssh_command(ssh, f"rm -f {remote_archive}")
    
    try:
        archive_path.unlink(missing_ok=True)
    except:
        pass
    
    return True

def main():
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

    print("=" * 50)
    print("  部署异步图表+AI主力位+AI简评修复")
    print("=" * 50)
    print(f"\nVPS: {VPS_USER}@{VPS_HOST}")
    print(f"路径: {VPS_PATH}\n")

    print("连接VPS...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(
            hostname=VPS_HOST,
            port=VPS_PORT,
            username=VPS_USER,
            password=VPS_PASSWORD,
            timeout=30
        )
        print("✓ SSH连接成功\n")
    except Exception as e:
        print(f"连接失败: {e}")
        sys.exit(1)

    steps = [
        ("上传修复文件", lambda: upload_files(ssh)),
        ("重启信号监控", lambda: run_ssh_command(ssh, "systemctl restart valuescan-signal")),
    ]

    success = True
    for i, (desc, action) in enumerate(steps, 1):
        print(f"[{i}/{len(steps)}] {desc}...")
        if not action():
            print(f"✗ {desc}失败")
            success = False
            break
        print(f"✓ {desc}完成\n")

    # 检查服务状态
    if success:
        print("检查服务状态...")
        run_ssh_command(ssh, "systemctl status valuescan-signal --no-pager -l | head -20")

    ssh.close()

    if success:
        print("\n" + "=" * 50)
        print("  ✓ 部署完成!")
        print("=" * 50)
        print("\n已部署文件:")
        for f in DEPLOY_FILES:
            print(f"  - {f}")
        print("\n已重启: valuescan-signal")
    else:
        print("\n部署失败")
        sys.exit(1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署AI信号分析修复到VPS
"""
import paramiko
import os
import sys
from pathlib import Path

# VPS配置
VPS_HOST = "valuescan.io"
VPS_USER = "root"
VPS_PASSWORD = "Qq159741"
VPS_PROJECT_PATH = "/root/valuescan"

# 需要上传的文件
FILES_TO_UPLOAD = [
    ("signal_monitor/ai_signal_analysis.py", "signal_monitor/ai_signal_analysis.py"),
]


def deploy_files():
    """上传文件并重启服务"""
    print("="*60)
    print("部署AI信号分析修复到VPS")
    print("="*60 + "\n")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"连接到 {VPS_HOST}...")
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD,
                   look_for_keys=False, allow_agent=False)
        sftp = ssh.open_sftp()

        print(f"✅ 已连接到 {VPS_HOST}\n")

        for local_path, remote_path in FILES_TO_UPLOAD:
            local_file = Path(local_path)
            remote_file = f"{VPS_PROJECT_PATH}/{remote_path}"

            if not local_file.exists():
                print(f"❌ 文件不存在: {local_path}")
                continue

            # 确保远程目录存在
            remote_dir = os.path.dirname(remote_file)
            try:
                sftp.stat(remote_dir)
            except:
                stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}")
                stdout.channel.recv_exit_status()

            print(f"上传: {local_path} -> {remote_file}")
            sftp.put(str(local_file), remote_file)
            print(f"✅ 上传完成\n")

        sftp.close()

        print("重启 valuescan-signal 服务...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart valuescan-signal")
        exit_status = stdout.channel.recv_exit_status()

        if exit_status == 0:
            print("✅ 服务已重启\n")
        else:
            print(f"⚠️  服务重启返回状态: {exit_status}\n")

        print("检查服务状态...")
        stdin, stdout, stderr = ssh.exec_command("systemctl status valuescan-signal --no-pager -l")
        status_output = stdout.read().decode('utf-8')
        print(status_output)

        ssh.close()
        print("\n" + "="*60)
        print("✅ 部署完成！")
        print("="*60)
        return True

    except Exception as e:
        print(f"❌ 部署失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = deploy_files()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署数据提供者模块到VPS
"""
import paramiko
import os
from pathlib import Path

# VPS配置
VPS_HOST = "8.138.115.109"
VPS_USER = "root"
VPS_PASSWORD = "Qq159741"
VPS_PROJECT_PATH = "/root/valuescan"

# 需要上传的文件
FILES_TO_UPLOAD = [
    ("signal_monitor/data_providers.py", "signal_monitor/data_providers.py"),
    ("signal_monitor/chart_pro_v10.py", "signal_monitor/chart_pro_v10.py"),
    ("docs/CRYPTO_DATA_APIS.md", "docs/CRYPTO_DATA_APIS.md"),
    ("docs/API_ACCESS_GUIDE.md", "docs/API_ACCESS_GUIDE.md"),
    ("test_data_providers.py", "test_data_providers.py"),
]


def upload_files():
    """上传文件到VPS"""
    print("连接到VPS...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD)
        sftp = ssh.open_sftp()

        print(f"✅ 已连接到 {VPS_HOST}\n")

        for local_path, remote_path in FILES_TO_UPLOAD:
            local_file = Path(local_path)
            remote_file = f"{VPS_PROJECT_PATH}/{remote_path}"

            if not local_file.exists():
                print(f"⚠️  跳过: {local_path} (文件不存在)")
                continue

            # 确保远程目录存在
            remote_dir = os.path.dirname(remote_file)
            try:
                sftp.stat(remote_dir)
            except:
                stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}")
                stdout.channel.recv_exit_status()

            # 上传文件
            print(f"上传: {local_path} -> {remote_path}")
            sftp.put(str(local_file), remote_file)
            print(f"✅ 完成\n")

        sftp.close()

        # 重启signal monitor服务
        print("重启signal monitor服务...")
        stdin, stdout, stderr = ssh.exec_command(
            "systemctl restart valuescan-signal"
        )
        stdout.channel.recv_exit_status()
        print("✅ 服务已重启\n")

        ssh.close()
        print("✅ 部署完成！")

    except Exception as e:
        print(f"❌ 部署失败: {e}")
        raise


if __name__ == '__main__':
    upload_files()

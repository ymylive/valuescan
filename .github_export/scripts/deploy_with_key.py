#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用公钥认证部署到VPS
"""
import paramiko
import os
import sys
from pathlib import Path

# VPS配置
VPS_HOST = "8.138.115.109"
VPS_USER = "root"
VPS_PASSWORD = "Qq159741"
VPS_PROJECT_PATH = "/root/valuescan"

# SSH密钥路径
SSH_KEY_PATH = os.path.expanduser("~/.ssh/valuescan_deploy")
SSH_PUB_KEY_PATH = os.path.expanduser("~/.ssh/valuescan_deploy.pub")

# 需要上传的文件
FILES_TO_UPLOAD = [
    ("signal_monitor/data_providers.py", "signal_monitor/data_providers.py"),
    ("signal_monitor/chart_pro_v10.py", "signal_monitor/chart_pro_v10.py"),
    ("docs/CRYPTO_DATA_APIS.md", "docs/CRYPTO_DATA_APIS.md"),
    ("docs/API_ACCESS_GUIDE.md", "docs/API_ACCESS_GUIDE.md"),
    ("test_data_providers.py", "test_data_providers.py"),
]


def setup_ssh_key():
    """首次设置：将公钥添加到VPS"""
    print("步骤1: 添加SSH公钥到VPS...")

    # 读取公钥
    with open(SSH_PUB_KEY_PATH, 'r') as f:
        pub_key = f.read().strip()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # 使用密码连接
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD,
                   look_for_keys=False, allow_agent=False)

        # 添加公钥到authorized_keys
        commands = [
            "mkdir -p ~/.ssh",
            "chmod 700 ~/.ssh",
            f"echo '{pub_key}' >> ~/.ssh/authorized_keys",
            "chmod 600 ~/.ssh/authorized_keys"
        ]

        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout.channel.recv_exit_status()

        ssh.close()
        print("✅ SSH公钥已添加到VPS\n")
        return True

    except Exception as e:
        print(f"❌ 添加公钥失败: {e}")
        return False


def upload_files_with_key():
    """使用SSH密钥上传文件"""
    print("步骤2: 使用SSH密钥上传文件...")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # 使用私钥连接
        private_key = paramiko.RSAKey.from_private_key_file(SSH_KEY_PATH)
        ssh.connect(VPS_HOST, username=VPS_USER, pkey=private_key)
        sftp = ssh.open_sftp()

        print(f"✅ 已连接到 {VPS_HOST}\n")

        for local_path, remote_path in FILES_TO_UPLOAD:
            local_file = Path(local_path)
            remote_file = f"{VPS_PROJECT_PATH}/{remote_path}"

            if not local_file.exists():
                print(f"⚠️  跳过: {local_path}")
                continue

            remote_dir = os.path.dirname(remote_file)
            try:
                sftp.stat(remote_dir)
            except:
                stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}")
                stdout.channel.recv_exit_status()

            print(f"上传: {local_path}")
            sftp.put(str(local_file), remote_file)
            print(f"✅ 完成\n")

        sftp.close()

        print("步骤3: 重启服务...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart valuescan-signal")
        stdout.channel.recv_exit_status()
        print("✅ 服务已重启\n")

        ssh.close()
        print("✅ 部署完成！")
        return True

    except Exception as e:
        print(f"❌ 部署失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("="*60)
    print("自动部署到VPS")
    print("="*60 + "\n")

    # 步骤1: 添加SSH公钥
    if not setup_ssh_key():
        sys.exit(1)

    # 步骤2: 使用公钥上传文件
    if not upload_files_with_key():
        sys.exit(1)

    print("\n" + "="*60)
    print("部署成功！")
    print("="*60)

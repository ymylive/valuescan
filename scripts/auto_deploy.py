#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动部署脚本 - 从环境变量读取VPS密码
"""
import paramiko
import os
import sys
from pathlib import Path

# VPS配置（允许环境变量覆盖）
VPS_HOST = os.getenv('VPS_HOST', "8.138.115.109")
VPS_USER = os.getenv('VPS_USER', "root")
VPS_PROJECT_PATH = os.getenv('VPS_PROJECT_PATH', "/root/valuescan")

# 从环境变量读取密码（必须提供）
VPS_PASSWORD = os.getenv('VALUESCAN_VPS_PASSWORD') or os.getenv('VPS_PASSWORD')
if not VPS_PASSWORD:
    raise RuntimeError("VPS_PASSWORD 环境变量未设置")

# 仅上传本次修改的文件
FILES_TO_UPLOAD = [
    ("signal_monitor/key_levels_pro.py", "signal_monitor/key_levels_pro.py"),
]


def upload_files():
    """上传文件到VPS"""
    print(f"连接到VPS: {VPS_HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # 使用密码认证
        ssh.connect(
            VPS_HOST,
            username=VPS_USER,
            password=VPS_PASSWORD,
            look_for_keys=False,
            allow_agent=False
        )
        sftp = ssh.open_sftp()

        print(f"已连接到 {VPS_HOST}\n")

        for local_path, remote_path in FILES_TO_UPLOAD:
            local_file = Path(local_path)
            remote_file = f"{VPS_PROJECT_PATH}/{remote_path}"

            if not local_file.exists():
                print(f"跳过: {local_path} (文件不存在)")
                continue

            # 确保远程目录存在
            remote_dir = os.path.dirname(remote_file)
            try:
                sftp.stat(remote_dir)
            except:
                stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}")
                stdout.channel.recv_exit_status()

            # 上传文件
            print(f"上传: {local_path}")
            sftp.put(str(local_file), remote_file)
            print(f"完成\n")

        sftp.close()

        # 重启signal monitor服务
        print("重启signal monitor服务...")
        stdin, stdout, stderr = ssh.exec_command(
            "systemctl restart valuescan-signal"
        )
        stdout.channel.recv_exit_status()
        print("服务已重启\n")

        ssh.close()
        print("部署完成！")
        return True

    except Exception as e:
        print(f"部署失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = upload_files()
    sys.exit(0 if success else 1)

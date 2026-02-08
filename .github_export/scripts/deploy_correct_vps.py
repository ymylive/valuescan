#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署到正确的VPS: 82.158.88.34
"""
import paramiko
import os
import sys
from pathlib import Path

# 正确的VPS配置
VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = "Qq159741"
VPS_PROJECT_PATH = "/root/valuescan"

# 需要上传的文件
FILES_TO_UPLOAD = [
    ("signal_monitor/data_providers.py", "signal_monitor/data_providers.py"),
    ("signal_monitor/chart_pro_v10.py", "signal_monitor/chart_pro_v10.py"),
]


def deploy():
    print(f"连接到VPS: {VPS_HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD,
                   look_for_keys=False, allow_agent=False)
        sftp = ssh.open_sftp()
        print(f"已连接\n")

        for local_path, remote_path in FILES_TO_UPLOAD:
            local_file = Path(local_path)
            remote_file = f"{VPS_PROJECT_PATH}/{remote_path}"

            if not local_file.exists():
                print(f"跳过: {local_path}")
                continue

            print(f"上传: {local_path}")
            sftp.put(str(local_file), remote_file)
            print(f"完成\n")

        sftp.close()

        print("重启服务...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart valuescan-signal")
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
    success = deploy()
    sys.exit(0 if success else 1)

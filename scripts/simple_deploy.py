#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化部署脚本 - 分步执行
"""
import paramiko
import os
import sys
from pathlib import Path

VPS_HOST = "8.138.115.109"
VPS_USER = "root"
VPS_PASSWORD = "Qq159741"
VPS_PROJECT_PATH = "/root/valuescan"

# 读取新生成的公钥
SSH_PUB_KEY = """ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCfBLxjaS5YfryajZdBaJaRVM9Sg7XJ19AKLLS1JESMZ7m8mj5pUqr7bGu8Tq3nYkpYkH4NBRG3Wy78lpzswAZHTYrDJL7T0CDd1UgEDzM7v7C7ZE3H6IRCpNP0QAfRhjVHG4D2N89WPL4sti1a+Rx+Fls/ogK+Cj0FGyA95qBT4KHI+vyBPUb90Xgv9U4+E/1pNqxD4PqjfwiDyMc4yFF+W6Aw6Odqja/BH2f2AY706SSKsPaQyuIi8qQ23NcwTLZrAwd2pBQH5+ZZF+TR3truKNQE8wW0qjXh7dLJtWXJH/pwVdRA8fItvJ4tMQcPEJOGspnKn4nmNUtav47Ar/t7vMxpAzI80vIrMo7enNyxrBzWQvjj2ZmPnKgQCs1JXXH/HZsidBdpMVAJjujJWRzj7gR1kx0FhfYj8NE2XgWC299g9Uns7Tp42ZEkVYHbWpBhJyWdbd9MNUnWIcoiHl1l8xGOKb/QomvKve2i7h7O7tE5iO0UvIBFWfUhaojeF5bNADUBmaSSOtdMnHJi37i8F+2QeeY7NQILUm+neCtjfPtpjRnfpHMKTcLtGjKyQbS/LHt0CppU9wq/JpAIDGO8cJN4WPRZaTvB8SOeu7T9aSPhfTNPQt2I809kw6F4VeeemPu6gVkijX8wolv0A+U3xZcCU2BjUtgBKuT1VFiCEw== valuescan_deploy"""

FILES = [
    ("signal_monitor/data_providers.py", "signal_monitor/data_providers.py"),
    ("signal_monitor/chart_pro_v10.py", "signal_monitor/chart_pro_v10.py"),
]


def add_ssh_key():
    """添加SSH公钥"""
    print("Step 1: Adding SSH key...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD,
                   look_for_keys=False, allow_agent=False)

        cmd = f"mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '{SSH_PUB_KEY}' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdout.channel.recv_exit_status()

        ssh.close()
        print("OK\n")
        return True
    except Exception as e:
        print(f"Failed: {e}\n")
        return False


def upload_files():
    """上传文件"""
    print("Step 2: Uploading files...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        key = paramiko.RSAKey.from_private_key_file(os.path.expanduser("~/.ssh/valuescan_deploy"))
        ssh.connect(VPS_HOST, username=VPS_USER, pkey=key)
        sftp = ssh.open_sftp()

        for local, remote in FILES:
            remote_file = f"{VPS_PROJECT_PATH}/{remote}"
            print(f"  {local}")
            sftp.put(local, remote_file)

        sftp.close()
        ssh.exec_command("systemctl restart valuescan-signal")
        ssh.close()
        print("OK\n")
        return True
    except Exception as e:
        print(f"Failed: {e}\n")
        return False


if __name__ == '__main__':
    if add_ssh_key() and upload_files():
        print("Deploy success!")
    else:
        sys.exit(1)

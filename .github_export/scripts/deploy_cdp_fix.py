#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署 CDP token 刷新服务修复
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
    "signal_monitor/cdp_token_refresher.py",
]


def create_ssh_client():
    """创建 SSH 客户端"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(VPS_HOST, port=VPS_PORT, username=VPS_USER, password=VPS_PASSWORD, timeout=30)
    return client


def upload_files(ssh_client):
    """上传文件到 VPS"""
    sftp = ssh_client.open_sftp()
    
    for rel_path in DEPLOY_FILES:
        local_path = LOCAL_ROOT / rel_path
        remote_path = f"{VPS_PATH}/{rel_path}"
        
        if not local_path.exists():
            print(f"[SKIP] 本地文件不存在: {local_path}")
            continue
        
        # 确保远程目录存在
        remote_dir = os.path.dirname(remote_path)
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            stdin, stdout, stderr = ssh_client.exec_command(f"mkdir -p {remote_dir}")
            stdout.read()
        
        print(f"[UPLOAD] {rel_path}")
        sftp.put(str(local_path), remote_path)
    
    sftp.close()


def restart_service(ssh_client, service_name):
    """重启服务"""
    print(f"[RESTART] {service_name}")
    stdin, stdout, stderr = ssh_client.exec_command(f"systemctl restart {service_name}")
    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        print(f"[ERROR] 重启失败: {stderr.read().decode()}")
        return False
    return True


def check_service_status(ssh_client, service_name):
    """检查服务状态"""
    stdin, stdout, stderr = ssh_client.exec_command(f"systemctl is-active {service_name}")
    status = stdout.read().decode().strip()
    return status == "active"


def get_service_logs(ssh_client, service_name, lines=50):
    """获取服务日志"""
    stdin, stdout, stderr = ssh_client.exec_command(
        f"journalctl -u {service_name} -n {lines} --no-pager"
    )
    return stdout.read().decode()


def main():
    print("=" * 50)
    print("部署 CDP Token 刷新服务修复")
    print("=" * 50)
    
    # 连接 VPS
    print("\n[1] 连接 VPS...")
    ssh = create_ssh_client()
    print(f"    已连接到 {VPS_HOST}")
    
    # 上传文件
    print("\n[2] 上传文件...")
    upload_files(ssh)
    
    # 重启服务
    print("\n[3] 重启 token 刷新服务...")
    restart_service(ssh, "valuescan-token-refresher")
    time.sleep(3)
    
    # 检查状态
    print("\n[4] 检查服务状态...")
    if check_service_status(ssh, "valuescan-token-refresher"):
        print("    ✓ valuescan-token-refresher 运行中")
    else:
        print("    ✗ valuescan-token-refresher 未运行")
    
    # 显示日志
    print("\n[5] 最近日志:")
    print("-" * 50)
    logs = get_service_logs(ssh, "valuescan-token-refresher", 30)
    print(logs)
    
    ssh.close()
    print("\n部署完成!")


if __name__ == "__main__":
    main()

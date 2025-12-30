#!/usr/bin/env python3
"""
部署前端到 VPS
"""
import os
import sys
import subprocess

try:
    import paramiko
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "paramiko"], check=True)
    import paramiko

VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "")

if not VPS_PASSWORD:
    print("Error: VALUESCAN_VPS_PASSWORD environment variable not set")
    exit(1)

print(f"Connecting to {VPS_HOST}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD)

sftp = ssh.open_sftp()

dist_dir = "web/dist"

def upload_dir(local_dir, remote_dir):
    """递归上传目录"""
    try:
        sftp.mkdir(remote_dir)
    except:
        pass
    
    for item in os.listdir(local_dir):
        local_path = os.path.join(local_dir, item)
        remote_path = f"{remote_dir}/{item}"
        
        if os.path.isfile(local_path):
            print(f"  {local_path} -> {remote_path}")
            sftp.put(local_path, remote_path)
        elif os.path.isdir(local_path):
            upload_dir(local_path, remote_path)

print("\n上传前端文件...")
upload_dir(dist_dir, "/root/valuescan/web/dist")

sftp.close()

# 同步到 nginx 服务的前端目录 (cornna.qzz.io / cornna.abrdns.com)
print("\n同步到 /var/www/valuescan ...")
stdin, stdout, stderr = ssh.exec_command("cp -r /root/valuescan/web/dist/* /var/www/valuescan/")
stdout.channel.recv_exit_status()
print("同步完成")

# 重载 nginx
print("\n重载 nginx...")
stdin, stdout, stderr = ssh.exec_command("nginx -t && systemctl reload nginx")
stdout.channel.recv_exit_status()
print(stdout.read().decode())

# 重启 API 服务以加载新前端
print("\n重启 API 服务...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart valuescan-api")
stdout.channel.recv_exit_status()

import time
time.sleep(2)

print("\n检查服务状态...")
stdin, stdout, stderr = ssh.exec_command("systemctl status valuescan-api --no-pager | head -10")
print(stdout.read().decode())

ssh.close()
print("\nDone! 前端已部署到:")
print("  - https://cornna.qzz.io/")
print("  - https://cornna.abrdns.com/")

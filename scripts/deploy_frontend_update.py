#!/usr/bin/env python3
"""部署前端更新到 VPS"""

import paramiko
import os
from pathlib import Path

VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741')
VALUESCAN_DIR = "/root/valuescan"

def main():
    print("=" * 60)
    print("部署前端更新到 VPS")
    print("=" * 60)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD)
    sftp = ssh.open_sftp()
    
    local_dist = Path("web/dist")
    remote_dist = f"{VALUESCAN_DIR}/web/dist"
    
    print(f"\n上传前端文件到 {remote_dist}...")
    
    # 清理远程目录
    stdin, stdout, stderr = ssh.exec_command(f'rm -rf {remote_dist}/*')
    stdout.read()
    
    # 上传所有文件
    file_count = 0
    for path in local_dist.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(local_dist).as_posix()
        remote_path = f"{remote_dist}/{rel}"
        
        # 创建远程目录
        remote_dir = remote_path.rsplit("/", 1)[0]
        try:
            sftp.stat(remote_dir)
        except:
            stdin, stdout, stderr = ssh.exec_command(f'mkdir -p {remote_dir}')
            stdout.read()
        
        sftp.put(str(path), remote_path)
        file_count += 1
    
    print(f"  上传了 {file_count} 个文件")
    
    # 重启 API 服务
    print("\n重启 API 服务...")
    stdin, stdout, stderr = ssh.exec_command('systemctl restart valuescan-api')
    stdout.read()
    
    print("\n✓ 部署完成!")
    print(f"访问: https://cornna.abrdns.com/")
    
    sftp.close()
    ssh.close()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
设置 ValueScan 自动重登录的部署脚本。

此脚本会：
1. 上传更新后的 systemd 服务文件到 VPS
2. 重新加载 systemd 配置
3. 重启信号监控服务

使用方法:
  python scripts/setup_auto_relogin.py
"""

import sys
import os
from pathlib import Path

# VPS 配置
VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "")
VPS_PATH = "/root/valuescan"


def get_ssh_client(retries: int = 3):
    """获取 SSH 客户端"""
    try:
        import paramiko
    except ImportError:
        print("正在安装 paramiko...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "paramiko", "-q"])
        import paramiko
    
    import time
    
    for attempt in range(retries):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                VPS_HOST, 
                username=VPS_USER, 
                password=VPS_PASSWORD, 
                timeout=60,
                banner_timeout=60,
                auth_timeout=60
            )
            return client
        except Exception as e:
            print(f"  连接尝试 {attempt + 1}/{retries} 失败: {e}")
            if attempt < retries - 1:
                print(f"  等待 5 秒后重试...")
                time.sleep(5)
            else:
                raise


def run_ssh(client, cmd: str) -> tuple:
    """执行 SSH 命令"""
    print(f"[SSH] {cmd}")
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
        out = stdout.read().decode('utf-8', errors='ignore')
        err = stderr.read().decode('utf-8', errors='ignore')
        exit_code = stdout.channel.recv_exit_status()
        if out:
            print(out)
        if err and exit_code != 0:
            print(err, file=sys.stderr)
        return exit_code, out, err
    except Exception as e:
        print(f"[SSH] 错误: {e}")
        return -1, "", str(e)


def run_scp(client, local_path: str, remote_path: str) -> bool:
    """上传文件到 VPS"""
    print(f"[SCP] {local_path} -> {remote_path}")
    try:
        sftp = client.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
        print(f"  ✓ 上传成功")
        return True
    except Exception as e:
        print(f"[SCP] 错误: {e}")
        return False


def main():
    print("=" * 60)
    print("ValueScan 自动重登录配置部署")
    print("=" * 60)
    
    if not VPS_PASSWORD:
        print("错误: 请设置环境变量 VALUESCAN_VPS_PASSWORD")
        return 1
    
    base_dir = Path(__file__).resolve().parent.parent
    
    # 连接 VPS
    print("\n[0/4] 连接 VPS...")
    try:
        client = get_ssh_client()
        print(f"  ✓ 已连接到 {VPS_HOST}")
    except Exception as e:
        print(f"  ✗ 连接失败: {e}")
        return 1
    
    try:
        # 1. 上传服务文件
        print("\n[1/4] 上传 systemd 服务文件...")
        
        service_files = [
            ("valuescan-signal.service", "/etc/systemd/system/valuescan-signal.service"),
            ("valuescan-monitor.service", "/etc/systemd/system/valuescan-monitor.service"),
        ]
        
        for local_name, remote_path in service_files:
            local_path = base_dir / local_name
            if local_path.exists():
                if run_scp(client, str(local_path), remote_path):
                    print(f"  ✓ {local_name}")
                else:
                    print(f"  ✗ {local_name} 上传失败")
            else:
                print(f"  - {local_name} 不存在，跳过")
        
        # 2. 重新加载 systemd
        print("\n[2/4] 重新加载 systemd 配置...")
        code, _, _ = run_ssh(client, "systemctl daemon-reload")
        if code == 0:
            print("  ✓ systemd 配置已重新加载")
        else:
            print("  ✗ 重新加载失败")
        
        # 3. 重启服务
        print("\n[3/4] 重启信号监控服务...")
        code, _, _ = run_ssh(client, "systemctl restart valuescan-signal")
        if code == 0:
            print("  ✓ valuescan-signal 已重启")
        else:
            print("  - valuescan-signal 重启失败或不存在")
        
        # 4. 检查状态
        print("\n[4/4] 检查服务状态...")
        code, stdout, _ = run_ssh(client, "systemctl is-active valuescan-signal")
        status = stdout.strip() if stdout else "unknown"
        print(f"  valuescan-signal: {status}")
        
        # 显示环境变量配置
        print("\n" + "=" * 60)
        print("自动重登录配置:")
        print("  VALUESCAN_EMAIL: ymy_live@outlook.com")
        print("  VALUESCAN_PASSWORD: ********")
        print("  VALUESCAN_AUTO_RELOGIN: 1")
        print("  VALUESCAN_AUTO_RELOGIN_COOLDOWN: 1800 秒 (30分钟)")
        print("=" * 60)
        
        print("\n完成! 当 token 过期时，系统会自动尝试重新登录。")
        print(f"查看日志: ssh {VPS_USER}@{VPS_HOST} 'journalctl -u valuescan-signal -f'")
        
    finally:
        client.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

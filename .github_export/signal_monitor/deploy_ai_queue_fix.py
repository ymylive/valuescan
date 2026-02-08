#!/usr/bin/env python3
"""
部署 AI 简评队列修复到 VPS
- ai_signal_queue.py (新文件)
- telegram.py (修改)
- chart_pro_v10.py (修改)
- ai_signal_analysis.py (修改)
"""

import paramiko
import os
from pathlib import Path

# VPS 配置
VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = "Qq159741"
VPS_PATH = "/root/valuescan/signal_monitor"

# 本地文件路径
LOCAL_DIR = Path(__file__).parent

# 需要部署的文件
FILES_TO_DEPLOY = [
    "ai_signal_queue.py",      # 新文件：队列管理器
    "telegram.py",             # 修改：使用队列
    "chart_pro_v10.py",        # 修改：添加代理支持
    "ai_signal_analysis.py",   # 修改：添加代理支持
]


def deploy():
    print(f"🚀 连接 VPS: {VPS_HOST}")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # 重试连接
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"   尝试连接 ({attempt + 1}/{max_retries})...")
            ssh.connect(
                VPS_HOST, 
                username=VPS_USER, 
                password=VPS_PASSWORD, 
                timeout=60,
                banner_timeout=60,
                auth_timeout=60
            )
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"   连接失败，重试中... ({e})")
                import time
                time.sleep(3)
            else:
                raise
    
    try:
        pass  # placeholder for indentation
        print("✅ SSH 连接成功")
        
        sftp = ssh.open_sftp()
        
        for filename in FILES_TO_DEPLOY:
            local_path = LOCAL_DIR / filename
            remote_path = f"{VPS_PATH}/{filename}"
            
            if not local_path.exists():
                print(f"⚠️ 本地文件不存在: {local_path}")
                continue
            
            print(f"📤 上传: {filename}")
            sftp.put(str(local_path), remote_path)
            print(f"   ✅ {filename} -> {remote_path}")
        
        sftp.close()
        
        # 重启服务
        print("\n🔄 重启 valuescan 服务...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart valuescan")
        exit_code = stdout.channel.recv_exit_status()
        
        if exit_code == 0:
            print("✅ valuescan 服务已重启")
        else:
            error = stderr.read().decode()
            print(f"⚠️ 重启返回码: {exit_code}")
            if error:
                print(f"   错误: {error}")
        
        # 检查服务状态
        print("\n📊 检查服务状态...")
        stdin, stdout, stderr = ssh.exec_command("systemctl status valuescan --no-pager -l | head -20")
        status = stdout.read().decode()
        print(status)
        
        print("\n✅ 部署完成!")
        
    except Exception as e:
        print(f"❌ 部署失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh.close()


if __name__ == "__main__":
    deploy()

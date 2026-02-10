#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速部署关键文件到 VPS
"""
import os
import sys
import getpass
import paramiko
from pathlib import Path

# 设置 Windows 控制台编码
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

DEFAULT_HOST = "82.158.88.34"
DEFAULT_USER = "root"
VALUESCAN_DIR = "/root/valuescan"

def _get_password():
    password = os.environ.get("VALUESCAN_VPS_PASSWORD", "")
    if password:
        return password
    if sys.stdin.isatty():
        try:
            pw = getpass.getpass(f"Enter SSH password for {DEFAULT_USER}@{DEFAULT_HOST}: ")
            return (pw or "").strip() or None
        except Exception:
            pass
    return None

def _exec(ssh, cmd, timeout=60):
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="ignore")
        err = stderr.read().decode("utf-8", errors="ignore")
        return (out + ("\n" + err if err else "")).strip()
    except Exception as exc:
        return f"[exec error] {cmd}: {exc}"

def _sftp_put_mkdir(sftp, local_path, remote_path):
    """上传文件，自动创建目录"""
    remote_dir = remote_path.rsplit("/", 1)[0]
    parts = remote_dir.split("/")
    cur = ""
    for part in parts:
        if not part:
            continue
        cur += f"/{part}"
        try:
            sftp.stat(cur)
        except Exception:
            try:
                sftp.mkdir(cur)
            except Exception:
                pass
    sftp.put(str(local_path), remote_path)

def main():
    password = _get_password()
    if not password:
        print("❌ 需要设置 VALUESCAN_VPS_PASSWORD 环境变量")
        return

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"连接到 {DEFAULT_USER}@{DEFAULT_HOST}...")
        ssh.connect(DEFAULT_HOST, username=DEFAULT_USER, password=password, timeout=30)
        print("✅ SSH 连接成功\n")
    except Exception as e:
        print(f"❌ SSH 连接失败: {e}")
        return

    sftp = ssh.open_sftp()

    # 需要部署的文件列表
    files_to_deploy = [
        # 配置文件
        ("signal_monitor/config.example.py", f"{VALUESCAN_DIR}/signal_monitor/config.example.py"),

        # 核心模块
        ("signal_monitor/market_data_sources.py", f"{VALUESCAN_DIR}/signal_monitor/market_data_sources.py"),
        ("signal_monitor/ai_market_summary.py", f"{VALUESCAN_DIR}/signal_monitor/ai_market_summary.py"),
        ("signal_monitor/polling_monitor.py", f"{VALUESCAN_DIR}/signal_monitor/polling_monitor.py"),
        ("signal_monitor/message_handler.py", f"{VALUESCAN_DIR}/signal_monitor/message_handler.py"),

        # API服务器
        ("api/server.py", f"{VALUESCAN_DIR}/api/server.py"),

        # 前端构建
        ("web/dist", f"{VALUESCAN_DIR}/web/dist"),
    ]

    print("=" * 80)
    print("开始部署文件")
    print("=" * 80)

    for local_rel, remote_path in files_to_deploy:
        local_path = Path(local_rel)

        if not local_path.exists():
            print(f"⚠️  跳过不存在的文件: {local_rel}")
            continue

        if local_path.is_dir():
            # 处理目录
            print(f"\n📁 同步目录: {local_rel} -> {remote_path}")

            # 清空远程目录
            _exec(ssh, f"rm -rf {remote_path}/* 2>/dev/null || true")
            _exec(ssh, f"mkdir -p {remote_path}")

            # 上传所有文件
            count = 0
            for file_path in local_path.rglob("*"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(local_path)
                    remote_file = f"{remote_path}/{rel_path}".replace("\\", "/")
                    try:
                        _sftp_put_mkdir(sftp, file_path, remote_file)
                        count += 1
                    except Exception as e:
                        print(f"  ❌ 上传失败: {rel_path} - {e}")

            print(f"  ✅ 上传了 {count} 个文件")
        else:
            # 处理单个文件
            print(f"📄 上传文件: {local_rel} -> {remote_path}")
            try:
                _sftp_put_mkdir(sftp, local_path, remote_path)
                print(f"  ✅ 上传成功")
            except Exception as e:
                print(f"  ❌ 上传失败: {e}")

    print("\n" + "=" * 80)
    print("重启服务")
    print("=" * 80)

    services = ["valuescan-signal", "valuescan-api"]
    for service in services:
        print(f"\n重启 {service}...")
        result = _exec(ssh, f"systemctl restart {service}")
        if result:
            print(f"  {result}")

        # 检查状态
        result = _exec(ssh, f"systemctl is-active {service}")
        if "active" in result:
            print(f"  ✅ {service} 运行中")
        else:
            print(f"  ❌ {service} 状态: {result}")

    print("\n" + "=" * 80)
    print("部署完成")
    print("=" * 80)

    sftp.close()
    ssh.close()

if __name__ == "__main__":
    main()

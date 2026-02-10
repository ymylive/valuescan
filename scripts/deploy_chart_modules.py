#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署图表相关模块
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

    # 图表相关模块
    chart_modules = [
        "key_levels_enhanced.py",
        "key_levels_pro.py",
        "pattern_detection_enhanced.py",
        "auxiliary_line_drawer.py",
        "ai_pattern_drawer.py",
        "ai_key_levels_cache.py",
        "ai_overlays_cache.py",
        "chart_fonts.py",
        "data_providers.py",
    ]

    print("=" * 80)
    print("部署图表相关模块")
    print("=" * 80)

    for module in chart_modules:
        local_path = Path(f"signal_monitor/{module}")
        remote_path = f"{VALUESCAN_DIR}/signal_monitor/{module}"

        if not local_path.exists():
            print(f"⚠️  跳过不存在的文件: {module}")
            continue

        print(f"📄 上传: {module}")
        try:
            _sftp_put_mkdir(sftp, local_path, remote_path)
            print(f"  ✅ 上传成功")
        except Exception as e:
            print(f"  ❌ 上传失败: {e}")

    print("\n" + "=" * 80)
    print("重启服务")
    print("=" * 80)

    print("\n重启 valuescan-signal...")
    result = _exec(ssh, "systemctl restart valuescan-signal")
    if result:
        print(f"  {result}")

    # 等待服务启动
    import time
    time.sleep(3)

    # 检查状态
    result = _exec(ssh, "systemctl is-active valuescan-signal")
    if "active" in result:
        print(f"  ✅ valuescan-signal 运行中")
    else:
        print(f"  ❌ valuescan-signal 状态: {result}")

    # 检查最新日志
    print("\n检查最新日志...")
    result = _exec(ssh, "journalctl -u valuescan-signal -n 20 --no-pager | tail -10")
    print(result)

    print("\n" + "=" * 80)
    print("部署完成")
    print("=" * 80)

    sftp.close()
    ssh.close()

if __name__ == "__main__":
    main()

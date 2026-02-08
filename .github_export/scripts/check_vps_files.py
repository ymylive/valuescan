#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查 VPS 上的前端文件
"""
import os
import sys

try:
    import paramiko
except ImportError:
    print("错误: 未安装 paramiko 库")
    print("请运行: pip install paramiko")
    sys.exit(1)

# VPS 配置
VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PORT = 22
VPS_PATH = "/root/valuescan"

def run_ssh_command(ssh, command):
    """执行 SSH 命令并返回输出"""
    try:
        stdin, stdout, stderr = ssh.exec_command(command, timeout=30)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        return output, error, exit_status == 0
    except Exception as e:
        return "", str(e), False

def main():
    # 设置 Windows 控制台编码
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

    print("=" * 60)
    print("  检查 VPS 前端文件")
    print("=" * 60)

    # 获取密码
    password = os.environ.get('VALUESCAN_VPS_PASSWORD')
    if not password:
        print("错误: 未设置 VPS 密码环境变量")
        sys.exit(1)

    # 连接 SSH
    print("\n正在连接 VPS...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(
            hostname=VPS_HOST,
            port=VPS_PORT,
            username=VPS_USER,
            password=password,
            timeout=30
        )
        print("✓ SSH 连接成功\n")
    except Exception as e:
        print(f"连接失败: {e}")
        sys.exit(1)

    # 检查命令列表
    checks = [
        ("检查前端构建目录", f"ls -lh {VPS_PATH}/web/dist/"),
        ("检查 ProxyPage JS 文件", f"ls -lh {VPS_PATH}/web/dist/assets/ProxyPage*.js"),
        ("检查源代码", f"grep -c '订阅管理' {VPS_PATH}/web/src/pages/ProxyPage.tsx || echo '0'"),
        ("检查构建文件内容", f"strings {VPS_PATH}/web/dist/assets/ProxyPage*.js | grep -o '订阅管理' | head -1 || echo '未找到'"),
    ]

    for desc, cmd in checks:
        print(f"\n{desc}...")
        print(f"命令: {cmd}")
        output, error, success = run_ssh_command(ssh, cmd)
        if output:
            print(output)
        if error and "WARNING" not in error:
            print(f"错误: {error}")

    ssh.close()
    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()

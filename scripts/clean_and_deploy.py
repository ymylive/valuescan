#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理 VPS 旧组件文件并重新部署
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

def run_ssh_command(ssh, command, show_output=True):
    """执行 SSH 命令"""
    try:
        stdin, stdout, stderr = ssh.exec_command(command, timeout=300)
        exit_status = stdout.channel.recv_exit_status()

        if show_output:
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')

            if output:
                print(output)
            if error and "WARNING" not in error and "npm WARN" not in error:
                print(error, file=sys.stderr)

        return exit_status == 0
    except Exception as e:
        print(f"执行失败: {e}")
        return False

def main():
    # 设置 Windows 控制台编码
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

    print("=" * 50)
    print("  清理并重新部署到 VPS")
    print("=" * 50)
    print(f"\nVPS: {VPS_USER}@{VPS_HOST}:{VPS_PORT}")
    print(f"路径: {VPS_PATH}\n")

    # 获取密码
    password = os.environ.get('VALUESCAN_VPS_PASSWORD')
    if not password:
        print("错误: 未设置 VPS 密码环境变量")
        sys.exit(1)

    # 连接 SSH
    print("正在连接 VPS...")
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

    steps = [
        ("清理旧组件文件", f"cd {VPS_PATH}/web/src/components && rm -rf valuescan"),
        ("清理旧库文件", f"cd {VPS_PATH}/web/src && rm -rf lib"),
        ("清理旧上下文文件", f"cd {VPS_PATH}/web/src && rm -rf contexts"),
        ("清理旧钩子文件", f"cd {VPS_PATH}/web/src && rm -rf hooks"),
        ("清理旧样式文件", f"cd {VPS_PATH}/web/src && rm -rf styles"),
        ("清理旧常量文件", f"cd {VPS_PATH}/web/src && rm -rf constants"),
        ("清理旧 i18n 文件", f"cd {VPS_PATH}/web/src && rm -rf i18n"),
        ("清理 node_modules", f"cd {VPS_PATH}/web && rm -rf node_modules"),
        ("清理构建缓存", f"cd {VPS_PATH}/web && rm -rf dist .vite"),
        ("重新安装依赖", f"cd {VPS_PATH}/web && npm install"),
        ("构建前端", f"cd {VPS_PATH}/web && npm run build"),
        ("重启服务", "systemctl restart valuescan-signal && systemctl restart valuescan-trader"),
    ]

    success = True
    for i, (desc, cmd) in enumerate(steps, 1):
        print(f"[{i}/{len(steps)}] {desc}...")
        if not run_ssh_command(ssh, cmd, show_output=(i >= 10)):  # 只显示安装和构建的输出
            print(f"步骤失败: {desc}")
            success = False
            break
        print(f"✓ {desc}完成\n")

    ssh.close()

    if success:
        print("=" * 50)
        print("  ✓ 部署完成!")
        print("=" * 50)
        print("\n已重启服务:")
        print("  - valuescan-signal (信号监控)")
        print("  - valuescan-trader (交易机器人)")
        print()
    else:
        print("\n部署失败，请检查错误信息")
        sys.exit(1)

if __name__ == "__main__":
    main()

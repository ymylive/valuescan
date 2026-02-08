#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ValueScan Clash 功能更新部署脚本
部署 Clash 前后端连接修复和服务管理功能
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

def run_ssh_command(ssh, command, show_output=True, timeout=300):
    """执行 SSH 命令"""
    try:
        stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
        exit_status = stdout.channel.recv_exit_status()

        if show_output:
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')

            if output:
                print(output)
            if error and "WARNING" not in error and "warning" not in error.lower():
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

    print("=" * 60)
    print("  ValueScan Clash 功能更新部署")
    print("=" * 60)
    print(f"\nVPS: {VPS_USER}@{VPS_HOST}:{VPS_PORT}")
    print(f"路径: {VPS_PATH}\n")

    # 获取密码
    password = os.environ.get('VALUESCAN_VPS_PASSWORD')
    if not password:
        print("错误: 未设置 VPS 密码环境变量")
        print("\n请先设置密码:")
        print("  Windows: set VALUESCAN_VPS_PASSWORD=your_password")
        print("  Linux/Mac: export VALUESCAN_VPS_PASSWORD=your_password")
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

    # 部署步骤
    steps = [
        ("检查当前分支", f"cd {VPS_PATH} && git branch"),
        ("拉取最新代码", f"cd {VPS_PATH} && git fetch origin && git reset --hard origin/master"),
        ("检查更新的文件", f"cd {VPS_PATH} && git log -1 --stat"),
        ("安装前端依赖", f"cd {VPS_PATH}/web && npm install"),
        ("构建前端", f"cd {VPS_PATH}/web && npm run build"),
        ("创建数据目录", f"mkdir -p {VPS_PATH}/data"),
        ("重启 API 服务", "systemctl restart valuescan-api"),
        ("检查 API 服务状态", "systemctl status valuescan-api --no-pager -l | head -10"),
        ("重启信号监控", "systemctl restart valuescan-signal"),
    ]

    success = True
    for i, (desc, cmd) in enumerate(steps, 1):
        print(f"\n[{i}/{len(steps)}] {desc}...")
        print(f"命令: {cmd}")
        if not run_ssh_command(ssh, cmd):
            print(f"⚠ 步骤失败: {desc}")
            # 某些步骤失败不影响继续（如检查状态）
            if "检查" not in desc and "状态" not in desc:
                success = False
                break
        print(f"✓ {desc}完成")

    ssh.close()

    print("\n" + "=" * 60)
    if success:
        print("✓ 部署完成！")
        print("\n后续步骤:")
        print("1. 访问 Web 界面: http://82.158.88.34")
        print("2. 进入代理管理页面检查 Clash 服务状态")
        print("3. 如果 Clash 未运行，点击'尝试启动服务'按钮")
        print("4. 或手动启动: systemctl start clash")
    else:
        print("✗ 部署过程中出现错误")
        print("请检查上面的错误信息")
    print("=" * 60)

if __name__ == '__main__':
    main()

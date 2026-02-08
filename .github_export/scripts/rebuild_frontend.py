#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
强制重新构建前端并清除缓存
"""
import os
import sys

try:
    import paramiko
except ImportError:
    print("错误: 未安装 paramiko 库")
    sys.exit(1)

VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PORT = 22
VPS_PATH = "/root/valuescan"

def run_command(ssh, cmd, desc):
    """执行命令"""
    print(f"\n{desc}...")
    print(f"命令: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=300)
    stdout.channel.recv_exit_status()
    output = stdout.read().decode('utf-8', errors='ignore')
    if output:
        print(output[:500])  # 只显示前500字符
    return True

def main():
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

    password = os.environ.get('VALUESCAN_VPS_PASSWORD')
    if not password:
        print("错误: 未设置密码")
        sys.exit(1)

    print("=" * 60)
    print("  强制重新构建前端")
    print("=" * 60)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(VPS_HOST, VPS_PORT, VPS_USER, password, timeout=30)
        print("\n✓ 连接成功")

        # 执行构建步骤
        steps = [
            ("删除旧的构建文件", f"rm -rf {VPS_PATH}/web/dist"),
            ("删除 node_modules/.vite 缓存", f"rm -rf {VPS_PATH}/web/node_modules/.vite"),
            ("重新构建前端", f"cd {VPS_PATH}/web && npm run build"),
            ("检查新构建的文件", f"ls -lh {VPS_PATH}/web/dist/assets/ProxyPage*.js"),
            ("验证构建内容", f"strings {VPS_PATH}/web/dist/assets/ProxyPage*.js | grep -c '订阅' || echo '0'"),
            ("重启 Nginx", "systemctl restart nginx"),
            ("重启 API 服务", "systemctl restart valuescan-api"),
        ]

        for desc, cmd in steps:
            run_command(ssh, cmd, desc)

        ssh.close()
        print("\n" + "=" * 60)
        print("✓ 重新构建完成！")
        print("请刷新浏览器（Ctrl+F5 强制刷新）")
        print("=" * 60)

    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

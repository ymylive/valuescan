#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查 VPS 源代码文件
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

def main():
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

    password = os.environ.get('VALUESCAN_VPS_PASSWORD')
    if not password:
        print("错误: 未设置密码")
        sys.exit(1)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(VPS_HOST, VPS_PORT, VPS_USER, password, timeout=30)
        print("✓ 连接成功\n")

        # 检查源代码
        cmd = "grep -n '订阅管理' /root/valuescan/web/src/pages/ProxyPage.tsx"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        output = stdout.read().decode('utf-8')

        print("VPS 源代码中的'订阅管理':")
        print(output if output else "未找到")

        ssh.close()
    except Exception as e:
        print(f"错误: {e}")

if __name__ == '__main__':
    main()

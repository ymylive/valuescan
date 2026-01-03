#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查构建文件的实际内容
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

        # 读取构建文件的一部分内容
        cmd = "head -c 5000 /root/valuescan/web/dist/assets/ProxyPage*.js"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        content = stdout.read().decode('utf-8', errors='ignore')

        print("构建文件前5000字符:")
        print(content)
        print("\n" + "=" * 60)

        # 检查是否包含 LinkIcon 或其他关键词
        keywords = ['LinkIcon', 'subscription', 'Subscription', 'Modal', 'showSubscription']
        print("\n检查关键词:")
        for keyword in keywords:
            cmd = f"grep -o '{keyword}' /root/valuescan/web/dist/assets/ProxyPage*.js | head -1"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            result = stdout.read().decode('utf-8').strip()
            print(f"  {keyword}: {'✓ 找到' if result else '✗ 未找到'}")

        ssh.close()

    except Exception as e:
        print(f"错误: {e}")

if __name__ == '__main__':
    main()

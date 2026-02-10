#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为Python 3.9安装图表生成依赖包
"""
import paramiko
import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password="Qq159741",
           look_for_keys=False, allow_agent=False)

print("为Python 3.9安装依赖包...")
packages = [
    "numpy",
    "pandas",
    "matplotlib",
    "scipy",
    "ccxt",
    "pycoingecko"
]

for package in packages:
    print(f"\n安装 {package} 到 python3.9...")
    stdin, stdout, stderr = ssh.exec_command(
        f"python3.9 -m pip install {package}"
    )
    exit_status = stdout.channel.recv_exit_status()

    output = stdout.read().decode('utf-8', errors='ignore')
    if exit_status == 0:
        print(f"✅ {package} 安装成功")
    else:
        error = stderr.read().decode('utf-8', errors='ignore')
        print(f"输出: {output}")
        print(f"错误: {error}")

print("\n验证安装...")
stdin, stdout, stderr = ssh.exec_command(
    "python3.9 -c 'import numpy, pandas, matplotlib, scipy, ccxt; "
    "from pycoingecko import CoinGeckoAPI; "
    "print(\"✅ 所有依赖包导入成功\")'"
)
result = stdout.read().decode('utf-8', errors='ignore')
error = stderr.read().decode('utf-8', errors='ignore')

if result:
    print(result)
else:
    print(f"验证失败: {error}")

ssh.close()
print("\n完成！")

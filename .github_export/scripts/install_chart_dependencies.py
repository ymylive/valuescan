#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安装图表生成所需的依赖包
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

print("检查当前已安装的包...")
stdin, stdout, stderr = ssh.exec_command("pip3 list | grep -E 'numpy|pandas|matplotlib|scipy|ccxt|pycoingecko'")
current_packages = stdout.read().decode('utf-8', errors='ignore')
print("当前已安装:")
print(current_packages if current_packages else "未找到相关包")

print("\n开始安装图表生成依赖包...")
packages = [
    "numpy",
    "pandas",
    "matplotlib",
    "scipy",
    "ccxt",
    "pycoingecko"
]

for package in packages:
    print(f"\n安装 {package}...")
    stdin, stdout, stderr = ssh.exec_command(f"pip3 install {package}")
    exit_status = stdout.channel.recv_exit_status()

    if exit_status == 0:
        print(f"✅ {package} 安装成功")
    else:
        error = stderr.read().decode('utf-8', errors='ignore')
        print(f"❌ {package} 安装失败:")
        print(error)

print("\n验证安装...")
stdin, stdout, stderr = ssh.exec_command("pip3 list | grep -E 'numpy|pandas|matplotlib|scipy|ccxt|pycoingecko'")
final_packages = stdout.read().decode('utf-8', errors='ignore')
print("最终已安装:")
print(final_packages)

ssh.close()
print("\n依赖安装完成！")

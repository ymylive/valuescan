#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重启服务并测试
"""
import paramiko
import sys
import codecs
import time

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password="Qq159741",
           look_for_keys=False, allow_agent=False)

print("1. 检查服务使用的Python环境...")
stdin, stdout, stderr = ssh.exec_command(
    "systemctl cat valuescan-signal | grep ExecStart"
)
exec_start = stdout.read().decode('utf-8', errors='ignore')
print(exec_start)

print("\n2. 检查Python3路径...")
stdin, stdout, stderr = ssh.exec_command("which python3")
python_path = stdout.read().decode('utf-8', errors='ignore').strip()
print(f"Python3路径: {python_path}")

print("\n3. 验证Python3环境中的numpy...")
stdin, stdout, stderr = ssh.exec_command(f"{python_path} -c 'import numpy; print(numpy.__version__)'")
numpy_check = stdout.read().decode('utf-8', errors='ignore')
numpy_error = stderr.read().decode('utf-8', errors='ignore')
if numpy_check:
    print(f"✅ numpy版本: {numpy_check.strip()}")
else:
    print(f"❌ numpy导入失败: {numpy_error}")

print("\n4. 重启valuescan-signal服务...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart valuescan-signal")
stdout.channel.recv_exit_status()
print("✅ 服务已重启")

print("\n5. 等待5秒让服务启动...")
time.sleep(5)

print("\n6. 检查服务状态...")
stdin, stdout, stderr = ssh.exec_command("systemctl status valuescan-signal --no-pager")
status = stdout.read().decode('utf-8', errors='ignore')
print(status)

ssh.close()
print("\n完成！")

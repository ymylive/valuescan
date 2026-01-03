#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

print("1. 重启Clash...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart clash")
stdout.channel.recv_exit_status()
print("✅ 已重启")

print("\n2. 等待10秒...")
time.sleep(10)

print("\n3. 检查端口...")
stdin, stdout, stderr = ssh.exec_command("netstat -tuln | grep -E '7890|7891'")
ports = stdout.read().decode('utf-8', errors='ignore')
if ports:
    print("✅ 端口已监听:")
    print(ports)
else:
    print("❌ 端口未监听")

print("\n4. 测试代理...")
stdin, stdout, stderr = ssh.exec_command(
    "curl -x socks5://127.0.0.1:7891 -s -o /dev/null -w '%{http_code}' "
    "--connect-timeout 10 https://fapi.binance.com/fapi/v1/ping"
)
result = stdout.read().decode('utf-8', errors='ignore').strip()
print(f"代理响应: {result}")

if result == '200':
    print("✅ 代理工作正常！")
else:
    print(f"⚠️ 代理异常: {result}")

ssh.close()

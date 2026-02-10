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

print("1. 重启Clash服务...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart clash")
stdout.channel.recv_exit_status()
print("✅ Clash已重启")

print("\n2. 等待5秒让Clash启动...")
time.sleep(5)

print("\n3. 检查Clash状态...")
stdin, stdout, stderr = ssh.exec_command("systemctl status clash --no-pager | head -15")
status = stdout.read().decode('utf-8', errors='ignore')
print(status)

print("\n4. 测试代理连接到Binance...")
stdin, stdout, stderr = ssh.exec_command(
    "curl -x socks5://127.0.0.1:7891 -s -o /dev/null -w '%{http_code}' "
    "--connect-timeout 5 https://fapi.binance.com/fapi/v1/ping"
)
result = stdout.read().decode('utf-8', errors='ignore').strip()
print(f"Binance API响应码: {result}")

if result == '200':
    print("✅ 代理连接正常")
else:
    print(f"⚠️ 代理连接异常")

ssh.close()
print("\n完成！")

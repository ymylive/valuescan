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

print("1. 等待Clash完全初始化（30秒）...")
time.sleep(30)

print("\n2. 检查Clash日志...")
stdin, stdout, stderr = ssh.exec_command("journalctl -u clash -n 20 --no-pager")
logs = stdout.read().decode('utf-8', errors='ignore')
print(logs[-1000:])  # 只显示最后1000字符

print("\n3. 测试代理端口是否监听...")
stdin, stdout, stderr = ssh.exec_command("netstat -tuln | grep -E '7890|7891'")
ports = stdout.read().decode('utf-8', errors='ignore')
print(ports if ports else "端口未监听")

print("\n4. 直接测试Binance API（不使用代理）...")
stdin, stdout, stderr = ssh.exec_command(
    "curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 https://fapi.binance.com/fapi/v1/ping"
)
direct_result = stdout.read().decode('utf-8', errors='ignore').strip()
print(f"直连响应码: {direct_result}")

print("\n5. 测试代理连接...")
stdin, stdout, stderr = ssh.exec_command(
    "curl -x socks5://127.0.0.1:7891 -s -o /dev/null -w '%{http_code}' "
    "--connect-timeout 10 https://fapi.binance.com/fapi/v1/ping"
)
proxy_result = stdout.read().decode('utf-8', errors='ignore').strip()
print(f"代理响应码: {proxy_result}")

ssh.close()

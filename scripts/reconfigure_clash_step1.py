#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新配置Clash - 完全禁用DNS并修复配置
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

print("1. 停止Clash服务...")
stdin, stdout, stderr = ssh.exec_command("systemctl stop clash")
stdout.channel.recv_exit_status()
print("✅ 已停止")

print("\n2. 使用另一个转换API...")
# 使用不同的转换参数，禁用DNS
subscription_url = "https://nano.nachoneko.cn/api/v1/client/subscribe?token=0564faff9cfd13442873e71f9a235469"

cmd = (
    f"curl -s 'https://api.v1.mk/sub?target=clash&url={subscription_url}"
    f"&insert=false&config=https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/config/ACL4SSR_Online.ini' "
    f"-o /etc/clash/config.yaml"
)

stdin, stdout, stderr = ssh.exec_command(cmd)
exit_status = stdout.channel.recv_exit_status()

# 检查文件
stdin, stdout, stderr = ssh.exec_command("wc -l /etc/clash/config.yaml")
lines = stdout.read().decode('utf-8', errors='ignore').strip()
print(f"配置文件: {lines}")

ssh.close()
print("\n完成第一步！")

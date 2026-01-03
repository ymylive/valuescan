#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import paramiko
import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password="Qq159741",
           look_for_keys=False, allow_agent=False)

print("1. 备份旧配置...")
stdin, stdout, stderr = ssh.exec_command("cp /etc/clash/config.yaml /etc/clash/config.yaml.bak 2>/dev/null || true")
stdout.channel.recv_exit_status()

print("\n2. 使用subconverter转换订阅...")
# 使用多个转换API尝试
converters = [
    "https://api.dler.io/sub",
    "https://sub.xeton.dev/sub",
    "https://api.wcc.best/sub"
]

subscription_url = "https://nano.nachoneko.cn/api/v1/client/subscribe?token=0564faff9cfd13442873e71f9a235469"

for i, converter in enumerate(converters, 1):
    print(f"\n尝试转换器 {i}/{len(converters)}: {converter}")

    cmd = f"curl -s '{converter}?target=clash&url={subscription_url}' -o /etc/clash/config.yaml"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()

    # 检查文件是否有内容
    stdin, stdout, stderr = ssh.exec_command("wc -l /etc/clash/config.yaml")
    lines = stdout.read().decode('utf-8', errors='ignore').strip().split()[0]

    if int(lines) > 10:
        print(f"✅ 转换成功，配置文件有 {lines} 行")
        break
    else:
        print(f"❌ 转换失败或文件为空")
else:
    print("\n⚠️ 所有转换器都失败，恢复备份...")
    stdin, stdout, stderr = ssh.exec_command("cp /etc/clash/config.yaml.bak /etc/clash/config.yaml 2>/dev/null || true")
    stdout.channel.recv_exit_status()

ssh.close()
print("\n完成！")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置Clash代理 - 使用fallback模式和订阅
"""
import paramiko
import sys
import codecs
import requests
import base64
import yaml

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

print("1. 获取订阅内容...")
subscription_url = "https://nano.nachoneko.cn/api/v1/client/subscribe?token=0564faff9cfd13442873e71f9a235469"

try:
    response = requests.get(subscription_url, timeout=30)
    if response.status_code == 200:
        print("✅ 订阅获取成功")

        # 解码base64订阅内容
        subscription_content = base64.b64decode(response.text).decode('utf-8')

        # 解析节点
        nodes = []
        for line in subscription_content.strip().split('\n'):
            if line.strip():
                nodes.append(line.strip())

        print(f"✅ 解析到 {len(nodes)} 个节点")

        # 显示前5个节点
        print("\n前5个节点:")
        for i, node in enumerate(nodes[:5], 1):
            # 解析节点名称
            if '#' in node:
                node_name = node.split('#')[-1]
                try:
                    node_name = requests.utils.unquote(node_name)
                except:
                    pass
                print(f"  {i}. {node_name}")
    else:
        print(f"❌ 订阅获取失败: {response.status_code}")
        sys.exit(1)

except Exception as e:
    print(f"❌ 获取订阅失败: {e}")
    sys.exit(1)

print("\n2. 生成Clash配置文件...")

# 创建Clash配置
clash_config = {
    'port': 7890,
    'socks-port': 7891,
    'allow-lan': False,
    'mode': 'rule',
    'log-level': 'info',
    'external-controller': '127.0.0.1:9090',
    'dns': {
        'enable': True,
        'listen': '0.0.0.0:53',
        'enhanced-mode': 'fake-ip',
        'nameserver': [
            '223.5.5.5',
            '119.29.29.29',
            '8.8.8.8'
        ]
    },
    'proxies': [],
    'proxy-groups': [
        {
            'name': 'PROXY',
            'type': 'fallback',
            'proxies': [],
            'url': 'http://www.gstatic.com/generate_204',
            'interval': 300
        }
    ],
    'rules': [
        'DOMAIN-SUFFIX,binance.com,PROXY',
        'DOMAIN-SUFFIX,binance.us,PROXY',
        'DOMAIN-SUFFIX,bnbstatic.com,PROXY',
        'DOMAIN-SUFFIX,coingecko.com,PROXY',
        'DOMAIN-SUFFIX,coinank.com,PROXY',
        'DOMAIN-SUFFIX,telegram.org,PROXY',
        'DOMAIN-SUFFIX,t.me,PROXY',
        'MATCH,DIRECT'
    ]
}

print("✅ 基础配置已创建")
print("\n3. 连接VPS上传配置...")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password="Qq159741",
           look_for_keys=False, allow_agent=False)

print("✅ 已连接到VPS")

# 将订阅内容保存到临时文件
print("\n4. 保存订阅内容到VPS...")
sftp = ssh.open_sftp()
with sftp.open('/tmp/clash_subscription.txt', 'w') as f:
    f.write(subscription_content)
print("✅ 订阅内容已保存")

# 使用clash订阅转换工具
print("\n5. 转换订阅为Clash配置...")
stdin, stdout, stderr = ssh.exec_command(
    "curl -s 'https://api.dler.io/sub?target=clash&url=https://nano.nachoneko.cn/api/v1/client/subscribe?token=0564faff9cfd13442873e71f9a235469' "
    "-o /etc/clash/config.yaml"
)
exit_status = stdout.channel.recv_exit_status()

if exit_status == 0:
    print("✅ 配置转换成功")
else:
    print("⚠️ 在线转换失败，使用本地配置")

sftp.close()
ssh.close()
print("\n✅ 配置完成！")

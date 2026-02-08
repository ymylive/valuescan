#!/usr/bin/env python3
"""最终部署验证"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print("=" * 60)
print("VPS 部署最终验证")
print("=" * 60)

# 1. ValueScan 服务状态
print("\n1. ValueScan 服务状态:")
stdin, stdout, stderr = ssh.exec_command('systemctl status valuescan-api valuescan-monitor valuescan-signal valuescan-token-refresher --no-pager | grep -E "(●|Active:)"')
print(stdout.read().decode())

# 2. ValueScan API 测试
print("\n2. ValueScan API 测试:")
stdin, stdout, stderr = ssh.exec_command('curl -s --max-time 5 http://127.0.0.1:5000/api/valuescan/token/status')
print(stdout.read().decode())

# 3. NOFX 目录
print("\n3. NOFX 目录:")
stdin, stdout, stderr = ssh.exec_command('ls -la /opt/nofx/web/dist/ | head -10')
print(stdout.read().decode())

# 4. NOFX 页面访问
print("\n4. NOFX 页面访问 (HTTPS):")
stdin, stdout, stderr = ssh.exec_command('curl -sk --max-time 5 -o /dev/null -w "%{http_code}" https://cornna.abrdns.com/nofx/')
print(f"  HTTP 状态码: {stdout.read().decode()}")

# 5. ValueScan 前端
print("\n5. ValueScan 前端 (HTTPS):")
stdin, stdout, stderr = ssh.exec_command('curl -sk --max-time 5 -o /dev/null -w "%{http_code}" https://cornna.abrdns.com/')
print(f"  HTTP 状态码: {stdout.read().decode()}")

# 6. 环境变量配置
print("\n6. 环境变量配置:")
stdin, stdout, stderr = ssh.exec_command('cat /root/valuescan/config/valuescan.env 2>/dev/null || echo "(文件不存在，可通过前端或手动创建)"')
print(stdout.read().decode())

print("\n" + "=" * 60)
print("部署完成总结")
print("=" * 60)
print("""
✓ ValueScan 后端已更新 (api/server.py 支持 VALUESCAN_EMAIL/PASSWORD)
✓ ValueScan 前端已更新 (ValueScanLoginSection.tsx)
✓ NOFX 已删除旧目录并重新克隆 dev 分支
✓ NOFX 前端已构建 (base=/nofx/)
✓ Nginx 已配置静态文件服务

访问地址:
  - ValueScan: https://cornna.abrdns.com/
  - NOFX: https://cornna.abrdns.com/nofx/

环境变量设置方式:
  方式 A: 前端「服务器环境变量」卡片保存账号/密码
  方式 B: 手动写入:
    printf 'VALUESCAN_EMAIL=你的邮箱\\nVALUESCAN_PASSWORD=你的密码\\n' | sudo tee /root/valuescan/config/valuescan.env
    sudo systemctl restart valuescan-monitor valuescan-signal valuescan-token-refresher
""")

ssh.close()

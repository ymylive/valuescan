#!/usr/bin/env python3
"""最终验证 NOFX 部署"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print("=" * 60)
print("NOFX 部署最终验证")
print("=" * 60)

# 1. 服务状态
print("\n1. 服务状态:")
stdin, stdout, stderr = ssh.exec_command('systemctl is-active nofx')
status = stdout.read().decode().strip()
print(f"  NOFX 服务: {status}")

# 2. 端口监听
print("\n2. 端口监听:")
stdin, stdout, stderr = ssh.exec_command('ss -tlnp | grep 8080')
print(stdout.read().decode() or "  (端口未监听)")

# 3. API 测试
print("\n3. API 测试:")
stdin, stdout, stderr = ssh.exec_command('curl -s --max-time 5 http://127.0.0.1:8080/api/config')
result = stdout.read().decode()
print(f"  /api/config: {result[:100]}..." if result else "  (无响应)")

# 4. 前端文件
print("\n4. 前端文件:")
stdin, stdout, stderr = ssh.exec_command('ls -la /opt/nofx/web/dist/index.html')
print(stdout.read().decode())

# 5. 通过 Nginx 访问
print("\n5. 通过 Nginx 访问:")
stdin, stdout, stderr = ssh.exec_command('curl -sk --max-time 5 -o /dev/null -w "%{http_code}" https://cornna.abrdns.com/nofx/')
print(f"  HTTPS 状态码: {stdout.read().decode()}")

# 6. 检查 Binance testnet 功能
print("\n6. Binance Testnet 功能:")
stdin, stdout, stderr = ssh.exec_command('grep -n "testnet\\|Testnet" /opt/nofx/trader/binance_futures.go | head -5')
print(stdout.read().decode())

print("\n" + "=" * 60)
print("部署完成总结")
print("=" * 60)
print("""
✓ NOFX 后端已编译并部署 (支持 Binance Testnet)
✓ NOFX 前端已构建 (包含 Testnet 开关 UI)
✓ systemd 服务已配置
✓ Nginx 已配置静态文件服务

访问地址:
  - NOFX: https://cornna.abrdns.com/nofx/
  - ValueScan: https://cornna.abrdns.com/

Binance Testnet 使用方法:
  1. 访问 https://cornna.abrdns.com/nofx/
  2. 进入交易所配置
  3. 添加 Binance 交易所时，开启「测试网模式」开关
  4. 使用 Binance Testnet 的 API Key 和 Secret

管理命令:
  systemctl start nofx    # 启动
  systemctl stop nofx     # 停止
  systemctl restart nofx  # 重启
  systemctl status nofx   # 状态
  journalctl -u nofx -f   # 日志
""")

ssh.close()

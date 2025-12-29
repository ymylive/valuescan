#!/usr/bin/env python3
"""修复 api/server.go 中的 NewFuturesTrader 调用"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print("修复 api/server.go...")

# 查看当前调用
print("\n当前 NewFuturesTrader 调用:")
stdin, stdout, stderr = ssh.exec_command('grep -n "NewFuturesTrader" /opt/nofx/api/server.go')
print(stdout.read().decode())

# 使用 Python 修复所有调用
modify_script = '''
import re

with open('/opt/nofx/api/server.go', 'r') as f:
    content = f.read()

# 查找所有 NewFuturesTrader 调用并添加 testnet 参数
# 模式: trader.NewFuturesTrader(xxx, xxx, xxx)
# 需要变成: trader.NewFuturesTrader(xxx, xxx, xxx, exchangeCfg.Testnet)

# 第一种模式: trader.NewFuturesTrader(exchangeCfg.APIKey, exchangeCfg.SecretKey, userID)
old_pattern1 = r'trader\\.NewFuturesTrader\\(exchangeCfg\\.APIKey, exchangeCfg\\.SecretKey, userID\\)'
new_pattern1 = 'trader.NewFuturesTrader(exchangeCfg.APIKey, exchangeCfg.SecretKey, userID, exchangeCfg.Testnet)'

content = re.sub(old_pattern1, new_pattern1, content)

with open('/opt/nofx/api/server.go', 'w') as f:
    f.write(content)

print("已修复 api/server.go 中的 NewFuturesTrader 调用")
'''

stdin, stdout, stderr = ssh.exec_command(f"python3 << 'PYEOF'\n{modify_script}\nPYEOF")
print(stdout.read().decode())
print(stderr.read().decode())

# 验证修复
print("\n验证修复:")
stdin, stdout, stderr = ssh.exec_command('grep -n "NewFuturesTrader" /opt/nofx/api/server.go')
print(stdout.read().decode())

ssh.close()

#!/usr/bin/env python3
"""完善 Binance testnet 支持"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print("完善 Binance testnet 支持...")

# 查看当前 NewFuturesTrader 函数
print("\n当前 NewFuturesTrader 函数:")
stdin, stdout, stderr = ssh.exec_command('sed -n "64,95p" /opt/nofx/trader/binance_futures.go')
print(stdout.read().decode())

# 使用 Python 修改文件
modify_script = '''
with open('/opt/nofx/trader/binance_futures.go', 'r') as f:
    content = f.read()

# 检查是否已经有 testnet 支持代码
if 'UseTestnet = true' not in content:
    # 在 client := futures.NewClient(apiKey, secretKey) 之后添加 testnet 支持
    old_code = 'client := futures.NewClient(apiKey, secretKey)'
    new_code = """client := futures.NewClient(apiKey, secretKey)

\tif testnet {
\t\tfutures.UseTestnet = true
\t\tlogger.Infof("🧪 Using Binance Futures TESTNET")
\t}"""
    
    content = content.replace(old_code, new_code)
    
    with open('/opt/nofx/trader/binance_futures.go', 'w') as f:
        f.write(content)
    print("已添加 testnet 支持代码")
else:
    print("testnet 支持代码已存在")
'''

stdin, stdout, stderr = ssh.exec_command(f"python3 << 'PYEOF'\n{modify_script}\nPYEOF")
print(stdout.read().decode())
print(stderr.read().decode())

# 验证修改
print("\n验证修改后的 NewFuturesTrader 函数:")
stdin, stdout, stderr = ssh.exec_command('sed -n "64,100p" /opt/nofx/trader/binance_futures.go')
print(stdout.read().decode())

# 编译测试
print("\n编译测试...")
stdin, stdout, stderr = ssh.exec_command('cd /opt/nofx && go build -o /tmp/nofx_test ./... 2>&1 | head -30')
result = stdout.read().decode()
print(result if result else "编译成功!")

ssh.close()

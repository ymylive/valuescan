#!/usr/bin/env python3
"""为 NOFX 添加 Binance 测试网支持"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print("=" * 60)
print("为 NOFX 添加 Binance 测试网支持")
print("=" * 60)

# 1. 修改 trader/binance_futures.go
print("\n1. 修改 trader/binance_futures.go...")

# 备份原文件
stdin, stdout, stderr = ssh.exec_command('cp /opt/nofx/trader/binance_futures.go /opt/nofx/trader/binance_futures.go.bak')
stdout.read()

# 修改 NewFuturesTrader 函数签名和实现
binance_patch = '''
// 修改 NewFuturesTrader 函数以支持 testnet
sed -i 's/func NewFuturesTrader(apiKey, secretKey string, userId string)/func NewFuturesTrader(apiKey, secretKey string, userId string, testnet bool)/' /opt/nofx/trader/binance_futures.go

# 在 NewClient 之后添加 testnet 支持
sed -i '/client := futures.NewClient(apiKey, secretKey)/a\\
\\tif testnet {\\
\\t\\tfutures.UseTestnet = true\\
\\t\\tlogger.Infof("🧪 Using Binance Futures TESTNET")\\
\\t}' /opt/nofx/trader/binance_futures.go
'''
stdin, stdout, stderr = ssh.exec_command(binance_patch)
print(stdout.read().decode())
print(stderr.read().decode())

# 2. 修改 trader/auto_trader.go
print("\n2. 修改 trader/auto_trader.go...")

# 备份
stdin, stdout, stderr = ssh.exec_command('cp /opt/nofx/trader/auto_trader.go /opt/nofx/trader/auto_trader.go.bak')
stdout.read()

# 添加 BinanceTestnet 字段到 AutoTraderConfig
auto_trader_patch = '''
# 在 BinanceSecretKey 后添加 BinanceTestnet 字段
sed -i '/BinanceSecretKey.*string/a\\
\\tBinanceTestnet        bool' /opt/nofx/trader/auto_trader.go

# 修改 NewFuturesTrader 调用以传递 testnet 参数
sed -i 's/trader = NewFuturesTrader(config.BinanceAPIKey, config.BinanceSecretKey, userID)/trader = NewFuturesTrader(config.BinanceAPIKey, config.BinanceSecretKey, userID, config.BinanceTestnet)/' /opt/nofx/trader/auto_trader.go
'''
stdin, stdout, stderr = ssh.exec_command(auto_trader_patch)
print(stdout.read().decode())
print(stderr.read().decode())

# 3. 修改 manager/trader_manager.go
print("\n3. 修改 manager/trader_manager.go...")

# 备份
stdin, stdout, stderr = ssh.exec_command('cp /opt/nofx/manager/trader_manager.go /opt/nofx/manager/trader_manager.go.bak')
stdout.read()

# 在 binance case 中添加 testnet 配置
manager_patch = '''
# 在 BinanceSecretKey 赋值后添加 BinanceTestnet
sed -i '/traderConfig.BinanceSecretKey = exchangeCfg.SecretKey/a\\
\\t\\ttraderConfig.BinanceTestnet = exchangeCfg.Testnet' /opt/nofx/manager/trader_manager.go
'''
stdin, stdout, stderr = ssh.exec_command(manager_patch)
print(stdout.read().decode())
print(stderr.read().decode())

# 4. 修改前端 ExchangeConfigModal.tsx 添加 testnet 开关
print("\n4. 修改前端 ExchangeConfigModal.tsx...")

# 备份
stdin, stdout, stderr = ssh.exec_command('cp /opt/nofx/web/src/components/traders/ExchangeConfigModal.tsx /opt/nofx/web/src/components/traders/ExchangeConfigModal.tsx.bak')
stdout.read()

# 创建 testnet 开关的 JSX 代码
testnet_ui = '''
                      {/* Testnet 开关 - 仅对 Binance 显示 */}
                      {currentExchangeType === 'binance' && (
                        <div className="flex items-center justify-between p-3 rounded" style={{ background: '#0B0E11', border: '1px solid #2B3139' }}>
                          <div>
                            <div className="text-sm font-semibold" style={{ color: '#EAECEF' }}>
                              {language === 'zh' ? '测试网模式' : 'Testnet Mode'}
                            </div>
                            <div className="text-xs" style={{ color: '#848E9C' }}>
                              {language === 'zh' ? '启用后将连接到 Binance 测试网，用于模拟交易' : 'Enable to connect to Binance Testnet for paper trading'}
                            </div>
                          </div>
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input
                              type="checkbox"
                              checked={testnet}
                              onChange={(e) => setTestnet(e.target.checked)}
                              className="sr-only peer"
                            />
                            <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#F0B90B]"></div>
                          </label>
                        </div>
                      )}
'''

# 使用 Python 在 VPS 上修改文件
modify_script = '''
import re

with open('/opt/nofx/web/src/components/traders/ExchangeConfigModal.tsx', 'r') as f:
    content = f.read()

# 在 Binance 白名单IP提示之前插入 testnet 开关
testnet_ui = """
                      {/* Testnet 开关 - 仅对 Binance 显示 */}
                      {currentExchangeType === 'binance' && (
                        <div className="flex items-center justify-between p-3 rounded mb-4" style={{ background: '#0B0E11', border: '1px solid #2B3139' }}>
                          <div>
                            <div className="text-sm font-semibold" style={{ color: '#EAECEF' }}>
                              {language === 'zh' ? '测试网模式' : 'Testnet Mode'}
                            </div>
                            <div className="text-xs" style={{ color: '#848E9C' }}>
                              {language === 'zh' ? '启用后将连接到 Binance 测试网，用于模拟交易' : 'Enable to connect to Binance Testnet for paper trading'}
                            </div>
                          </div>
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input
                              type="checkbox"
                              checked={testnet}
                              onChange={(e) => setTestnet(e.target.checked)}
                              className="sr-only peer"
                            />
                            <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#F0B90B]"></div>
                          </label>
                        </div>
                      )}

"""

# 在 {/* Binance 白名单IP提示 */} 之前插入
if '{/* Testnet 开关' not in content:
    content = content.replace(
        '{/* Binance 白名单IP提示 */}',
        testnet_ui + '                      {/* Binance 白名单IP提示 */}'
    )
    
    with open('/opt/nofx/web/src/components/traders/ExchangeConfigModal.tsx', 'w') as f:
        f.write(content)
    print("已添加 Testnet 开关 UI")
else:
    print("Testnet 开关 UI 已存在")
'''

stdin, stdout, stderr = ssh.exec_command(f'python3 << \'PYEOF\'\n{modify_script}\nPYEOF')
print(stdout.read().decode())
print(stderr.read().decode())

# 5. 验证修改
print("\n5. 验证修改...")

print("\n检查 binance_futures.go:")
stdin, stdout, stderr = ssh.exec_command('grep -n "func NewFuturesTrader" /opt/nofx/trader/binance_futures.go')
print(stdout.read().decode())

print("\n检查 auto_trader.go:")
stdin, stdout, stderr = ssh.exec_command('grep -n "BinanceTestnet" /opt/nofx/trader/auto_trader.go')
print(stdout.read().decode())

print("\n检查 trader_manager.go:")
stdin, stdout, stderr = ssh.exec_command('grep -n "BinanceTestnet" /opt/nofx/manager/trader_manager.go')
print(stdout.read().decode())

print("\n检查前端 testnet UI:")
stdin, stdout, stderr = ssh.exec_command('grep -n "Testnet 开关" /opt/nofx/web/src/components/traders/ExchangeConfigModal.tsx')
print(stdout.read().decode())

ssh.close()
print("\n完成!")

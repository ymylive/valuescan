#!/usr/bin/env python3
"""Upload and run full test on VPS"""
import paramiko

TEST_SCRIPT = '''#!/usr/bin/env python3
import sys
sys.path.insert(0, '/root/valuescan')

print("=== VPS ValuScan 完整测试 ===")

# 1. ValuScan API
print("\\n[1] ValuScan API 测试")
try:
    from valuescan_api.client import ValuScanClient
    from pathlib import Path
    
    token_file = Path("/root/valuescan/signal_monitor/valuescan_localstorage.json")
    print(f"Token file exists: {token_file.exists()}")
    
    client = ValuScanClient(token_file=token_file)
    
    # Test main force
    mf = client.get_dense_area(keyword=1, days=14)
    print(f"主力位 code: {mf.get('code') if mf else 'NO RESPONSE'}")
    if mf and mf.get('error'):
        print(f"  Error: {mf.get('error')}")
    mf_data = mf.get("data", [])
    if mf_data:
        print(f"BTC主力位: ${float(mf_data[-1]['price']):,.2f}")
    
    # Test hold cost
    hc = client.get_hold_cost(keyword=1, days=14)
    print(f"主力成本 code: {hc.get('code')}")
    hc_data = hc.get("data", {}).get("holdingPrice", [])
    if hc_data:
        print(f"BTC主力成本: ${float(hc_data[-1]['val']):,.2f}")
        
except Exception as e:
    import traceback
    print(f"ValuScan API错误: {e}")
    traceback.print_exc()

# 2. Signal Monitor 模块
print("\\n[2] Signal Monitor 模块")
try:
    from signal_monitor import config as sm_config
    print(f"Signal Monitor config: OK")
except Exception as e:
    print(f"Signal Monitor config: {e}")

print("\\n=== 测试完成 ===")
'''

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password="Qq159741")

# Write test script to VPS
sftp = ssh.open_sftp()
with sftp.file("/tmp/vps_test.py", "w") as f:
    f.write(TEST_SCRIPT)
sftp.close()

# Run test
stdin, stdout, stderr = ssh.exec_command("python3 /tmp/vps_test.py 2>&1")
print(stdout.read().decode())

ssh.close()

#!/usr/bin/env python3
"""Test AI modules on VPS"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password="Qq159741")

print("=== VPS AI 模块测试 ===\n")

# Test AI Market Summary
cmd = """cd /root/valuescan && python3 -c "
from signal_monitor.ai_market_summary import AIMarketSummary
print('AIMarketSummary: OK')
" 2>&1"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

# Test AI Key Levels  
cmd = """cd /root/valuescan && python3 -c "
from signal_monitor.ai_key_levels import generate_key_levels
print('AI Key Levels: OK')
" 2>&1"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

# Test ValuScan API on VPS
cmd = """cd /root/valuescan && PYTHONPATH=/root/valuescan python3 -c "
import sys
sys.path.insert(0, '/root/valuescan')
from valuescan_api import get_main_force, get_hold_cost
mf = get_main_force('BTC', 14)
hc = get_hold_cost('BTC', 14)
print(f'ValuScan API: code={mf.get(\"code\")}')
mf_data = mf.get('data', [])
if mf_data:
    print(f'BTC主力位: {float(mf_data[-1][\"price\"]):,.2f}')
hc_data = hc.get('data', {}).get('holdingPrice', [])
if hc_data:
    print(f'BTC主力成本: {float(hc_data[-1][\"val\"]):,.2f}')
" 2>&1"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

ssh.close()
print("=== 测试完成 ===")

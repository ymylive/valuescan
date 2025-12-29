#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查图表编辑结果
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

print("检查图表生成和编辑的完整日志...")
print("\n搜索关键词: '图表', 'chart', '编辑', 'edit', 'ETH'")

stdin, stdout, stderr = ssh.exec_command(
    "journalctl -u valuescan-signal --since '5 minutes ago' --no-pager | "
    "grep -E '图表|chart|编辑|edit|ETH|3782' | tail -30"
)

output = stdout.read().decode('utf-8', errors='ignore')
print("\n=== 图表相关日志 ===")
if output:
    print(output)
else:
    print("未找到相关日志")

print("\n" + "="*60)
print("检查测试脚本的完整输出...")
stdin, stdout, stderr = ssh.exec_command(
    "cat /root/valuescan/test_final_chart.py"
)
print(stdout.read().decode('utf-8', errors='ignore')[:500])

ssh.close()
print("\n✅ 检查完成！")
print("\n请到Telegram查看消息ID 3782，确认图表是否已添加。")

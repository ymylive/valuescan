#!/usr/bin/env python3
import os
# -*- coding: utf-8 -*-
"""
最终测试异步图表生成功能
"""
import paramiko
import sys
import codecs
import time

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password=os.getenv("VALUESCAN_VPS_PASSWORD", ""),
           look_for_keys=False, allow_agent=False)

print("1. 重启服务...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart valuescan-signal")
stdout.channel.recv_exit_status()
print("✅ 服务已重启")

print("\n2. 等待5秒让服务启动...")
time.sleep(5)

print("\n3. 创建测试脚本...")
test_script = """
import sys
sys.path.insert(0, '/root/valuescan/signal_monitor')

from logger import logger
from telegram import send_message_with_async_chart

logger.info("=" * 60)
logger.info("开始测试异步图表生成（依赖已安装）")
logger.info("=" * 60)

message = '''🔍 <b>$ETH AI 开始追踪</b>
━━━━━━━━━
🤖 AI捕获潜力代币，开始实时追踪
💵 现价: <b>$3500</b>
📈 24H涨幅: <code>+3.20%</code>
🎯 AI评分: <b>80</b> (⭐⭐⭐ 高分)

💡 提示:
   • 🔍 AI 已开始实时监控
   • 📊 关注后续价格和资金动态

#观察代币
━━━━━━━━━
🕐 测试时间
'''

logger.info("调用 send_message_with_async_chart...")
result = send_message_with_async_chart(message, 'ETH', pin_message=False)
logger.info(f"返回结果: {result}")

import time
logger.info("等待20秒让图表生成...")
time.sleep(20)

logger.info("测试完成")
logger.info("=" * 60)
"""

sftp = ssh.open_sftp()
with sftp.open('/root/valuescan/test_final_chart.py', 'w') as f:
    f.write(test_script)
sftp.close()
print("✅ 测试脚本已上传")

print("\n4. 执行测试...")
stdin, stdout, stderr = ssh.exec_command(
    "cd /root/valuescan && /usr/bin/python3.9 test_final_chart.py"
)
exit_status = stdout.channel.recv_exit_status()

output = stdout.read().decode('utf-8', errors='ignore')
error = stderr.read().decode('utf-8', errors='ignore')

print("\n=== 测试输出 ===")
print(output)
if error:
    print("\n=== 错误信息 ===")
    print(error)

print("\n5. 检查服务日志（最近50行）...")
stdin, stdout, stderr = ssh.exec_command(
    "journalctl -u valuescan-signal -n 50 --no-pager"
)
logs = stdout.read().decode('utf-8', errors='ignore')
print(logs)

ssh.close()
print("\n✅ 测试完成！请检查Telegram查看消息和图表。")

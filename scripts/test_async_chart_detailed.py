#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细测试异步图表生成
添加更多日志来追踪线程执行情况
"""
import paramiko
import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password=os.getenv("VALUESCAN_VPS_PASSWORD", ""),
           look_for_keys=False, allow_agent=False)

# 创建详细测试脚本
test_script = """
import sys
import os
import time
import threading

# 添加路径
sys.path.insert(0, '/root/valuescan/signal_monitor')

# 设置日志
from logger import logger

logger.info("=" * 50)
logger.info("开始详细测试异步图表生成")
logger.info("=" * 50)

# 导入函数
from telegram import send_message_with_async_chart

# 测试消息
message = '''🔍 <b>$BTC AI 开始追踪</b>
━━━━━━━━━
🤖 AI捕获潜力代币，开始实时追踪
💵 现价: <b>$98000</b>
📈 24H涨幅: <code>+2.50%</code>
🎯 AI评分: <b>75</b> (⭐⭐⭐ 高分)

💡 提示:
   • 🔍 AI 已开始实时监控
   • 📊 关注后续价格和资金动态
   • 🎯 等待更明确的入场信号
   • ⚠️ 追踪≠建议买入，注意风险

#观察代币
━━━━━━━━━
🕐 12:00:00 (UTC+8)
'''

logger.info("调用 send_message_with_async_chart...")
result = send_message_with_async_chart(message, 'BTC', pin_message=False)
logger.info(f"函数返回结果: {result}")

# 等待一段时间让线程执行
logger.info("等待15秒让后台线程执行...")
time.sleep(15)

logger.info("测试完成，检查是否有图表生成日志")
logger.info("=" * 50)
"""

# 上传测试脚本
sftp = ssh.open_sftp()
with sftp.open('/root/valuescan/test_async_detailed.py', 'w') as f:
    f.write(test_script)
sftp.close()

print("测试脚本已上传")
print("执行详细测试...")

# 执行测试
stdin, stdout, stderr = ssh.exec_command(
    "cd /root/valuescan && python3 test_async_detailed.py"
)

# 等待执行完成
exit_status = stdout.channel.recv_exit_status()

# 输出结果
output = stdout.read().decode('utf-8', errors='ignore')
error = stderr.read().decode('utf-8', errors='ignore')

print("\n=== 执行结果 ===")
print(output)
if error:
    print("\n=== 错误信息 ===")
    print(error)

print("\n=== 检查服务日志（最近30行）===")
stdin, stdout, stderr = ssh.exec_command(
    "journalctl -u valuescan-signal -n 30 --no-pager"
)
log_output = stdout.read().decode('utf-8', errors='ignore')
print(log_output)

ssh.close()
print("\n测试完成！")

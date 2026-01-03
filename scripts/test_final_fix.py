#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import paramiko
import sys
import codecs
import time

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password="Qq159741",
           look_for_keys=False, allow_agent=False)

# 创建最终测试脚本
test_script = """
import sys
sys.path.insert(0, '/root/valuescan/signal_monitor')

from logger import logger
from telegram import send_message_with_async_chart

logger.info("="*60)
logger.info("最终测试：5秒超时 + 详细日志")
logger.info("="*60)

message = '''🔍 <b>$BTC 最终测试</b>
━━━━━━━━━
测试5秒超时优化
💵 现价: <b>$98000</b>
'''

logger.info("发送测试消息...")
result = send_message_with_async_chart(message, 'BTC', pin_message=False)
logger.info(f"返回结果: {result}")

logger.info("等待45秒观察图表生成...")
import time
time.sleep(45)

logger.info("测试完成")
logger.info("="*60)
"""

sftp = ssh.open_sftp()
with sftp.open('/root/valuescan/test_final_fix.py', 'w') as f:
    f.write(test_script)
sftp.close()

print("测试脚本已上传")
print("执行最终测试...\n")

stdin, stdout, stderr = ssh.exec_command(
    "cd /root/valuescan && /usr/bin/python3.9 test_final_fix.py"
)

exit_status = stdout.channel.recv_exit_status()
output = stdout.read().decode('utf-8', errors='ignore')
error = stderr.read().decode('utf-8', errors='ignore')

print("=== 测试输出 ===")
print(output)
if error:
    print("\n=== 错误信息 ===")
    print(error)

print("\n检查详细日志...")
stdin, stdout, stderr = ssh.exec_command(
    "journalctl --since '2 minutes ago' | "
    "grep -E '\\[图表生成|获取.*数据|渲染|完成|超时|异常' | tail -30"
)
logs = stdout.read().decode('utf-8', errors='ignore')
print("\n=== 详细日志 ===")
print(logs if logs else "未找到相关日志")

ssh.close()
print("\n✅ 测试完成！请检查Telegram查看消息和图表。")

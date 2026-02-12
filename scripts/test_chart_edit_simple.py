#!/usr/bin/env python3
import os
# -*- coding: utf-8 -*-
"""
简单测试图表生成和消息编辑
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

# 创建测试脚本
test_script = """
import sys
import time
sys.path.insert(0, '/root/valuescan/signal_monitor')

from logger import logger

logger.info("="*60)
logger.info("测试图表生成和消息编辑")
logger.info("="*60)

# 1. 测试图表生成
logger.info("步骤1: 测试图表生成...")
try:
    from chart_pro_v10 import generate_chart_v10
    logger.info("✅ 导入 chart_pro_v10 成功")

    chart_data = generate_chart_v10('BTC', '15m', 200)
    if chart_data:
        logger.info(f"✅ 图表生成成功，大小: {len(chart_data)} bytes")
    else:
        logger.error("❌ 图表生成返回 None")
        sys.exit(1)
except Exception as e:
    logger.error(f"❌ 图表生成失败: {e}")
    import traceback
    logger.error(traceback.format_exc())
    sys.exit(1)

# 2. 测试发送消息
logger.info("\\n步骤2: 发送测试消息...")
try:
    from telegram import send_telegram_message

    message = '''🔍 <b>$BTC 测试消息</b>
━━━━━━━━━
这是一条测试消息
💵 现价: <b>$98000</b>
'''

    result = send_telegram_message(message, pin_message=False, symbol='BTC')
    if result and result.get('success'):
        message_id = result.get('message_id')
        logger.info(f"✅ 消息发送成功，ID: {message_id}")
    else:
        logger.error("❌ 消息发送失败")
        sys.exit(1)
except Exception as e:
    logger.error(f"❌ 发送消息失败: {e}")
    import traceback
    logger.error(traceback.format_exc())
    sys.exit(1)

# 3. 等待2秒
logger.info("\\n步骤3: 等待2秒...")
time.sleep(2)

# 4. 测试编辑消息添加图片
logger.info("\\n步骤4: 编辑消息添加图片...")
try:
    from telegram import edit_message_with_photo

    edit_result = edit_message_with_photo(
        message_id,
        chart_data,
        caption=message
    )

    if edit_result:
        logger.info("✅ 消息编辑成功，图片已添加")
    else:
        logger.error("❌ 消息编辑失败")
except Exception as e:
    logger.error(f"❌ 编辑消息失败: {e}")
    import traceback
    logger.error(traceback.format_exc())

logger.info("="*60)
logger.info("测试完成")
logger.info("="*60)
"""

# 上传测试脚本
sftp = ssh.open_sftp()
with sftp.open('/root/valuescan/test_chart_edit.py', 'w') as f:
    f.write(test_script)
sftp.close()

print("测试脚本已上传")
print("执行测试...\n")

# 执行测试
stdin, stdout, stderr = ssh.exec_command(
    "cd /root/valuescan && /usr/bin/python3.9 test_chart_edit.py"
)

# 等待执行完成
exit_status = stdout.channel.recv_exit_status()

# 输出结果
output = stdout.read().decode('utf-8', errors='ignore')
error = stderr.read().decode('utf-8', errors='ignore')

print("=== 测试输出 ===")
print(output)
if error:
    print("\n=== 错误信息 ===")
    print(error)

ssh.close()
print("\n测试完成！请检查Telegram查看消息和图表。")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import paramiko
import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password="Qq159741",
           look_for_keys=False, allow_agent=False)

# 创建测试脚本
test_script = """
import sys
sys.path.insert(0, '/root/valuescan/signal_monitor')

from telegram import send_message_with_async_chart

# 测试消息
message = '''🔔 <b>测试信号</b>

币种: $BTC
价格: 98000
类型: 测试异步图表生成

这是一条测试消息，用于验证异步图表生成功能。
'''

result = send_message_with_async_chart(message, 'BTC', pin_message=False)
print(f"发送结果: {result}")
"""

# 上传测试脚本
sftp = ssh.open_sftp()
with sftp.open('/root/valuescan/test_async_chart.py', 'w') as f:
    f.write(test_script)
sftp.close()

print("测试脚本已上传")
print("执行测试...")

# 执行测试
stdin, stdout, stderr = ssh.exec_command(
    "cd /root/valuescan && python3 test_async_chart.py"
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

ssh.close()
print("\n测试完成！请检查Telegram查看消息和图表。")

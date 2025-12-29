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

# 创建直接测试图表生成的脚本
test_script = """
import sys
sys.path.insert(0, '/root/valuescan/signal_monitor')

from logger import logger

logger.info("="*60)
logger.info("直接测试图表生成函数")
logger.info("="*60)

try:
    from chart_pro_v10 import generate_chart_v10

    logger.info("开始生成BTC图表...")
    chart_data = generate_chart_v10('BTC', '15m', 200)

    if chart_data:
        logger.info(f"✅ 图表生成成功: {len(chart_data)} bytes")
    else:
        logger.error("❌ 图表生成失败，返回None")

except Exception as e:
    logger.error(f"❌ 异常: {e}")
    import traceback
    logger.error(traceback.format_exc())

logger.info("="*60)
"""

sftp = ssh.open_sftp()
with sftp.open('/root/valuescan/test_direct_chart.py', 'w') as f:
    f.write(test_script)
sftp.close()

print("测试脚本已上传")
print("执行测试（使用timeout命令限制60秒）...\n")

stdin, stdout, stderr = ssh.exec_command(
    "cd /root/valuescan && timeout 60 /usr/bin/python3.9 test_direct_chart.py"
)

exit_status = stdout.channel.recv_exit_status()
output = stdout.read().decode('utf-8', errors='ignore')
error = stderr.read().decode('utf-8', errors='ignore')

print("=== 测试输出 ===")
print(output)
if error:
    print("\n=== 错误信息 ===")
    print(error)

print(f"\n退出状态: {exit_status}")
if exit_status == 124:
    print("⚠️ 测试超时（60秒）")

ssh.close()
print("\n测试完成！")

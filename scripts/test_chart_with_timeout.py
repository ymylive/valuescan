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

# 创建简化的测试脚本
test_script = """
import sys
import signal
sys.path.insert(0, '/root/valuescan/signal_monitor')

from logger import logger

# 设置30秒超时
def timeout_handler(signum, frame):
    logger.error("❌ 图表生成超时（30秒）")
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(30)

logger.info("开始测试图表生成（30秒超时）...")

try:
    from chart_pro_v10 import generate_chart_v10
    logger.info("✅ 模块导入成功")

    logger.info("开始生成RAVE图表...")
    chart_data = generate_chart_v10('RAVE', '15m', 200)

    signal.alarm(0)  # 取消超时

    if chart_data:
        logger.info(f"✅ 图表生成成功: {len(chart_data)} bytes")
    else:
        logger.error("❌ 图表生成返回None")

except Exception as e:
    signal.alarm(0)
    logger.error(f"❌ 异常: {e}")
    import traceback
    logger.error(traceback.format_exc())
"""

sftp = ssh.open_sftp()
with sftp.open('/root/valuescan/test_chart_timeout.py', 'w') as f:
    f.write(test_script)
sftp.close()

print("测试脚本已上传")
print("执行测试（30秒超时）...\n")

stdin, stdout, stderr = ssh.exec_command(
    "cd /root/valuescan && timeout 35 /usr/bin/python3.9 test_chart_timeout.py"
)

exit_status = stdout.channel.recv_exit_status()
output = stdout.read().decode('utf-8', errors='ignore')
error = stderr.read().decode('utf-8', errors='ignore')

print("=== 测试输出 ===")
print(output)
if error:
    print("\n=== 错误信息 ===")
    print(error)

ssh.close()
print("\n测试完成！")

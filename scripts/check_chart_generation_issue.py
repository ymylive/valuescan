#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查图表生成和编辑失败的原因
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

print("1. 检查config.py中的ENABLE_PRO_CHART配置...")
stdin, stdout, stderr = ssh.exec_command(
    "grep -n 'ENABLE_PRO_CHART' /root/valuescan/signal_monitor/config.py"
)
config_output = stdout.read().decode('utf-8', errors='ignore')
print(config_output if config_output else "未找到ENABLE_PRO_CHART配置")

print("\n2. 检查chart_pro_v10.py是否存在...")
stdin, stdout, stderr = ssh.exec_command(
    "ls -lh /root/valuescan/signal_monitor/chart_pro_v10.py"
)
chart_file = stdout.read().decode('utf-8', errors='ignore')
print(chart_file if chart_file else "文件不存在")

print("\n3. 测试直接调用图表生成函数...")
test_chart_script = """
import sys
sys.path.insert(0, '/root/valuescan/signal_monitor')

from logger import logger

logger.info("测试图表生成...")

try:
    from chart_pro_v10 import generate_chart_v10
    logger.info("✅ chart_pro_v10 导入成功")

    logger.info("开始生成BTC图表...")
    chart_data = generate_chart_v10('BTC', '15m', 200)

    if chart_data:
        logger.info(f"✅ 图表生成成功，数据大小: {len(chart_data)} bytes")
    else:
        logger.error("❌ 图表生成失败，返回None")

except Exception as e:
    logger.error(f"❌ 图表生成异常: {e}")
    import traceback
    logger.error(traceback.format_exc())
"""

sftp = ssh.open_sftp()
with sftp.open('/root/valuescan/test_chart_generation.py', 'w') as f:
    f.write(test_chart_script)
sftp.close()

print("执行图表生成测试...")
stdin, stdout, stderr = ssh.exec_command(
    "cd /root/valuescan && /usr/bin/python3.9 test_chart_generation.py"
)
exit_status = stdout.channel.recv_exit_status()

output = stdout.read().decode('utf-8', errors='ignore')
error = stderr.read().decode('utf-8', errors='ignore')

print("\n=== 测试输出 ===")
print(output)
if error:
    print("\n=== 错误信息 ===")
    print(error)

ssh.close()
print("\n完成！")

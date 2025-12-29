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

print("1. 上传修改后的chart_pro_v10.py...")
sftp = ssh.open_sftp()
sftp.put("signal_monitor/chart_pro_v10.py", "/root/valuescan/signal_monitor/chart_pro_v10.py")
print("✅ 文件已上传")
sftp.close()

print("\n2. 重启valuescan-signal服务...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart valuescan-signal")
stdout.channel.recv_exit_status()
print("✅ 服务已重启")

ssh.close()
print("\n✅ 部署完成！")
print("\n修改内容：")
print("- 支撑位 (S1, S2): 精度改为小数点后4位")
print("- 阻力位 (R1, R2): 精度改为小数点后4位")
print("- 24H最高价格: 精度改为小数点后4位")
print("- 24H最低价格: 精度改为小数点后4位")

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

print("1. 上传修复后的chart_pro_v10.py...")
sftp = ssh.open_sftp()
sftp.put("signal_monitor/chart_pro_v10.py", "/root/valuescan/signal_monitor/chart_pro_v10.py")
print("✅ 已上传")
sftp.close()

print("\n2. 重启服务...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart valuescan-signal")
stdout.channel.recv_exit_status()
print("✅ 服务已重启")

print("\n3. 等待5秒...")
import time
time.sleep(5)

print("\n4. 检查服务状态...")
stdin, stdout, stderr = ssh.exec_command("systemctl status valuescan-signal --no-pager | head -15")
status = stdout.read().decode('utf-8', errors='ignore')
print(status)

ssh.close()
print("\n✅ 部署完成！")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import paramiko
from pathlib import Path

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password="Qq159741", look_for_keys=False, allow_agent=False)

sftp = ssh.open_sftp()

# 上传telegram.py
local_file = "signal_monitor/telegram.py"
remote_file = "/root/valuescan/signal_monitor/telegram.py"

print(f"上传: {local_file}")
sftp.put(local_file, remote_file)
print("完成")

sftp.close()

# 重启服务
print("重启服务...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart valuescan-signal")
stdout.channel.recv_exit_status()
print("服务已重启")

ssh.close()
print("部署完成！")

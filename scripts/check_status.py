#!/usr/bin/env python3
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password="Qq159741", look_for_keys=False, allow_agent=False)

# 等待服务启动
time.sleep(2)

# 检查服务状态
stdin, stdout, stderr = ssh.exec_command("systemctl status valuescan-signal --no-pager -n 20")
print(stdout.read().decode())

ssh.close()
